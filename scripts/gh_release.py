import hashlib
import json
import re
import shutil
import sys
import zipfile


OFFICIAL_DOWNLOAD = re.compile(r"https://github\.com/cli/cli/releases/download/v[0-9.]+/gh_[0-9.]+_macOS_(arm64|amd64)\.zip")


def macos_asset(architecture):
    suffix = "_macOS_{}.zip".format(architecture)
    release = json.load(sys.stdin)
    assets = [asset for asset in release["assets"] if asset["name"].endswith(suffix)]

    if not assets or not OFFICIAL_DOWNLOAD.fullmatch(assets[0]["browser_download_url"]):
        raise ValueError("no official macOS asset")

    return assets[0]


def verify_download(architecture, archive_path):
    algorithm, _, expected = macos_asset(architecture)["digest"].partition(":")

    with open(archive_path, "rb") as archive:
        actual = hashlib.sha256(archive.read()).hexdigest()

    if algorithm != "sha256" or actual != expected:
        raise ValueError("the download does not match the published digest")


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
            print(macos_asset(sys.argv[2])["browser_download_url"])
        elif sys.argv[1] == "verify-download":
            verify_download(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "extract-binary":
            extract_binary(sys.argv[2], sys.argv[3])
        else:
            sys.exit(2)
    except (AttributeError, IndexError, KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile):
        sys.exit(1)


main()
