import json
import re
import shutil
import sys
import zipfile


def asset_url(architecture):
    suffix = "_macOS_{}.zip".format(architecture)
    release = json.load(sys.stdin)
    urls = [asset["browser_download_url"] for asset in release["assets"] if asset["name"].endswith(suffix)]

    if not urls or not urls[0].startswith("https://"):
        raise ValueError("no macOS asset")

    return urls[0]


def extract_binary(archive_path, destination):
    with zipfile.ZipFile(archive_path) as archive:
        members = [name for name in archive.namelist() if re.fullmatch(r"gh_[^/]+/bin/gh", name)]

        if len(members) != 1:
            raise ValueError("unexpected archive layout")

        with archive.open(members[0]) as source, open(destination, "wb") as target:
            shutil.copyfileobj(source, target)

    return destination


def main():
    try:
        if sys.argv[1] == "asset-url":
            print(asset_url(sys.argv[2]))
        elif sys.argv[1] == "extract-binary":
            extract_binary(sys.argv[2], sys.argv[3])
        else:
            sys.exit(2)
    except (AttributeError, IndexError, KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile):
        sys.exit(1)


main()
