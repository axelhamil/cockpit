import copy
import json
import os
import re
import shutil
import sys
import tempfile


GITHUB_REPOSITORY = re.compile(r"https://github\.com/([A-Za-z0-9_-][A-Za-z0-9._-]*/[A-Za-z0-9_-][A-Za-z0-9._-]*?)(?:\.git)?/?")


class SettingsError(Exception):
    pass


class ManifestError(Exception):
    pass


def plugin_repository(manifest_path):
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        raise ManifestError("cannot be read")

    repository = manifest.get("repository") if isinstance(manifest, dict) else None
    match = GITHUB_REPOSITORY.fullmatch(repository) if isinstance(repository, str) else None

    if not match:
        raise ManifestError("does not name the GitHub repository of the plugin")

    return match.group(1)


def marketplace_entry(repository):
    return {"source": {"source": "github", "repo": repository}, "autoUpdate": True}


def load_settings(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except UnicodeDecodeError:
        raise SettingsError("is not readable text (invalid UTF-8)")

    if not text.strip():
        return {}

    try:
        settings = json.loads(text)
    except ValueError:
        raise SettingsError("is not valid JSON")

    if not isinstance(settings, dict):
        raise SettingsError("does not hold a JSON object")

    return settings


def merge_permissions(settings, shipped):
    permissions = settings.setdefault("permissions", {})

    if not isinstance(permissions, dict):
        raise SettingsError("has a 'permissions' entry that is not an object")

    added = 0

    for kind, wanted in shipped.items():
        current = permissions.setdefault(kind, [])

        if not isinstance(current, list):
            raise SettingsError("has a 'permissions.{}' entry that is not a list".format(kind))

        for value in wanted:
            if value not in current:
                current.append(value)
                added += 1

    return added


def merge_marketplace(settings, name, repository):
    marketplaces = settings.setdefault("extraKnownMarketplaces", {})

    if not isinstance(marketplaces, dict):
        raise SettingsError("has an 'extraKnownMarketplaces' entry that is not an object")

    existing = marketplaces.get(name)
    kept = existing if isinstance(existing, dict) else {}
    marketplaces[name] = {**kept, **marketplace_entry(repository)}


def remove_permissions(settings, shipped, before):
    permissions = settings.get("permissions")
    owned = before.get("permissions")

    if not isinstance(permissions, dict):
        return 0

    if not isinstance(owned, dict):
        owned = {}

    removed = 0

    for kind, shipped_values in shipped.items():
        current = permissions.get(kind)
        already_there = owned.get(kind)

        if not isinstance(current, list):
            continue

        if not isinstance(already_there, list):
            already_there = []

        kept = [value for value in current if value not in shipped_values or value in already_there]
        removed += len(current) - len(kept)
        permissions[kind] = kept

        if not kept and kind not in owned:
            del permissions[kind]

    return removed


def remove_marketplace(settings, name, before):
    marketplaces = settings.get("extraKnownMarketplaces")
    owned = before.get("extraKnownMarketplaces")

    if not isinstance(marketplaces, dict):
        return

    if isinstance(owned, dict) and name in owned:
        marketplaces[name] = owned[name]
        return

    marketplaces.pop(name, None)


def stage(path, text):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".cockpit-")

    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)

    if os.path.exists(path):
        shutil.copymode(path, temporary)

    return temporary


def discard(staged):
    for temporary in staged:
        if os.path.exists(temporary):
            os.unlink(temporary)


def drop_emptied(settings, before):
    for key in ("permissions", "extraKnownMarketplaces"):
        if settings.get(key) == {} and key not in before:
            del settings[key]


def forget_backup(mode, backup_path):
    if mode == "remove" and os.path.exists(backup_path):
        os.unlink(backup_path)


def apply(mode, settings_arg, permissions_path, marketplace, manifest_path):
    settings_path = os.path.realpath(settings_arg)
    backup_path = settings_arg + ".before-cockpit"

    with open(permissions_path, encoding="utf-8") as handle:
        shipped = json.load(handle)["permissions"]

    original = load_settings(settings_path)
    settings = copy.deepcopy(original)

    if mode == "remove":
        before = load_settings(backup_path)
        changed = remove_permissions(settings, shipped, before)
        remove_marketplace(settings, marketplace, before)
        drop_emptied(settings, before)
    else:
        changed = merge_permissions(settings, shipped)
        merge_marketplace(settings, marketplace, plugin_repository(manifest_path))

    if settings == original and (mode == "remove" or os.path.exists(settings_path)):
        forget_backup(mode, backup_path)
        return changed

    staged = [stage(settings_path, json.dumps(settings, indent=2, ensure_ascii=False) + "\n")]

    try:
        if mode != "remove" and os.path.exists(settings_path) and not os.path.exists(backup_path):
            shutil.copy2(settings_path, backup_path)

        os.replace(staged[0], settings_path)
    finally:
        discard(staged)

    forget_backup(mode, backup_path)
    return changed


def main():
    mode, settings_arg, permissions_path, marketplace, manifest_path = sys.argv[1:6]

    try:
        changed = apply(mode, settings_arg, permissions_path, marketplace, manifest_path)
    except ManifestError as error:
        sys.stderr.write(
            "The plugin file {} {}. Nothing was changed. Update or reinstall cockpit, then run this step again.\n".format(
                manifest_path, error
            )
        )
        sys.exit(1)
    except SettingsError as error:
        sys.stderr.write(
            "The Claude settings file {} {}. Nothing was changed. A developer has to repair that file, then this step can run again.\n".format(
                settings_arg, error
            )
        )
        sys.exit(1)
    except OSError as error:
        sys.stderr.write(
            "The settings could not be written ({}: {}). Nothing was changed. Check that the folder exists and is writable, then run this step again.\n".format(
                error.strerror, error.filename
            )
        )
        sys.exit(1)

    if mode == "remove":
        print("Settings cleaned: {} permission entries removed, {} is no longer a known marketplace.".format(changed, marketplace))
        return

    print("Settings applied: {} permission entries added, automatic updates on for {}.".format(changed, marketplace))


main()
