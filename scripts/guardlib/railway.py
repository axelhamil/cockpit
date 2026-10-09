from typing import Optional, Sequence

from . import commandline
from .commandline import Path
from .config import GuardContext

ALLOWED_PATHS = (
    "--version",
    "--help",
    "help",
    "docs",
    "whoami",
    "login",
    "list",
    "status",
    "link",
    "unlink",
    "open",
    "logs",
    "metrics",
    "usage",
    "usage projects",
    "usage limit status",
    "templates search",
    "domain list",
    "domain status",
    "environment list",
    "environment config",
    "service list",
    "service status",
    "service logs",
    "deployment list",
    "postgres pitr status",
    "postgres pitr progress",
    "postgres pitr backup list",
    "postgres pitr backup create",
    "postgres pitr schedule list",
    "postgres pitr schedule set",
    "postgres pitr enable",
    "postgres history",
    "postgres ha status",
    "postgres pgbouncer status",
)

OPTIONS_WITH_VALUE = (
    "-s",
    "--service",
    "-e",
    "--environment",
    "-p",
    "--project",
    "-w",
    "--workspace",
    "--period",
)

OPTIONS_WITHOUT_VALUE = ("--json",)

TOP_LEVEL_ALIASES = {
    "variables": "variable",
    "vars": "variable",
    "var": "variable",
    "env": "environment",
    "template": "templates",
    "deployments": "deployment",
    "projects": "project",
    "new": "init",
}

ANY_LEVEL_ALIASES = {
    "ls": "list",
    "rm": "delete",
    "remove": "delete",
}

SUBCOMMAND_ALIASES = {
    ("templates",): {"find": "search"},
    ("environment",): {"show": "config", "info": "config"},
}

BLOCKED_OPTIONS = {
    ("postgres", "pitr", "schedule", "set"): ("--none",),
}

STREAM_BOUNDING_OPTIONS = ("--since", "-S", "--until", "-U", "--lines", "-n", "--tail")
STREAMING_PATHS = (("logs",), ("service", "logs"))

TOOLS_SCRIPT_COMMANDS = (
    "init",
    "deploy",
    "add",
    "domain",
    "variable",
    "redeploy",
    "restart",
    "service",
)

TOOLS_SCRIPT = "scripts/railway-tools.sh"
FREE_TEXT_OPTIONS = ()


def canonical(path: Path, word: str) -> str:
    if not path and word in TOP_LEVEL_ALIASES:
        return TOP_LEVEL_ALIASES[word]

    scoped = SUBCOMMAND_ALIASES.get(path, {})

    return scoped.get(word) or ANY_LEVEL_ALIASES.get(word, word)


ALLOWED = commandline.as_paths(ALLOWED_PATHS)


def blocking_reason(arguments: Sequence[str], context: GuardContext) -> Optional[str]:
    try:
        path, rest = commandline.command_path(arguments, ALLOWED, OPTIONS_WITH_VALUE, OPTIONS_WITHOUT_VALUE, canonical)
    except commandline.UnknownOption as unknown:
        return (
            "railway option " + unknown.option + " placed before the subcommand is not one the guard knows. "
            "Write the subcommand first, then its options"
        )

    if path not in ALLOWED:
        return off_list_reason(path, context)

    if commandline.is_option_path(path) and rest:
        return commandline.spelled("railway", path) + " followed by other arguments is blocked. Run it alone"

    return blocked_option_reason(path, rest) or endless_stream_reason(path, rest)


def endless_stream_reason(path: Path, rest: Sequence[str]) -> Optional[str]:
    if path not in STREAMING_PATHS or any(is_stream_bound(word) for word in rest):
        return None

    return (
        commandline.spelled("railway", path) + " without a bound streams forever and never returns. "
        "Add --since <duration> or --lines <count>"
    )


def is_stream_bound(word: str) -> bool:
    if commandline.option_name(word) in STREAM_BOUNDING_OPTIONS:
        return True

    return commandline.is_short_option(word) and word[:2] in STREAM_BOUNDING_OPTIONS


def blocked_option_reason(path: Path, rest: Sequence[str]) -> Optional[str]:
    for option in BLOCKED_OPTIONS.get(path, ()):
        if any(commandline.option_name(word) == option for word in rest):
            return (
                commandline.spelled("railway", path) + " " + option + " is blocked because it removes a protection "
                "of the SaaS. Escalate to the SaaS developer if the client really needs it"
            )

    return None


def off_list_reason(path: Path, context: GuardContext) -> str:
    command = commandline.spelled("railway", path)

    if path and path[0] in TOOLS_SCRIPT_COMMANDS:
        return (
            command + " is blocked as a direct call: it must go through sh " + context.plugin_root + "/"
            + TOOLS_SCRIPT + " with the same arguments, which only works on the tools project, never on the SaaS"
        )

    return (
        command + " is blocked: only read-only railway commands run directly. Do not work around it, "
        "escalate to the SaaS developer if the client really needs it"
    )
