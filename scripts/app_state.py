import os
import re
from typing import List, NamedTuple, Optional

LEGACY_SLUG = "app"
SLUG = re.compile(r"^[a-z0-9-]+$")
NAME = r"[A-Za-z0-9_.-]+"
REPOSITORY_URL = re.compile(
    r"^(?:(?:https?|ssh|git)://(?:[^@/]+@)?github\.com(?::\d+)?/|[^@/\s]+@github\.com:)?"
    r"(?P<owner>" + NAME + r")/(?P<repo>" + NAME + r")/?$"
)
APP_SERVICE = re.compile(
    r"^- App service: .*?, repository (?P<repository>\S+), deployed branch (?P<branch>\S+)\s*$"
)
TEST_ENVIRONMENT = re.compile(r"^- Test environment: (?P<value>.*?)\s*$")
TEST_BRANCH = re.compile(r", branch (?P<branch>[^\s,]+)")


class AppState(NamedTuple):
    slug: str
    onboarding: str
    repository: Optional[str]
    deployed_branch: Optional[str]
    test_branch: Optional[str]


def normalize_repository(url: str) -> Optional[str]:
    match = REPOSITORY_URL.match(url.strip())

    if not match:
        return None

    repo = match.group("repo")

    if repo.endswith(".git"):
        repo = repo[: -len(".git")]

    if not repo or repo in (".", ".."):
        return None

    return "{}/{}".format(match.group("owner"), repo).lower()


def header_values(lines: List[str]) -> dict:
    values = {}

    if not lines or lines[0].strip() != "---":
        return values

    for line in lines[1:]:
        if line.strip() == "---":
            return values

        key, separator, value = line.partition(":")

        if separator:
            values[key.strip()] = value.strip()

    return {}


def parse_state(slug: str, text: str) -> Optional[AppState]:
    lines = text.splitlines()
    onboarding = header_values(lines).get("onboarding")

    if not onboarding:
        return None

    repository = None
    deployed_branch = None
    test_branch = None

    for line in lines:
        app_service = APP_SERVICE.match(line)

        if app_service:
            repository = normalize_repository(app_service.group("repository"))
            deployed_branch = app_service.group("branch")
            continue

        test_environment = TEST_ENVIRONMENT.match(line)

        if test_environment and test_environment.group("value") != "none":
            branch = TEST_BRANCH.search(test_environment.group("value"))
            test_branch = branch.group("branch") if branch else None

    return AppState(slug, onboarding, repository, deployed_branch, test_branch)


def read_state(slug: str, path: str) -> Optional[AppState]:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return None

    if "\x00" in text:
        return None

    return parse_state(slug, text)


def state_files(state_home: str) -> List[tuple]:
    if not os.path.isfile(os.path.join(state_home, "cockpit.md")) and os.path.exists(
        os.path.join(state_home, "state.md")
    ):
        return [(LEGACY_SLUG, os.path.join(state_home, "state.md"))]

    projects = os.path.join(state_home, "projects")

    try:
        slugs = sorted(os.listdir(projects))
    except OSError:
        return []

    return [
        (slug, os.path.join(projects, slug, "state.md"))
        for slug in slugs
        if SLUG.match(slug) and os.path.isfile(os.path.join(projects, slug, "state.md"))
    ]


def read_apps(state_home: str) -> List[AppState]:
    apps = []

    for slug, path in state_files(state_home):
        app = read_state(slug, path)

        if app:
            apps.append(app)

    return apps
