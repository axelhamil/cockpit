import json
import sys
from urllib.parse import urlsplit


def public_endpoint(payload):
    if isinstance(payload, list):
        payload = {item.get("name"): item.get("value") for item in payload if isinstance(item, dict)}

    url = urlsplit(payload["DATABASE_PUBLIC_URL"])

    if not url.hostname or not url.port:
        raise ValueError("no public endpoint")

    return "{} {}".format(url.hostname, url.port)


READERS = {"public-endpoint": public_endpoint}


def main():
    try:
        print(READERS[sys.argv[1]](json.load(sys.stdin)))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        sys.exit(1)


main()
