import re
from typing import Dict, List, Optional, Tuple

PLACEHOLDER = "\x00"
BLANKS = " \t"
WORD_BREAKS = " \t\n;&|()<>"
SEGMENT_OPERATORS = ("&&", "||", ";;", "|&", ";", "|", "&")
PIPE_OPERATORS = ("|", "|&")
PROCESS_SUBSTITUTIONS = ("<(", ">(")
HEREDOC_OPERATORS = ("<<", "<<-")
HERE_STRING_OPERATOR = "<<<"
REDIRECTION = re.compile(r"\d*(&>>|&>|>>|>\||>&|<<<|<<-|<<|<&|<>|>|<)")
VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SPECIAL_PARAMETERS = "@*#?$!-0123456789"
GLOB_CHARACTERS = "*?[{"
DOUBLE_QUOTE_ESCAPES = '$`"\\'
BACKTICK_ESCAPES = "`\\$"
HOME_VARIABLE = "HOME"
SUBSHELL_OPENER = "("
SUBSHELL_CLOSER = ")"
GROUP_OPENER = "{"
GROUP_CLOSER = "}"
CASE_OPENER = "case"
CASE_SUBJECT_END = "in"
CASE_CLOSER = "esac"
CASE_BODY_TERMINATORS = (";;&", ";;", ";&")
CASE_PATTERN_SEPARATOR = "|"
NEWLINE = "\n"

Pipelines = Tuple[object, ...]


class ShellSyntaxError(ValueError):
    pass


class Word:
    def __init__(self, text: str, splits: bool = False, globs: bool = False):
        self.text = text
        self.splits = splits
        self.globs = globs

    @property
    def is_dynamic(self) -> bool:
        return PLACEHOLDER in self.text

    @property
    def is_literal(self) -> bool:
        return not self.is_dynamic and not self.globs

    @property
    def literal_prefix(self) -> str:
        return self.text.split(PLACEHOLDER, 1)[0]


class Redirection:
    def __init__(self, operator: str, target: Word):
        self.operator = operator
        self.target = target


class Segment:
    def __init__(self, pipelines: Pipelines, reads_pipe: bool = False):
        self.pipelines = pipelines
        self.reads_pipe = reads_pipe
        self.words: List[Word] = []
        self.redirections: List[Redirection] = []
        self.heredocs: List[str] = []

    @property
    def pipeline(self) -> object:
        return self.pipelines[-1]

    @property
    def is_empty(self) -> bool:
        return not self.words and not self.redirections


class PendingHeredoc:
    def __init__(self, segment: Segment, delimiter: str, expands: bool, strips_tabs: bool):
        self.segment = segment
        self.delimiter = delimiter
        self.expands = expands
        self.strips_tabs = strips_tabs


