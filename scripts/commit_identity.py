import json
import re
import subprocess
import sys
from typing import List, Optional

NOREPLY_DOMAIN = "@users.noreply.github.com"
LOGIN_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
COMMAND_TIMEOUT_SECONDS = 5


def output_of(command: List[str]) -> Optional[str]:
    try:
        finished = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if finished.returncode != 0:
        return None

    return finished.stdout


def noreply_address(answer: str) -> Optional[str]:
    try:
        user = json.loads(answer)
    except ValueError:
        return None

    if not isinstance(user, dict):
        return None

    user_id = user.get("id")
    login = user.get("login")

    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        return None

    if not isinstance(login, str) or not LOGIN_PATTERN.fullmatch(login):
        return None

    return "{}+{}{}".format(user_id, login, NOREPLY_DOMAIN)


def main() -> None:
    repo_dir, git_bin, gh_bin = sys.argv[1:4]
    current = output_of([git_bin, "-C", repo_dir, "config", "user.email"]) or ""

    if current.strip().endswith(NOREPLY_DOMAIN):
        return

    answer = output_of([gh_bin, "api", "user"])

    if answer is None:
        return

    address = noreply_address(answer)

    if address is None:
        return

    output_of([git_bin, "-C", repo_dir, "config", "user.email", address])


if __name__ == "__main__":
    main()
