import json
import subprocess
import sys
from urllib.parse import unquote, urlsplit


def variables(payload):
    if isinstance(payload, list):
        return {item.get("name"): item.get("value") for item in payload if isinstance(item, dict)}

    return payload


def main():
    clipboard_command = sys.argv[1]

    try:
        public_url = variables(json.load(sys.stdin)).get("DATABASE_PUBLIC_URL")
    except (AttributeError, TypeError, ValueError):
        sys.exit(4)

    if not public_url:
        sys.exit(3)

    try:
        url = urlsplit(public_url)
        host, port, user, password = url.hostname, url.port, url.username, url.password
        database = unquote(url.path.lstrip("/"))
    except (AttributeError, TypeError, ValueError):
        sys.exit(4)

    if not (host and port and user and password and database):
        sys.exit(4)

    copied = subprocess.run(clipboard_command, shell=True, input=unquote(password), universal_newlines=True)

    if copied.returncode != 0:
        sys.exit(5)

    print("host: {}".format(host))
    print("port: {}".format(port))
    print("database: {}".format(database))
    print("user: {}".format(unquote(user)))


main()
