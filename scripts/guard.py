import json
import os
import sys
from typing import Mapping, Optional

PLUGIN_SCRIPTS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(PLUGIN_SCRIPTS_DIRECTORY)

sys.dont_write_bytecode = True
sys.path.insert(0, PLUGIN_SCRIPTS_DIRECTORY)

from guardlib import bash, files
from guardlib.config import context_from_environment
from guardlib.shell import PLACEHOLDER

ALLOW = 0
BLOCK = 2
BASH_TOOL = "Bash"
FILE_TOOLS = ("Edit", "Write", "NotebookEdit", "MultiEdit")
FILE_PATH_FIELDS = ("file_path", "notebook_path")
REASON_PREFIX = "railway-pilot guard: "
PLACEHOLDER_SPELLING = "$..."
MAXIMUM_REASON_LENGTH = 600


def decide(raw_input: str, environment: Mapping[str, str]) -> Optional[str]:
    payload = json.loads(raw_input)
    tool_name = required_text(payload, "tool_name")

    if tool_name != BASH_TOOL and tool_name not in FILE_TOOLS:
        return None

    tool_input = payload["tool_input"]
    working_directory = payload.get("cwd") or os.getcwd()
    context = context_from_environment(PLUGIN_ROOT, environment, working_directory)

    if tool_name == BASH_TOOL:
        return bash.blocking_reason(required_text(tool_input, "command", allow_empty=True), context)

    return files.blocking_reason(file_path_of(tool_input), context)


def required_text(fields: Mapping[str, object], name: str, allow_empty: bool = False) -> str:
    value = fields[name]

    if not isinstance(value, str) or not (value or allow_empty):
        raise ValueError(name + " is not a usable text")

    return value


def file_path_of(tool_input: Mapping[str, object]) -> str:
    present = [name for name in FILE_PATH_FIELDS if name in tool_input]

    if not present:
        raise ValueError("no file path in the tool input")

    return required_text(tool_input, present[0])


def one_line(reason: str) -> str:
    readable = reason.replace(PLACEHOLDER, PLACEHOLDER_SPELLING)
    flattened = " ".join(readable.split())
    printable = flattened.encode("ascii", "backslashreplace").decode("ascii")

    return REASON_PREFIX + printable[:MAXIMUM_REASON_LENGTH]


def unreadable_call_reason(error: BaseException) -> str:
    return (
        "this tool call could not be read (" + type(error).__name__ + ": " + str(error) + "), so it is blocked. "
        "Retry with a simpler command"
    )


def main() -> int:
    try:
        raw_input = sys.stdin.buffer.read().decode("utf-8")
        reason = decide(raw_input, os.environ)
    except Exception as error:
        reason = unreadable_call_reason(error)

    if reason is None:
        return ALLOW

    print(one_line(reason), file=sys.stderr)
    return BLOCK


if __name__ == "__main__":
    sys.exit(main())
