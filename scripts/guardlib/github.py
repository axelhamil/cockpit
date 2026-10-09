import re
from typing import Callable, Dict, List, Optional, Sequence

from . import commandline
from .commandline import Path
from .config import GuardContext

GH_ALLOWED_PATHS = (
    "--version",
    "auth status",
    "auth setup-git",
    "auth login",
    "repo view",
    "repo clone",
    "search code",
    "search issues",
    "search prs",
    "issue list",
    "issue view",
    "issue create",
    "issue comment",
    "issue close",
    "issue reopen",
    "pr list",
    "pr view",
    "pr diff",
    "pr checks",
    "pr create",
    "pr comment",
    "pr ready",
    "pr merge",
    "pr revert",
    "run list",
    "run view",
    "run watch",
    "label list",
    "label create",
    "api",
)

GH_OPTIONS_WITH_VALUE = ("-R", "--repo")
GH_OPTIONS_WITHOUT_VALUE = ()
GH_FREE_TEXT_OPTIONS = ("-b", "--body", "-t", "--title")
GH_TOKEN_LOGIN_OPTION = "--with-token"
GH_TOKEN_PRINTING_OPTIONS = ("--show-token", "-t")
GH_ADMIN_MERGE_OPTION = "--admin"
GH_API_ALLOWED_METHODS = ("GET",)
GH_API_METHOD_OPTION = "--method"
GH_API_METHOD_LETTER = "X"
GH_API_BLOCKED_OPTIONS = ("--field", "--raw-field", "--input")
GH_API_BLOCKED_LETTERS = "fF"
GH_API_LETTERS_WITH_VALUE = "Hqtp"

GIT_ALLOWED_SUBCOMMANDS = (
    "--version",
    "status",
    "diff",
    "log",
    "show",
    "add",
    "commit",
    "checkout",
    "switch",
    "branch",
    "fetch",
    "pull",
    "clone",
    "restore",
    "stash",
    "merge",
    "rebase",
    "reset",
    "rev-parse",
    "ls-files",
    "blame",
    "grep",
    "rm",
    "mv",
    "remote",
    "config",
    "push",
)

GIT_OPTIONS_WITH_VALUE = ("-C",)
GIT_OPTIONS_WITHOUT_VALUE = ("--no-pager",)
GIT_FREE_TEXT_OPTIONS = ("-m", "--message")

GIT_FILE_WRITING_OPTIONS = ("--output",)

GIT_COMMAND_RUNNING_OPTIONS = {
    "rebase": ("--exec", "-x"),
    "clone": ("--config", "-c", "--upload-pack", "-u", "--template"),
    "fetch": ("--upload-pack",),
    "pull": ("--upload-pack",),
    "grep": ("--open-files-in-pager", "-O"),
}

GIT_REMOTE_READ_OPTIONS = ("-v", "--verbose")
GIT_REMOTE_READ_SUBCOMMANDS = ("get-url", "show")
GIT_CONFIG_SCOPES = ("--local",)
GIT_CONFIG_LIST_OPTIONS = ("--list", "-l")
GIT_CONFIG_GET_OPTION = "--get"
GIT_CONFIG_WRITABLE_KEYS = ("user.name", "user.email")
GIT_PUSH_UPSTREAM_OPTIONS = ("-u", "--set-upstream")
GIT_PUSH_REMOTE = "origin"
GIT_PUSH_BRANCH = re.compile(r"pilot/[A-Za-z0-9._/-]+")
GIT_BRANCH_REFERENCE_PREFIX = "refs/heads/"
END_OF_OPTIONS = "--"

GH_ALLOWED = commandline.as_paths(GH_ALLOWED_PATHS)
GIT_ALLOWED = commandline.as_paths(GIT_ALLOWED_SUBCOMMANDS)

PUSH_FORM = "git push -u origin pilot/<name>"


