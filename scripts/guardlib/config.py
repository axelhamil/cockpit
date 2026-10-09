import os
from typing import Dict, FrozenSet, Mapping, Set

DEFAULT_PROTECTED_BRANCHES = ("main", "master", "production", "prod")
BRANCH_SETTINGS = ("DEPLOYED_BRANCH", "TEST_BRANCH")
CONFIGURATION_FILE_NAME = "guard.conf"
STATE_HOME_VARIABLE = "RAILWAY_PILOT_HOME"
DEFAULT_STATE_DIRECTORY = ".railway-pilot"
SCRIPTS_DIRECTORY_NAME = "scripts"
VALUE_QUOTES = "\"'"


class GuardContext:
    def __init__(self, plugin_root: str, state_home: str, home: str, working_directory: str):
        self.plugin_root = plugin_root
        self.state_home = state_home
        self.home = home
        self.working_directory = working_directory

    @property
    def scripts_directory(self) -> str:
        return os.path.join(self.plugin_root, SCRIPTS_DIRECTORY_NAME)

    @property
    def configuration_path(self) -> str:
        return os.path.join(self.state_home, CONFIGURATION_FILE_NAME)

    def protected_branches(self) -> FrozenSet[str]:
        settings = read_settings(self.configuration_path)
        configured = (settings.get(name, "") for name in BRANCH_SETTINGS)

        return frozenset(DEFAULT_PROTECTED_BRANCHES) | frozenset(branch for branch in configured if branch)


def path_spellings(path: str) -> Set[str]:
    return {os.path.normpath(path).casefold(), os.path.realpath(path).casefold()}


def read_settings(path: str) -> Dict[str, str]:
    if not os.path.exists(path):
        return {}

    with open(path, encoding="utf-8") as configuration:
        lines = configuration.read().splitlines()

    pairs = (line.split("=", 1) for line in lines if "=" in line)

    return {name.strip(): value.strip().strip(VALUE_QUOTES) for name, value in pairs}


def context_from_environment(plugin_root: str, environment: Mapping[str, str], working_directory: str) -> GuardContext:
    home = environment.get("HOME") or os.path.expanduser("~")
    state_home = environment.get(STATE_HOME_VARIABLE) or os.path.join(home, DEFAULT_STATE_DIRECTORY)

    return GuardContext(
        plugin_root=plugin_root,
        state_home=state_home,
        home=home,
        working_directory=working_directory,
    )
