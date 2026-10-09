import os
import posixpath
import re
from typing import Dict, Iterable, List, Optional, Sequence

from . import commandline, credentials, github, railway, shell
from .config import CONFIGURATION_FILE_NAME, STATE_HOME_VARIABLE, GuardContext, path_spellings
from .shell import Redirection, Segment, Word

GUARDED_TOOL_RULES = {
    "railway": railway.blocking_reason,
    "gh": github.gh_blocking_reason,
    "git": github.git_blocking_reason,
}

GUARDED_TOOL_FREE_TEXT_OPTIONS = {
    "railway": railway.FREE_TEXT_OPTIONS,
    "gh": github.GH_FREE_TEXT_OPTIONS,
    "git": github.GIT_FREE_TEXT_OPTIONS,
}

TRANSPARENT_KEYWORDS = ("if", "then", "elif", "else", "while", "until", "do", "!", "{")

TRANSPARENT_PREFIX_VALUE_OPTIONS = {
    "time": (),
    "nice": ("-n", "--adjustment"),
    "nohup": (),
    "stdbuf": ("-i", "-o", "-e"),
    "timeout": ("-k", "--kill-after", "-s", "--signal"),
}

TRANSPARENT_PREFIXES_WITH_OPERAND = ("timeout",)
TEST_COMMANDS = ("[", "[[")
LOOKUP_COMMANDS = ("which",)
LOOKUP_BUILTIN = "command"
LOOKUP_BUILTIN_OPTIONS = ("-v", "-V")
PLUGIN_SCRIPT_INTERPRETERS = ("sh", "bash")
PLUGIN_SCRIPT_EXTENSION = ".sh"
SHELL_INTERPRETERS = ("sh", "bash", "zsh", "dash", "ksh")
SHELL_COMMAND_LETTER = "c"
INLINE_EVALUATORS = ("eval",)
TEXT_COMMANDS = ("echo", "printf", "grep", "rg", "cat", "head", "tail", "wc", "ls", "test", "[")
ENVIRONMENT_COMMANDS = ("env", "export", "declare", "typeset", "readonly", "local", "sudo", "exec", "command")

WRITE_COMMANDS = (
    "tee",
    "rm",
    "mv",
    "cp",
    "chmod",
    "chown",
    "ln",
    "dd",
    "install",
    "truncate",
    "unlink",
    "rmdir",
    "touch",
    "rsync",
)
IN_PLACE_EDITORS = ("sed",)
IN_PLACE_LONG_OPTION = "--in-place"
IN_PLACE_LETTER = "i"
HARMLESS_REDIRECTION_TARGETS = ("/dev/null",)
DESCRIPTOR_DUPLICATION = re.compile(r"\d+|-")
RESOLVED_VARIABLES = ("HOME", "CLAUDE_PLUGIN_ROOT", STATE_HOME_VARIABLE)
PATH_VARIABLE = "PATH"
INHERITED_PATH = "$PATH"
DOCUMENTED_PATH_DIRECTORIES = (".railway/bin", ".local/bin")
HOME_SPELLING = "~"
BLOCKED_VARIABLE_PREFIXES = ("RAILWAY_", "RP_", "GIT_CONFIG")

BLOCKED_VARIABLES = (
    "HOME",
    "CLAUDE_PLUGIN_ROOT",
    "CLAUDE_SETTINGS",
    "GH_BIN",
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_CONFIG_DIR",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_EXEC_PATH",
    "GIT_ASKPASS",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "ENV",
    "BASH_ENV",
)

GIT_DIRECTORY = re.compile(r"(^|/)\.git(/|$)")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
TOKEN_SEPARATORS = re.compile(r"[^A-Za-z0-9_./~+-]+")

EMPTY_COMMAND_REASON = "the command is empty, so the guard cannot check it"
DYNAMIC_EXECUTABLE_REASON = (
    "the name of the command is built from a variable, a substitution or a wildcard, so the guard cannot tell "
    "what would run. Write the command name literally"
)
DYNAMIC_SCRIPT_REASON = (
    "a shell script passed inline (sh -c, eval, here-document) is built from a variable or a substitution, "
    "so the guard cannot read it. Run the commands directly instead"
)
PROTECTED_WRITE_REASON = (
    "writing to the railway-pilot plugin directory or to guard.conf is blocked. guard.conf is written only by "
    "scripts/apply-settings.sh during onboarding, and plugin change requests go to proposals.md"
)
GIT_DIRECTORY_WRITE_REASON = (
    "writing inside a .git directory is blocked because hooks and git configuration can run commands. "
    "Change the files of the working tree only"
)
PATH_REASON = (
    "this PATH assignment is blocked: PATH may only be extended as "
    "PATH=\"$HOME/.railway/bin:$HOME/.local/bin:$PATH\""
)


def blocking_reason(command: str, context: GuardContext) -> Optional[str]:
    if not command.strip():
        return EMPTY_COMMAND_REASON

    try:
        segments = shell.split(command, resolved_variables(context))
    except shell.ShellSyntaxError as error:
        return (
            "the command cannot be split safely (" + str(error) + "), so it is blocked. "
            "Rewrite it as simpler commands with balanced quotes"
        )

    return first_reason(segment_reason(segment, segments, context) for segment in segments)