def gh_blocking_reason(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    try:
        path, rest = commandline.command_path(arguments, GH_ALLOWED, GH_OPTIONS_WITH_VALUE, GH_OPTIONS_WITHOUT_VALUE)
    except commandline.UnknownOption as unknown:
        return "gh option " + unknown.option + " placed before the subcommand is blocked. Write the subcommand first"

    if path not in GH_ALLOWED:
        return (
            commandline.spelled("gh", path) + " is blocked: gh is limited to reading the repository, issues, "
            "pull requests, runs, labels and GET api calls. Escalate to the SaaS developer for anything else"
        )

    if commandline.is_option_path(path) and rest:
        return commandline.spelled("gh", path) + " followed by other arguments is blocked. Run it alone"

    return GH_PATH_RULES.get(path, allow)(rest)


def allow(arguments: Sequence[str]) -> Optional[str]:
    return None


def gh_login_reason(arguments: Sequence[str]) -> Optional[str]:
    if GH_TOKEN_LOGIN_OPTION in arguments:
        return None

    return (
        "gh auth login without --with-token is blocked: the web login gives access to every repository. "
        "Use gh auth login --with-token with the fine-grained token of the SaaS repository"
    )


def gh_status_reason(arguments: Sequence[str]) -> Optional[str]:
    if not commandline.uses_option(arguments, GH_TOKEN_PRINTING_OPTIONS):
        return None

    return (
        "gh auth status with --show-token is blocked: the token must never enter the conversation. "
        "Run gh auth status alone"
    )


def gh_merge_reason(arguments: Sequence[str]) -> Optional[str]:
    if not any(word.startswith(GH_ADMIN_MERGE_OPTION) for word in arguments):
        return None

    return (
        "gh pr merge --admin is blocked because it bypasses the branch protection. Merge without it, "
        "or leave the pull request open for the SaaS developer"
    )


def gh_clone_reason(arguments: Sequence[str]) -> Optional[str]:
    if END_OF_OPTIONS not in arguments:
        return None

    return "gh repo clone with git options after -- is blocked. Clone with the repository and the directory only"


def gh_api_reason(arguments: Sequence[str]) -> Optional[str]:
    methods = api_methods(arguments)

    if any(method.upper() not in GH_API_ALLOWED_METHODS for method in methods):
        return (
            "gh api with a method other than GET is blocked. Use the gh issue and gh pr commands to write, "
            "or escalate to the SaaS developer"
        )

    if any(sends_api_field(word) for word in arguments):
        return (
            "gh api with a field or an input (-f, -F, --field, --raw-field, --input) is blocked because it turns "
            "the call into a write. Put the parameters in the query string of a GET call"
        )

    return None


def api_methods(arguments: Sequence[str]) -> List[str]:
    following = list(arguments[1:]) + [""]

    return [
        method
        for word, next_word in zip(arguments, following)
        for method in api_method_of(word, next_word)
    ]


def api_method_of(word: str, next_word: str) -> List[str]:
    if commandline.option_name(word) == GH_API_METHOD_OPTION:
        return [word.split("=", 1)[1] if "=" in word else next_word]

    if is_api_letter_cluster(word) and GH_API_METHOD_LETTER in word:
        return [word.split(GH_API_METHOD_LETTER, 1)[1] or next_word]

    return []


def is_api_letter_cluster(word: str) -> bool:
    return commandline.is_short_option(word) and word[1] not in GH_API_LETTERS_WITH_VALUE


def sends_api_field(word: str) -> bool:
    if commandline.option_name(word) in GH_API_BLOCKED_OPTIONS:
        return True

    if not is_api_letter_cluster(word) or GH_API_METHOD_LETTER in word:
        return False

    return any(letter in word for letter in GH_API_BLOCKED_LETTERS)


GH_PATH_RULES: Dict[Path, Callable[[Sequence[str]], Optional[str]]] = {
    ("auth", "login"): gh_login_reason,
    ("auth", "status"): gh_status_reason,
    ("pr", "merge"): gh_merge_reason,
    ("repo", "clone"): gh_clone_reason,
    ("api",): gh_api_reason,
}


def git_blocking_reason(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    try:
        path, rest = commandline.command_path(arguments, GIT_ALLOWED, GIT_OPTIONS_WITH_VALUE, GIT_OPTIONS_WITHOUT_VALUE)
    except commandline.UnknownOption as unknown:
        return (
            "git option " + unknown.option + " placed before the subcommand is blocked: configuration and path "
            "overrides can run arbitrary commands. Run git without it"
        )

    if path not in GIT_ALLOWED:
        return (
            commandline.spelled("git", path) + " is blocked: it is not on the list of git commands needed for "
            "small changes. Escalate to the SaaS developer if the client really needs it"
        )

    if commandline.is_option_path(path) and rest:
        return commandline.spelled("git", path) + " followed by other arguments is blocked. Run it alone"

    subcommand = path[0]
    options = before_end_of_options(rest)

    if commandline.uses_option(options, GIT_FILE_WRITING_OPTIONS):
        return (
            "git " + subcommand + " with --output is blocked because it can overwrite any file. "
            "Read the result from the standard output"
        )

    if commandline.uses_option(options, GIT_COMMAND_RUNNING_OPTIONS.get(subcommand, ())):
        return (
            "git " + subcommand + " with an option that runs another command is blocked. "
            "Run it without that option"
        )

    return GIT_SUBCOMMAND_RULES.get(subcommand, allow_git)(rest, context)


def allow_git(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    return None


def before_end_of_options(arguments: Sequence[str]) -> Sequence[str]:
    if END_OF_OPTIONS not in arguments:
        return arguments

    return arguments[:list(arguments).index(END_OF_OPTIONS)]


def git_remote_reason(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    is_listing = len(arguments) <= 1 and all(word in GIT_REMOTE_READ_OPTIONS for word in arguments)
    is_reading = bool(arguments) and arguments[0] in GIT_REMOTE_READ_SUBCOMMANDS

    if is_listing or is_reading:
        return None

    return (
        "changing git remotes is blocked: only git remote, git remote -v, git remote get-url and git remote show "
        "are allowed. The clone must keep pointing at the SaaS repository"
    )


def git_config_reason(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    words = [word for word in arguments if word not in GIT_CONFIG_SCOPES]
    is_listing = len(words) == 1 and words[0] in GIT_CONFIG_LIST_OPTIONS
    is_getting = len(words) == 2 and words[0] == GIT_CONFIG_GET_OPTION and not commandline.is_option(words[1])

    if is_listing or is_getting or is_identity_setting(words):
        return None

    return (
        "this git config call is blocked: only git config --get <key>, git config --list and setting user.name "
        "or user.email in the clone are allowed, with no --global, --system or --file"
    )


def is_identity_setting(words: Sequence[str]) -> bool:
    if not 1 <= len(words) <= 2 or words[0] not in GIT_CONFIG_WRITABLE_KEYS:
        return False

    return not any(commandline.is_option(word) for word in words[1:])


def git_push_reason(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    protected_branches = context.protected_branches()
    operands = [word for word in arguments if word not in GIT_PUSH_UPSTREAM_OPTIONS]

    for operand in operands[1:]:
        if pushed_branch(operand) in protected_branches:
            return (
                "pushing to " + pushed_branch(operand) + " is blocked, push a pilot/ branch and open a pull "
                "request: " + PUSH_FORM + " then gh pr create"
            )

    if is_pilot_push(operands):
        return None

    return (
        "this git push is blocked: the only allowed form is " + PUSH_FORM + ", with no force flag, no other "
        "remote and no other refspec. Push a pilot/ branch and open a pull request"
    )


def is_pilot_push(operands: Sequence[str]) -> bool:
    if len(operands) != 2 or operands[0] != GIT_PUSH_REMOTE:
        return False

    return GIT_PUSH_BRANCH.fullmatch(operands[1]) is not None


def pushed_branch(refspec: str) -> str:
    destination = refspec.lstrip("+").split(":")[-1]

    if destination.startswith(GIT_BRANCH_REFERENCE_PREFIX):
        return destination[len(GIT_BRANCH_REFERENCE_PREFIX):]

    return destination


GIT_SUBCOMMAND_RULES: Dict[str, Callable[[Sequence[str], GuardContext], Optional[str]]] = {
    "remote": git_remote_reason,
    "config": git_config_reason,
    "push": git_push_reason,
}
