from typing import Callable, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from .shell import Word

Path = Tuple[str, ...]
Normalise = Callable[[Path, str], str]


class UnknownOption(ValueError):
    def __init__(self, option: str):
        super().__init__(option)
        self.option = option


def as_paths(spellings: Iterable[str]) -> FrozenSet[Path]:
    return frozenset(tuple(spelling.split()) for spelling in spellings)


def option_name(word: str) -> str:
    return word.split("=", 1)[0]


def is_option(word: str) -> bool:
    return word.startswith("-") and word != "-"


def is_short_option(word: str) -> bool:
    return is_option(word) and not word.startswith("--")


def keep_spelling(path: Path, word: str) -> str:
    return word


def words_consumed_by_option(word: str, value_options: Sequence[str], flag_options: Sequence[str]) -> int:
    if word in value_options:
        return 2

    if "=" in word and option_name(word) in value_options:
        return 1

    if is_short_option(word) and word[:2] in value_options:
        return 1

    if word in flag_options:
        return 1

    raise UnknownOption(word)


def command_path(
    arguments: Sequence[str],
    allowed_paths: FrozenSet[Path],
    value_options: Sequence[str] = (),
    flag_options: Sequence[str] = (),
    normalise: Normalise = keep_spelling,
) -> Tuple[Path, List[str]]:
    groups = {path[:size] for path in allowed_paths for size in range(1, len(path))}
    path: Path = ()
    index = 0

    while index < len(arguments) and (not path or path in groups):
        word = arguments[index]
        opens_path = not path and (word,) in allowed_paths

        if opens_path or not is_option(word):
            path += (normalise(path, word),)
            index += 1
            continue

        index += words_consumed_by_option(word, value_options, flag_options)

    return path, list(arguments[index:])


def is_option_path(path: Path) -> bool:
    return bool(path) and is_option(path[0])


def spelled(tool: str, path: Path) -> str:
    return " ".join((tool,) + path)


def uses_option(arguments: Sequence[str], options: Sequence[str]) -> bool:
    return any(matches_option(word, option) for word in arguments for option in options)


def matches_option(word: str, option: str) -> bool:
    if not is_option(word):
        return False

    if is_short_option(option):
        return is_short_option(word) and option[1] in word[1:]

    name = option_name(word)

    return len(name) > 2 and option.startswith(name)


def dynamic_argument_reason(tool: str, arguments: Sequence[Word], free_text_options: Sequence[str]) -> Optional[str]:
    previous_texts = [""] + [word.text for word in arguments]

    for previous_text, word in zip(previous_texts, arguments):
        if word.splits:
            return (
                "an unquoted $VARIABLE or $(...) in a " + tool + " command is blocked because the guard cannot see "
                "the arguments it expands to. Write the value literally"
            )

        if word.is_dynamic and not is_harmless_dynamic(word, previous_text, free_text_options):
            return (
                "a " + tool + " argument built from a variable or a substitution is blocked unless it is the text "
                "of a message option. Write the argument literally"
            )

    return None


def is_harmless_dynamic(word: Word, previous_text: str, free_text_options: Sequence[str]) -> bool:
    prefix = word.literal_prefix

    if prefix.startswith("-"):
        return "=" in prefix

    return bool(prefix) or previous_text in free_text_options
