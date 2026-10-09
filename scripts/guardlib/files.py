import fnmatch
import os
from typing import List, Optional, Sequence

from .config import GuardContext, path_spellings

INSTALLED_PLUGINS_DIRECTORY = (".claude", "plugins")
REPO_CLONE_DIRECTORY = "repo"
PROTECTED_REPO_FILE_PATTERNS = (".env", ".env.*", "railway.json", "railway.toml", "railway.ts")
PROTECTED_REPO_DIRECTORIES = ((".github", "workflows"), (".railway",), (".git",))

PLUGIN_REASON = (
    "editing the railway-pilot plugin files is blocked. Write the change request in proposals.md of the state "
    "directory for the plugin maintainer instead"
)
INSTALLED_PLUGINS_REASON = (
    "editing the installed Claude Code plugins is blocked. Plugins change only through their own updates"
)
CONFIGURATION_REASON = (
    "editing guard.conf is blocked: it is written only by scripts/apply-settings.sh during onboarding. "
    "Rerun onboarding to change the protected project or branches"
)
REPO_REASON = (
    "editing CI workflows, environment files, Railway configuration files or the .git directory of the SaaS "
    "repository is blocked. Escalate this change to the SaaS developer"
)


def blocking_reason(file_path: str, context: GuardContext) -> Optional[str]:
    path = absolute(file_path, context)

    if is_inside(path, context.plugin_root):
        return PLUGIN_REASON

    if is_inside(path, os.path.join(context.home, *INSTALLED_PLUGINS_DIRECTORY)):
        return INSTALLED_PLUGINS_REASON

    if path_spellings(path) & path_spellings(context.configuration_path):
        return CONFIGURATION_REASON

    if any(is_protected_repo_file(relative) for relative in paths_inside_clone(path, context)):
        return REPO_REASON

    return None


def absolute(file_path: str, context: GuardContext) -> str:
    if file_path == "~" or file_path.startswith("~/"):
        return context.home + file_path[1:]

    return os.path.join(context.working_directory, file_path)


def is_inside(path: str, directory: str) -> bool:
    return bool(relative_paths(path, directory))


def relative_paths(path: str, directory: str) -> List[str]:
    return [
        candidate[len(root):].lstrip(os.sep)
        for candidate in path_spellings(path)
        for root in path_spellings(directory)
        if candidate == root or candidate.startswith(root + os.sep)
    ]


def paths_inside_clone(path: str, context: GuardContext) -> List[str]:
    return relative_paths(path, os.path.join(context.state_home, REPO_CLONE_DIRECTORY))


def is_protected_repo_file(relative_path: str) -> bool:
    parts = relative_path.split(os.sep)
    name = parts[-1]

    if any(fnmatch.fnmatchcase(name, pattern) for pattern in PROTECTED_REPO_FILE_PATTERNS):
        return True

    return any(holds_sequence(parts[:-1], directory) for directory in PROTECTED_REPO_DIRECTORIES)


def holds_sequence(parts: Sequence[str], sequence: Sequence[str]) -> bool:
    size = len(sequence)

    return any(tuple(parts[start:start + size]) == tuple(sequence) for start in range(len(parts) - size + 1))