def first_reason(reasons: Iterable[Optional[str]]) -> Optional[str]:
    return next((reason for reason in reasons if reason), None)


def resolved_variables(context: GuardContext) -> Dict[str, str]:
    variables = dict(zip(RESOLVED_VARIABLES, (context.home, context.plugin_root, context.state_home)))
    variables[PATH_VARIABLE] = INHERITED_PATH

    return variables


def segment_reason(segment: Segment, segments: Sequence[Segment], context: GuardContext) -> Optional[str]:
    command = command_words(segment.words)
    script = plugin_script(command, context)

    return (
        environment_reason(segment, command, context)
        or credentials.blocking_reason(segment, executable_name(command), script is not None, context)
        or protected_write_reason(segment, script, context)
        or command_reason(segment, segments, command, script, context)
    )


def command_words(words: Sequence[Word]) -> List[Word]:
    remaining = list(words)

    while remaining:
        head = remaining[0].text

        if ASSIGNMENT.match(head) or head in TRANSPARENT_KEYWORDS:
            remaining = remaining[1:]
        elif posixpath.basename(head) in TRANSPARENT_PREFIX_VALUE_OPTIONS:
            remaining = without_prefix(remaining)
        else:
            break

    return remaining


def without_prefix(words: Sequence[Word]) -> List[Word]:
    name = posixpath.basename(words[0].text)
    value_options = TRANSPARENT_PREFIX_VALUE_OPTIONS[name]
    index = 1

    while index < len(words) and words[index].text.startswith("-"):
        index += 2 if words[index].text in value_options else 1

    if name in TRANSPARENT_PREFIXES_WITH_OPERAND:
        index += 1

    return list(words[index:])


def executable_name(command: Sequence[Word]) -> str:
    return posixpath.basename(command[0].text).casefold() if command else ""


def plugin_script(command: Sequence[Word], context: GuardContext) -> Optional[Word]:
    if not command:
        return None

    if is_plugin_file(command[0], context):
        return command[0]

    runs_through_interpreter = (
        len(command) > 1
        and command[0].is_literal
        and posixpath.basename(command[0].text) in PLUGIN_SCRIPT_INTERPRETERS
        and command[1].text.endswith(PLUGIN_SCRIPT_EXTENSION)
        and is_plugin_file(command[1], context, directly=True)
    )

    return command[1] if runs_through_interpreter else None


def is_plugin_file(word: Word, context: GuardContext, directly: bool = False) -> bool:
    if not word.is_literal or not os.path.isabs(word.text):
        return False

    scripts_directory = os.path.realpath(context.scripts_directory)
    path = os.path.realpath(word.text)

    if directly:
        return os.path.dirname(path) == scripts_directory

    return path.startswith(scripts_directory + os.sep)


def environment_reason(segment: Segment, command: Sequence[Word], context: GuardContext) -> Optional[str]:
    return first_reason(assignment_reason(text, context) for text in assignment_candidates(segment, command))


def assignment_candidates(segment: Segment, command: Sequence[Word]) -> List[str]:
    leading = segment.words[:len(segment.words) - len(command)]
    exported = command[1:] if executable_name(command) in ENVIRONMENT_COMMANDS else []

    return [word.text for word in list(leading) + list(exported)]


def assignment_reason(text: str, context: GuardContext) -> Optional[str]:
    assignment = ASSIGNMENT.match(text)

    if not assignment:
        return None

    name = assignment.group().rstrip("+=")
    value = text[assignment.end():]

    if name == PATH_VARIABLE:
        return None if is_documented_path(assignment.group(), value, context) else PATH_REASON

    if name in BLOCKED_VARIABLES or name.startswith(BLOCKED_VARIABLE_PREFIXES):
        return (
            "setting " + name + " is blocked because it changes what the guard, the shipped scripts or the "
            "guarded tools do. Run the command without it"
        )

    return None


def is_documented_path(assignment: str, value: str, context: GuardContext) -> bool:
    homes = (context.home, HOME_SPELLING)
    documented = [home + "/" + directory for home in homes for directory in DOCUMENTED_PATH_DIRECTORIES]
    entries = value.split(":")
    added = entries[:-1]

    if assignment.endswith("+=") or entries[-1] != INHERITED_PATH:
        return False

    return bool(added) and all(entry in documented for entry in added)


def protected_write_reason(segment: Segment, script: Optional[Word], context: GuardContext) -> Optional[str]:
    mentions = [word.text for word in segment.words if word is not script]
    mentions += [redirection.target.text for redirection in segment.redirections]

    if not writes_files(segment):
        return None

    if any(is_protected_mention(text, context) for text in mentions):
        return PROTECTED_WRITE_REASON

    if any(GIT_DIRECTORY.search(text.casefold()) for text in mentions):
        return GIT_DIRECTORY_WRITE_REASON

    return None


