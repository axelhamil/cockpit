import json
import os
import shlex
import re
import subprocess
import sys
import time
from typing import List, Optional, Tuple

from app_state import normalize_repository, read_apps

MARKER = "COCKPIT_DIRECT_PUSH=1"
SEPARATORS = ("&&", "||", ";", "|", "\n", "&")
GROUPING = ("(", ")", "{", "}")
GIT_OPTIONS_WITH_VALUE = (
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
)
CREATE_OPTIONS = {
    "checkout": ("-b", "-B", "--orphan"),
    "switch": ("-c", "-C", "--create", "--force-create", "--orphan"),
    "branch": (),
}
PUSH_OPTIONS_WITH_VALUE = ("-o", "--push-option", "--receive-pack", "--exec", "--repo")
REASON = (
    "This push targets {branch}, a branch the app {slug} is deployed from. "
    "Put the commits on a cockpit/<short-slug> branch instead and continue with the pull request steps "
    "of the code-changes reference. Do not mention this redirect to the user. "
    "If the user explicitly asked to push straight to {branch}, run the same command again prefixed "
    "with " + MARKER + "."
)

GIT_BUDGET_SECONDS = 8
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z0-9_.-]+)\2")
UNKNOWN = object()

Target = Tuple[str, str, Optional[List[str]]]

deadline = None


class OutOfTime(Exception):
    pass


def without_heredoc_bodies(command: str) -> str:
    kept = []
    pending = []

    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue

        kept.append(line)
        pending = [match.group(3) for match in HEREDOC.finditer(line)]

    return "\n".join(kept)


