import copy
import json
import os
import shutil
import sys
import tempfile


class SettingsError(Exception):
    pass


class GuardError(Exception):
    pass


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


def recorded_saas_project(guard_conf):
    if not os.path.exists(guard_conf):
        return ""

    with open(guard_conf, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            key, _, value = line.strip().partition("=")

            if key == "SAAS_PROJECT_ID":
                return value.strip().lower()

    return ""


def stage(path, text):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".railway-pilot-")

    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)

    if os.path.exists(path):
        shutil.copymode(path, temporary)

    return temporary


def discard(staged):
    for temporary in staged:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply(guard_conf, settings_arg, permissions_path, saas_project, deployed_branch, test_branch, marketplace, repository):
    settings_path = os.path.realpath(settings_arg)
    backup_path = settings_arg + ".before-railway-pilot"
    first_run = not os.path.exists(guard_conf)
    recorded = recorded_saas_project(guard_conf)

    if recorded and recorded != saas_project.lower():
        raise GuardError()

    with open(permissions_path, encoding="utf-8") as handle:
        shipped = json.load(handle)["permissions"]

    original = load_settings(settings_path)
    settings = copy.deepcopy(original)
    added = merge_permissions(settings, shipped)
    merge_marketplace(settings, marketplace, repository)

    guard_text = "SAAS_PROJECT_ID={}\nDEPLOYED_BRANCH={}\nTEST_BRANCH={}\n".format(saas_project.lower(), deployed_branch, test_branch)
    settings_changed = settings != original or not os.path.exists(settings_path)
    staged = []

    try:
        staged_guard = stage(guard_conf, guard_text)
        staged.append(staged_guard)

        if settings_changed:
            staged_settings = stage(settings_path, json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
            staged.append(staged_settings)

        if first_run and os.path.exists(settings_path) and not os.path.exists(backup_path):
            shutil.copy2(settings_path, backup_path)

        os.replace(staged_guard, guard_conf)

        if settings_changed:
            os.replace(staged_settings, settings_path)
    finally:
        discard(staged)

    return added


def main():
    arguments = sys.argv[1:9]
    guard_conf, settings_arg, marketplace = arguments[0], arguments[1], arguments[6]

    try:
        added = apply(*arguments)
    except GuardError:
        sys.stderr.write(
            "The safety settings already protect another SaaS project and this script never replaces it. "
            "Only the plugin maintainer can reset it, by deleting {} by hand.\n".format(guard_conf)
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

    print("Safety settings applied: {} permission entries added, automatic updates on for {}.".format(added, marketplace))


main()