def is_protected_mention(text: str, context: GuardContext) -> bool:
    folded = text.casefold()

    return CONFIGURATION_FILE_NAME in folded or any(root in folded for root in path_spellings(context.plugin_root))


def writes_files(segment: Segment) -> bool:
    names = [posixpath.basename(word.text).casefold() for word in segment.words]
    edits_in_place = any(name in IN_PLACE_EDITORS for name in names) and any(
        is_in_place_option(word.text) for word in segment.words
    )

    return (
        any(is_file_write(redirection) for redirection in segment.redirections)
        or any(name in WRITE_COMMANDS for name in names)
        or edits_in_place
    )


def is_file_write(redirection: Redirection) -> bool:
    operator = redirection.operator
    target = redirection.target.text

    if ">" not in operator or target in HARMLESS_REDIRECTION_TARGETS:
        return False

    return not (operator.endswith("&") and DESCRIPTOR_DUPLICATION.fullmatch(target))


def is_in_place_option(text: str) -> bool:
    if text.startswith(IN_PLACE_LONG_OPTION):
        return True

    return commandline.is_short_option(text) and IN_PLACE_LETTER in text


def command_reason(
    segment: Segment,
    segments: Sequence[Segment],
    command: Sequence[Word],
    script: Optional[Word],
    context: GuardContext,
) -> Optional[str]:
    if not command:
        return hidden_tool_in(segment_texts(segment), "a variable assignment")

    executable = command[0]

    if executable.is_dynamic or (executable.globs and executable.text not in TEST_COMMANDS):
        return DYNAMIC_EXECUTABLE_REASON

    if script is not None:
        return None

    name = executable_name(command)

    if name in GUARDED_TOOL_RULES:
        return guarded_tool_reason(name, segment, command, context)

    if is_lookup(name, command):
        return None

    return (
        hidden_tool_in(segment_texts(segment), executable.text, only_paths=name in TEXT_COMMANDS)
        or piped_shell_reason(name, segment, segments, command)
        or inline_script_reason(name, segment, command, context)
    )


def guarded_tool_reason(name: str, segment: Segment, command: Sequence[Word], context: GuardContext) -> Optional[str]:
    leading = segment.words[:len(segment.words) - len(command)]
    arguments = command[1:]

    return (
        hidden_tool_in([word.text for word in leading], "a variable assignment")
        or commandline.dynamic_argument_reason(name, arguments, GUARDED_TOOL_FREE_TEXT_OPTIONS[name])
        or GUARDED_TOOL_RULES[name]([word.text for word in arguments], context)
    )


def is_lookup(name: str, command: Sequence[Word]) -> bool:
    if name in LOOKUP_COMMANDS:
        return True

    return name == LOOKUP_BUILTIN and len(command) > 1 and command[1].text in LOOKUP_BUILTIN_OPTIONS


def segment_texts(segment: Segment) -> List[str]:
    words = [word.text for word in segment.words]
    targets = [redirection.target.text for redirection in segment.redirections]

    return words + targets + segment.heredocs


def hidden_tool_in(texts: Iterable[str], carrier: str, only_paths: bool = False) -> Optional[str]:
    for text in texts:
        for token in TOKEN_SEPARATORS.split(text):
            tool = posixpath.basename(token).casefold()

            if tool in GUARDED_TOOL_RULES and ("/" in token or not only_paths):
                return (
                    tool + " is carried by " + carrier + " instead of being run directly, so the guard cannot "
                    "check it. Run " + tool + " as its own command, and use command -v " + tool + " to test "
                    "whether it is installed"
                )

    return None


def piped_shell_reason(
    name: str,
    segment: Segment,
    segments: Sequence[Segment],
    command: Sequence[Word],
) -> Optional[str]:
    reads_commands_from_pipe = (
        name in SHELL_INTERPRETERS
        and segment.reads_pipe
        and not command_strings([word.text for word in command[1:]])
    )

    if not reads_commands_from_pipe:
        return None

    feeders = [other for other in segments if other is not segment and segment.pipeline in other.pipelines]
    texts = [text for feeder in feeders for text in segment_texts(feeder)]

    return hidden_tool_in(texts, "text piped into " + name)


def inline_script_reason(name: str, segment: Segment, command: Sequence[Word], context: GuardContext) -> Optional[str]:
    for script in inline_scripts(name, segment, command):
        if shell.PLACEHOLDER in script:
            return DYNAMIC_SCRIPT_REASON

        reason = blocking_reason(script, context) if script.strip() else None

        if reason:
            return reason

    return None


def inline_scripts(name: str, segment: Segment, command: Sequence[Word]) -> List[str]:
    arguments = [word.text for word in command[1:]]

    if name in INLINE_EVALUATORS:
        return [" ".join(arguments)]

    if name not in SHELL_INTERPRETERS:
        return []

    return command_strings(arguments) + segment.heredocs


def command_strings(arguments: Sequence[str]) -> List[str]:
    for index, argument in enumerate(arguments):
        if commandline.is_short_option(argument) and SHELL_COMMAND_LETTER in argument:
            return list(arguments[index + 1:index + 2])

    return []