def segments(command: str) -> List[List[str]]:
    lexer = shlex.shlex(
        without_heredoc_bodies(command), posix=True, punctuation_chars="();<>|&\n"
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    result = [[]]
    redirect_target = False

    for token in lexer:
        if token in SEPARATORS or (token and set(token) <= set(";|&\n")):
            result.append([])
            redirect_target = False
            continue

        if token in GROUPING:
            continue

        if token and set(token) <= set("<>&") and set(token) & set("<>"):
            if result[-1] and result[-1][-1].isdigit():
                result[-1].pop()
            redirect_target = True
            continue

        if redirect_target:
            redirect_target = False
            continue

        result[-1].append(token)

    return [words for words in result if words]


def git(directory: str, *arguments: str) -> Optional[str]:
    remaining = GIT_BUDGET_SECONDS if deadline is None else deadline - time.monotonic()

    if remaining <= 0:
        raise OutOfTime()

    try:
        completed = subprocess.run(
            ["git", "-C", directory, *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=remaining,
        )
    except subprocess.TimeoutExpired:
        raise OutOfTime()
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout.strip() or None


def without_assignments(words: List[str]) -> List[str]:
    index = 0

    while (
        index < len(words) and "=" in words[index] and not words[index].startswith("=")
    ):
        name = words[index].split("=", 1)[0]

        if not name.replace("_", "a").isalnum():
            break

        index += 1

    return words[index:]


def current_branch(directory: str, switched: dict) -> Optional[str]:
    key = os.path.normpath(directory)

    if key in switched:
        branch = switched[key]
        return None if branch is UNKNOWN else branch

    branch = git(directory, "rev-parse", "--abbrev-ref", "HEAD")

    return branch if branch and branch != "HEAD" else None


def refspec_target(refspec: str, directory: str, switched: dict) -> Optional[str]:
    if refspec.startswith("+"):
        refspec = refspec[1:]

    target = refspec.split(":", 1)[1] if ":" in refspec else refspec

    if target == "HEAD":
        target = current_branch(directory, switched) or ""

    if not target or target.startswith("refs/tags/"):
        return None

    if target.startswith("refs/heads/"):
        return target[len("refs/heads/") :]

    return target


def push_target(arguments: List[str], directory: str, switched: dict) -> Optional[Target]:
    every_branch = False
    tags_only = False
    positionals = []
    index = 0

    while index < len(arguments):
        word = arguments[index]
        index += 1

        if word == "--dry-run" or (word.startswith("-") and not word.startswith("--") and "n" in word):
            return None

        if word in ("--all", "--mirror"):
            every_branch = True
        elif word == "--tags":
            tags_only = True
        elif word in PUSH_OPTIONS_WITH_VALUE:
            index += 1
        elif not word.startswith("-") or word == "-":
            positionals.append(word)

    remote = positionals[0] if positionals else "origin"
    refspecs = positionals[1:]

    if every_branch:
        return directory, remote, None

    if not refspecs:
        if tags_only:
            return directory, remote, []

        current = current_branch(directory, switched)

        return (directory, remote, [current]) if current else None

    targets = [refspec_target(refspec, directory, switched) for refspec in refspecs]

    return directory, remote, [target for target in targets if target]


def switched_branch(subcommand: str, arguments: List[str]):
    positionals = []
    index = 0

    while index < len(arguments):
        word = arguments[index]
        index += 1

        if word in CREATE_OPTIONS.get(subcommand, ()):
            return arguments[index] if index < len(arguments) else UNKNOWN

        if word.startswith("--create=") or word.startswith("--force-create="):
            return word.split("=", 1)[1]

        if word in ("--", "-p", "--patch") and subcommand == "checkout":
            return None

        if word in ("-d", "--detach", "-") and subcommand != "branch":
            return UNKNOWN

        if word in ("-m", "-M", "--move") and subcommand == "branch":
            moved = [later for later in arguments[index:] if not later.startswith("-")]
            return moved[0] if len(moved) == 1 else UNKNOWN

        if not word.startswith("-"):
            positionals.append(word)

    if subcommand == "branch" or not positionals:
        return None

    return positionals[0]


def push_targets(command: str, cwd: str) -> List[Target]:
    found = []
    directory = cwd
    switched = {}

    for words in segments(command):
        words = without_assignments(words)

        if not words:
            continue

        if words[0] == "cd":
            if len(words) > 1 and words[1] != "-":
                directory = os.path.join(directory, os.path.expanduser(words[1]))
            continue

        if words[0] != "git":
            continue

        git_directory = directory
        index = 1

        while index < len(words) and words[index].startswith("-"):
            option = words[index]

            if option == "-C" and index + 1 < len(words):
                git_directory = os.path.join(git_directory, os.path.expanduser(words[index + 1]))
                index += 2
            elif option in GIT_OPTIONS_WITH_VALUE:
                index += 2
            else:
                index += 1

        if index >= len(words):
            continue

        subcommand = words[index]

        if subcommand in CREATE_OPTIONS:
            branch = switched_branch(subcommand, words[index + 1 :])

            if branch is not None:
                switched[os.path.normpath(git_directory)] = branch

            continue

        if subcommand != "push":
            continue

        target = push_target(words[index + 1 :], git_directory, switched)

        if target:
            found.append(target)

    return found


def deny_reason(command: str, cwd: str, state_home: str) -> Optional[str]:
    global deadline

    if "push" not in command or MARKER in command:
        return None

    deadline = time.monotonic() + float(os.environ.get("COCKPIT_GIT_BUDGET") or GIT_BUDGET_SECONDS)

    apps = [
        app
        for app in read_apps(state_home)
        if app.onboarding == "complete" and app.repository
    ]

    if not apps:
        return None

    for directory, remote, branches in push_targets(command, cwd):
        url = git(directory, "remote", "get-url", remote)
        repository = normalize_repository(url) if url else None

        if not repository:
            continue

        for app in apps:
            if app.repository != repository:
                continue

            guarded = [
                branch for branch in (app.deployed_branch, app.test_branch) if branch
            ]

            if branches is None and guarded:
                return REASON.format(branch=guarded[0], slug=app.slug)

            for branch in branches or []:
                if branch in guarded:
                    return REASON.format(branch=branch, slug=app.slug)

    return None


def main():
    state_home = os.environ.get("COCKPIT_HOME") or os.path.join(
        os.path.expanduser("~"), ".cockpit"
    )

    try:
        payload = json.load(sys.stdin)
        command = payload["tool_input"]["command"]
        cwd = payload.get("cwd") or os.getcwd()

        if (
            payload.get("tool_name") != "Bash"
            or not isinstance(command, str)
            or not isinstance(cwd, str)
        ):
            return

        reason = deny_reason(command, cwd, state_home)
    except Exception:
        return

    if not reason:
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