class Reader:
    def __init__(self, text: str, variables: Dict[str, str], segments: List[Segment]):
        self.text = text
        self.variables = variables
        self.segments = segments
        self.position = 0
        self.pending_heredocs: List[PendingHeredoc] = []

    def at_end(self) -> bool:
        return self.position >= len(self.text)

    def peek(self) -> str:
        return self.text[self.position]

    def following(self) -> str:
        return self.text[self.position + 1:self.position + 2]

    def starts_with(self, prefix) -> bool:
        return self.text.startswith(prefix, self.position)

    def read_list(self, closer: Optional[str], enclosing: Pipelines) -> None:
        segment = Segment(enclosing + (object(),))

        while True:
            self.skip_blanks()

            if self.at_list_end(closer, segment):
                self.finish(segment)
                return

            if self.read_into_segment(segment):
                continue

            separator = self.read_separator(segment)

            if separator == NEWLINE and segment.is_empty and segment.reads_pipe:
                continue

            self.finish(segment)
            segment = self.following_segment(segment, separator, enclosing)

    def following_segment(self, segment: Segment, separator: str, enclosing: Pipelines) -> Segment:
        if separator in PIPE_OPERATORS:
            return Segment(segment.pipelines, reads_pipe=True)

        if separator == SUBSHELL_OPENER:
            return Segment(segment.pipelines, reads_pipe=segment.reads_pipe)

        return Segment(enclosing + (object(),))

    def at_list_end(self, closer: Optional[str], segment: Segment) -> bool:
        if self.at_end():
            return self.end_of_text_closes(closer)

        if self.starts_with(SUBSHELL_CLOSER):
            return self.parenthesis_closes(closer)

        if closer == GROUP_CLOSER and segment.is_empty and self.at_keyword(GROUP_CLOSER):
            self.position += len(GROUP_CLOSER)
            return True

        return closer == CASE_CLOSER and self.at_case_body_end(segment)

    def end_of_text_closes(self, closer: Optional[str]) -> bool:
        if closer:
            raise ShellSyntaxError("a substitution, a subshell, a group or a case is never closed")

        return True

    def parenthesis_closes(self, closer: Optional[str]) -> bool:
        if closer != SUBSHELL_CLOSER:
            raise ShellSyntaxError("a closing parenthesis has no opening one")

        self.position += 1
        return True

    def at_case_body_end(self, segment: Segment) -> bool:
        if self.starts_with(CASE_BODY_TERMINATORS):
            return True

        return segment.is_empty and self.at_keyword(CASE_CLOSER)

    def at_keyword(self, keyword: str) -> bool:
        if not self.starts_with(keyword):
            return False

        after = self.text[self.position + len(keyword):self.position + len(keyword) + 1]

        return after == "" or after in WORD_BREAKS

    def read_into_segment(self, segment: Segment) -> bool:
        if self.starts_with("#"):
            self.skip_comment()
            return True

        if segment.is_empty and self.at_keyword(CASE_OPENER):
            self.position += len(CASE_OPENER)
            self.read_case(segment)
            return True

        if segment.is_empty and self.at_keyword(GROUP_OPENER):
            self.position += len(GROUP_OPENER)
            self.read_list(GROUP_CLOSER, segment.pipelines)
            return True

        if self.starts_with(PROCESS_SUBSTITUTIONS):
            self.position += 2
            self.read_list(SUBSHELL_CLOSER, segment.pipelines)
            segment.words.append(Word(PLACEHOLDER))
            return True

        redirection = REDIRECTION.match(self.text, self.position)

        if redirection:
            self.position = redirection.end()
            self.read_redirection(redirection.group(1), segment)
            return True

        if self.at_separator():
            return False

        segment.words.append(self.read_word(segment))
        return True

    def at_separator(self) -> bool:
        return self.starts_with(NEWLINE) or self.starts_with(SUBSHELL_OPENER) or self.operator_here() is not None

    def read_separator(self, segment: Segment) -> str:
        if self.starts_with(NEWLINE):
            self.position += 1
            self.read_heredoc_bodies()
            return NEWLINE

        if self.starts_with(SUBSHELL_OPENER):
            self.position += 1
            self.read_list(SUBSHELL_CLOSER, segment.pipelines)
            return SUBSHELL_OPENER

        operator = self.operator_here() or ""
        self.position += len(operator)

        return operator

    def read_case(self, segment: Segment) -> None:
        self.skip_blanks()
        self.read_word(segment)
        self.skip_case_spacing()

        if not self.at_keyword(CASE_SUBJECT_END):
            raise ShellSyntaxError("a case statement has no 'in'")

        self.position += len(CASE_SUBJECT_END)
        self.skip_case_spacing()

        while not self.at_keyword(CASE_CLOSER):
            self.read_case_patterns(segment)
            self.read_list(CASE_CLOSER, segment.pipelines)
            self.skip_case_body_terminator()
            self.skip_case_spacing()

        self.position += len(CASE_CLOSER)

    def skip_case_spacing(self) -> None:
        self.skip_blanks()

        while self.starts_with(NEWLINE) or self.starts_with("#"):
            self.skip_case_line_end()
            self.skip_blanks()

    def skip_case_line_end(self) -> None:
        if self.starts_with("#"):
            self.skip_comment()
            return

        self.position += 1
        self.read_heredoc_bodies()

    def skip_case_body_terminator(self) -> None:
        terminator = next((spelling for spelling in CASE_BODY_TERMINATORS if self.starts_with(spelling)), "")
        self.position += len(terminator)

    def read_case_patterns(self, segment: Segment) -> None:
        if self.starts_with(SUBSHELL_OPENER):
            self.position += 1

        while True:
            self.skip_blanks()

            if self.at_end():
                raise ShellSyntaxError("a case statement is never closed")

            if self.starts_with(SUBSHELL_CLOSER):
                self.position += 1
                return

            if self.starts_with(CASE_PATTERN_SEPARATOR):
                self.position += 1
                continue

            self.read_word(segment)

    def operator_here(self) -> Optional[str]:
        return next((operator for operator in SEGMENT_OPERATORS if self.starts_with(operator)), None)

    def finish(self, segment: Segment) -> None:
        if not segment.is_empty:
            self.segments.append(segment)

    def skip_blanks(self) -> None:
        while not self.at_end() and (self.peek() in BLANKS or self.starts_with("\\\n")):
            self.position += 2 if self.peek() == "\\" else 1

    def skip_comment(self) -> None:
        line_end = self.text.find("\n", self.position)
        self.position = len(self.text) if line_end == -1 else line_end

    def read_redirection(self, operator: str, segment: Segment) -> None:
        self.skip_blanks()
        start = self.position
        target = self.read_word(segment)
        segment.redirections.append(Redirection(operator, target))

        if operator == HERE_STRING_OPERATOR:
            segment.heredocs.append(target.text)

        if operator in HEREDOC_OPERATORS:
            is_quoted = self.text[start:self.position] != target.text
            self.pending_heredocs.append(PendingHeredoc(segment, target.text, not is_quoted, operator.endswith("-")))

    def read_heredoc_bodies(self) -> None:
        pending, self.pending_heredocs = self.pending_heredocs, []

        for heredoc in pending:
            body = self.read_heredoc_body(heredoc)
            heredoc.segment.heredocs.append(self.expand(body, heredoc.segment) if heredoc.expands else body)

    def read_heredoc_body(self, heredoc: PendingHeredoc) -> str:
        lines = []

        while not self.at_end():
            line = self.read_line()
            candidate = line.lstrip("\t") if heredoc.strips_tabs else line

            if candidate == heredoc.delimiter:
                return "\n".join(lines)

            lines.append(line)

        raise ShellSyntaxError("a here-document is never closed")

    def read_line(self) -> str:
        line_end = self.text.find("\n", self.position)
        stop = len(self.text) if line_end == -1 else line_end
        line = self.text[self.position:stop]
        self.position = stop + 1

        return line

    def expand(self, body: str, segment: Segment) -> str:
        reader = Reader(body, self.variables, self.segments)
        pieces = []

        while not reader.at_end():
            pieces.append(reader.read_quoted_piece(segment))

        return "".join(pieces)

    def read_word(self, segment: Segment) -> Word:
        fragments: List[Word] = []

        while not self.at_end() and self.peek() not in WORD_BREAKS:
            if self.starts_with("\\\n"):
                self.position += 2
                continue

            fragments.append(self.read_fragment(segment, is_first=not fragments))

        if not fragments:
            raise ShellSyntaxError("a word is missing")

        return Word(
            "".join(fragment.text for fragment in fragments),
            splits=any(fragment.splits for fragment in fragments),
            globs=any(fragment.globs for fragment in fragments),
        )

    def read_fragment(self, segment: Segment, is_first: bool) -> Word:
        character = self.peek()

        if character == "\\":
            return Word(self.read_escaped())

        if character == "'":
            return Word(self.read_single_quoted())

        if character == '"':
            return Word(self.read_double_quoted(segment))

        if character == "`":
            return Word(self.read_backticks(segment), splits=True)

        if character == "$":
            return self.read_dollar(segment, is_quoted=False)

        if character == "~" and is_first and self.tilde_expands():
            self.position += 1
            return Word(self.variables.get(HOME_VARIABLE, PLACEHOLDER))

        self.position += 1
        return Word(character, globs=character in GLOB_CHARACTERS)

    def tilde_expands(self) -> bool:
        following = self.following()

        return following == "" or following == "/" or following in WORD_BREAKS

    def read_escaped(self) -> str:
        escaped = self.following()

        if not escaped:
            raise ShellSyntaxError("the command ends with a backslash")

        self.position += 2
        return escaped

    def read_single_quoted(self) -> str:
        closing = self.text.find("'", self.position + 1)

        if closing == -1:
            raise ShellSyntaxError("a single quote is never closed")

        content = self.text[self.position + 1:closing]
        self.position = closing + 1

        return content

    def read_double_quoted(self, segment: Segment) -> str:
        self.position += 1
        pieces = []

        while not self.starts_with('"'):
            if self.at_end():
                raise ShellSyntaxError("a double quote is never closed")

            pieces.append(self.read_quoted_piece(segment))

        self.position += 1
        return "".join(pieces)

    def read_quoted_piece(self, segment: Segment) -> str:
        character = self.peek()

        if character == "\\":
            return self.read_quoted_escape()

        if character == "`":
            return self.read_backticks(segment)

        if character == "$":
            return self.read_dollar(segment, is_quoted=True).text

        self.position += 1
        return character

    def read_quoted_escape(self) -> str:
        escaped = self.following()
        self.position += 2 if escaped else 1

        if escaped == "\n":
            return ""

        if escaped and escaped in DOUBLE_QUOTE_ESCAPES:
            return escaped

        return "\\" + escaped

    def read_backticks(self, segment: Segment) -> str:
        self.position += 1
        pieces = []

        while not self.starts_with("`"):
            if self.at_end():
                raise ShellSyntaxError("a backtick is never closed")

            pieces.append(self.read_backtick_piece())

        self.position += 1
        self.read_nested("".join(pieces), segment)

        return PLACEHOLDER

    def read_backtick_piece(self) -> str:
        character = self.peek()
        escaped = self.following()

        if character == "\\" and escaped and escaped in BACKTICK_ESCAPES:
            self.position += 2
            return escaped

        self.position += 1
        return character

    def read_nested(self, text: str, host: Segment) -> None:
        reader = Reader(text, self.variables, self.segments)
        reader.read_list(None, host.pipelines)

        if reader.pending_heredocs:
            raise ShellSyntaxError("a here-document is never closed")

    def read_dollar(self, segment: Segment, is_quoted: bool) -> Word:
        if self.starts_with("$("):
            self.position += 2
            self.read_list(SUBSHELL_CLOSER, segment.pipelines)
            return Word(PLACEHOLDER, splits=True)

        if self.starts_with("${"):
            return self.read_braced_parameter(segment)

        if not is_quoted and self.starts_with("$'"):
            return Word(self.read_ansi_quoted())

        if not is_quoted and self.starts_with('$"'):
            self.position += 1
            return Word("")

        return self.read_plain_parameter()

    def read_plain_parameter(self) -> Word:
        name = VARIABLE_NAME.match(self.text, self.position + 1)

        if name:
            self.position = name.end()
            return self.resolve(name.group())

        self.position += 1

        if not self.at_end() and self.peek() in SPECIAL_PARAMETERS:
            self.position += 1
            return Word(PLACEHOLDER, splits=True)

        return Word("$")

    def resolve(self, name: str) -> Word:
        if name in self.variables:
            return Word(self.variables[name])

        return Word(PLACEHOLDER, splits=True)

    def read_braced_parameter(self, segment: Segment) -> Word:
        self.position += 2
        start = self.position

        while not self.starts_with("}"):
            if self.at_end():
                raise ShellSyntaxError("a parameter expansion is never closed")

            self.skip_parameter_piece(segment)

        content = self.text[start:self.position]
        self.position += 1

        if VARIABLE_NAME.fullmatch(content):
            return self.resolve(content)

        return Word(PLACEHOLDER, splits=True)

    def skip_parameter_piece(self, segment: Segment) -> None:
        character = self.peek()

        if character == "\\":
            self.position += 2
        elif character == "`":
            self.read_backticks(segment)
        elif character == "$":
            self.read_dollar(segment, is_quoted=True)
        else:
            self.position += 1

    def read_ansi_quoted(self) -> str:
        self.position += 2
        start = self.position

        while not self.starts_with("'"):
            if self.at_end():
                raise ShellSyntaxError("a single quote is never closed")

            self.position += 2 if self.peek() == "\\" else 1

        content = self.text[start:self.position]
        self.position += 1

        return PLACEHOLDER if "\\" in content else content


def split(command: str, variables: Dict[str, str]) -> List[Segment]:
    if PLACEHOLDER in command:
        raise ShellSyntaxError("the command holds a null character")

    segments: List[Segment] = []
    reader = Reader(command, variables, segments)
    reader.read_list(None, ())

    if reader.pending_heredocs:
        raise ShellSyntaxError("a here-document is never closed")

    return segments
