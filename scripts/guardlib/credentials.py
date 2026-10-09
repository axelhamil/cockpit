import re
from typing import List, Optional, Pattern, Sequence

from .config import STATE_HOME_VARIABLE, GuardContext
from .shell import Redirection, Segment

LOGIN_DIRECTORIES = (".railway", ".config/gh")
LOGIN_FREE_SUBDIRECTORIES = ("bin",)
SECRETS_DIRECTORY = "secrets"
HOME_SPELLINGS = ("~", "$HOME", "${HOME}")
STATE_HOME_SPELLINGS = ("$" + STATE_HOME_VARIABLE, "${" + STATE_HOME_VARIABLE + "}")
SECRET_KEEPING_COMMANDS = ("chmod", "mkdir", "ls", "test", "[", "rm")
SECRET_FILE_OPTIONS = ("-H", "--header")
SECRET_FILE_MARK = "@"
PARENT_DIRECTORY = ".."
PATH_END = r"(?![a-z0-9_.-])"
FREE_SUBDIRECTORY = re.compile("/(?:" + "|".join(LOGIN_FREE_SUBDIRECTORIES) + ")" + PATH_END)

LOGIN_REASON = (
    "reading the Railway or GitHub login files (~/.railway, ~/.config/gh) is blocked: tokens must never enter "
    "the conversation. Use railway whoami or gh auth status to check a login"
)
SECRET_REASON = (
    "reading a file of the secrets directory is blocked: keys must never enter the conversation. Store a key "
    "with pbpaste > <file> and send it with curl -H @<file>"
)


def blocking_reason(
    segment: Segment,
    executable_name: str,
    runs_plugin_script: bool,
    context: GuardContext,
) -> Optional[str]:
    words = [word.text for word in segment.words]
    targets = [redirection.target.text for redirection in segment.redirections]

    if any(mentions_login_file(text, context) for text in words + targets + segment.heredocs):
        return LOGIN_REASON

    secrets = directory_pattern(secrets_directories(context))

    if reads_secret_through_redirection(segment, secrets):
        return SECRET_REASON

    if runs_plugin_script or executable_name in SECRET_KEEPING_COMMANDS:
        return None

    return None if all_secrets_are_header_files(words, secrets) else SECRET_REASON


def directory_pattern(directories: Sequence[str]) -> Pattern[str]:
    spellings = "|".join(re.escape(directory.casefold()) for directory in directories)

    return re.compile("(?:" + spellings + ")" + PATH_END)


def login_directories(context: GuardContext) -> List[str]:
    homes = (context.home,) + HOME_SPELLINGS

    return [home + "/" + directory for home in homes for directory in LOGIN_DIRECTORIES]


def secrets_directories(context: GuardContext) -> List[str]:
    state_homes = [context.state_home] + list(STATE_HOME_SPELLINGS)

    if context.state_home.startswith(context.home + "/"):
        below_home = context.state_home[len(context.home):]
        state_homes += [home + below_home for home in HOME_SPELLINGS]

    return [state_home + "/" + SECRETS_DIRECTORY for state_home in state_homes]


def mentions_login_file(text: str, context: GuardContext) -> bool:
    folded = text.casefold()
    mentions = directory_pattern(login_directories(context)).finditer(folded)

    return any(PARENT_DIRECTORY in folded or not FREE_SUBDIRECTORY.match(folded, mention.end()) for mention in mentions)


def reads_secret_through_redirection(segment: Segment, secrets: Pattern[str]) -> bool:
    if any(secrets.search(heredoc.casefold()) for heredoc in segment.heredocs):
        return True

    return any(
        secrets.search(redirection.target.text.casefold()) and not is_output(redirection)
        for redirection in segment.redirections
    )


def is_output(redirection: Redirection) -> bool:
    return redirection.operator.startswith(">")


def all_secrets_are_header_files(words: Sequence[str], secrets: Pattern[str]) -> bool:
    previous_words = [""] + list(words)

    return all(
        is_header_file(previous, word)
        for previous, word in zip(previous_words, words)
        if secrets.search(word.casefold())
    )


def is_header_file(previous: str, word: str) -> bool:
    if word.startswith(SECRET_FILE_MARK) and previous in SECRET_FILE_OPTIONS:
        return True

    return any(word.startswith(option + "=" + SECRET_FILE_MARK) for option in SECRET_FILE_OPTIONS)
