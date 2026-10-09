import filecmp
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import datetime, timezone

SCHEMA_VERSION = 2
NEWER_SCHEMA_STATUS = 3
HEADER_LINE_LIMIT = 50
LOCK_NAME = ".migrating"
LOCK_STALE_SECONDS = 600
LOCK_WAIT_SECONDS = 3
DEFAULT_SLUG = "app"
IMPORTED_HEADING = b"## Imported\n\n"
CLONE_LINE = "- Clone: ~/.cockpit/repo"
MOVED_DIRECTORIES = ("saas-project", "tools-project", "repo", "secrets")
LINKED_DIRECTORIES = ("saas-project", "tools-project")
PROJECT_FILES = ("journal.md", "handoff.md", "report.txt")
PROJECT_TOPICS = ("domain", "schema", "codebase", "tools")
USER_HEADER_KEYS = ("language", "plugin_version", "dependencies")
PROJECT_HEADER_KEYS = ("onboarding", "onboarding_step")
KNOWN_HEADER_KEYS = ("schema_version",) + USER_HEADER_KEYS + PROJECT_HEADER_KEYS
LEGACY_ROOT_FILES = (
    "domain.md",
    "schema.md",
    "codebase.md",
    "tools.md",
    "preferences.md",
    "journal.md",
    "handoff.md",
    "report.txt",
    "state.md",
)
NOTHING = "nothing"
NEWER = "newer"
MIGRATION = "migration"
CLEANUP = "cleanup"
USER_LINE = re.compile(r"^- User:[ \t]*(.*?)\r?$")


class MigrationError(Exception):
    pass


def reach(stage, can_fail=True):
    if can_fail and os.environ.get("COCKPIT_MIGRATION_FAIL_AT") == stage:
        raise MigrationError("stopped on purpose after " + stage)

    if os.environ.get("COCKPIT_MIGRATION_KILL_AT") == stage:
        os._exit(70)


def split_header(text):
    lines = text.split("\n")

    if lines[0].rstrip("\r") != "---":
        return None

    for index in range(1, min(len(lines), HEADER_LINE_LIMIT)):
        if lines[index].rstrip("\r") == "---":
            header = [line.rstrip("\r") for line in lines[1:index]]
            return header, "\n".join(lines[index + 1 :])

    return None


def read_header(lines):
    known = {}
    extra = []

    for line in lines:
        key, separator, value = line.partition(":")

        if separator and key in KNOWN_HEADER_KEYS and key not in known:
            known[key] = value.strip()
        else:
            extra.append(line)

    return known, extra


def read_state(path):
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as handle:
        parsed = split_header(handle.read())

    if parsed is None:
        return None

    known, extra = read_header(parsed[0])
    return known, extra, parsed[1]


def schema_of(known):
    value = known.get("schema_version", "")
    return int(value) if re.fullmatch(r"[0-9]{1,5}", value) else None


def heading_of(line):
    text = line.rstrip("\r")
    return text[3:].strip() if text.startswith("## ") else None


def slug_from(body):
    section = None

    for line in body.split("\n"):
        section = heading_of(line) or section

        if section == "SaaS project" and line.startswith("- Project:"):
            name = re.sub(r"\([^()]*\)\s*$", "", line[len("- Project:") :].rstrip("\r").rstrip())
            plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
            return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or DEFAULT_SLUG

    return DEFAULT_SLUG


def split_user(body):
    section = None
    kept = []
    user = None

    for line in body.split("\n"):
        section = heading_of(line) or section
        match = USER_LINE.match(line)

        if section == "Profile" and match and user is None:
            user = match.group(1)
            continue

        if line.rstrip("\r") == CLONE_LINE:
            continue

        kept.append(line)

    return "\n".join(kept), user


def user_lines(user):
    if not user or not user.strip():
        return []

    name, separator, email = user.rpartition(",")

    if separator and name.strip() and "@" in email and " " not in email.strip():
        return ["- Name: " + name.strip(), "- Email: " + email.strip()]

    return ["- User: " + user]


def user_file_text(known, user):
    lines = ["schema_version: {}".format(SCHEMA_VERSION)]
    lines += ["{}: {}".format(key, known[key]) for key in USER_HEADER_KEYS if key in known]

    return "---\n" + "\n".join(lines) + "\n---\n\n## User\n" + "".join(line + "\n" for line in user_lines(user))


def project_file_text(known, extra, body):
    lines = ["provider: railway"]
    lines += ["{}: {}".format(key, known[key]) for key in PROJECT_HEADER_KEYS if key in known]
    lines += extra

    return "---\n" + "\n".join(lines) + "\n---\n" + body


def write_new(path, data, text=False):
    if text:
        handle = open(path, "x", encoding="utf-8", errors="surrogateescape", newline="")
    else:
        handle = open(path, "xb")

    with handle:
        handle.write(data)


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def remove_if_empty(path):
    try:
        os.rmdir(path)
    except OSError:
        pass


def backup_names(root, partial):
    try:
        names = sorted(os.listdir(os.path.join(root, "backups")))
    except FileNotFoundError:
        return []

    return [name for name in names if name.startswith("v1-") and name.endswith(".partial") == partial]


def latest_backup(root):
    names = backup_names(root, partial=False)
    return os.path.join(root, "backups", names[-1]) if names else None


def remove_unchanged(path, backup):
    if backup is None:
        return

    saved = os.path.join(backup, os.path.basename(path))

    try:
        if os.path.isfile(path) and os.path.isfile(saved) and filecmp.cmp(path, saved, shallow=False):
            os.remove(path)
    except OSError:
        pass


class Lock:
    def __init__(self, root):
        self.path = os.path.join(root, LOCK_NAME)

    def is_stale(self):
        try:
            return time.time() - os.stat(self.path).st_mtime > LOCK_STALE_SECONDS
        except FileNotFoundError:
            return True

    def __enter__(self):
        wait = float(os.environ.get("COCKPIT_MIGRATION_LOCK_WAIT", LOCK_WAIT_SECONDS))
        deadline = time.monotonic() + wait

        while True:
            try:
                os.mkdir(self.path)
                return self
            except FileExistsError:
                pass

            if self.is_stale():
                try:
                    os.rmdir(self.path)
                except FileNotFoundError:
                    pass
                continue

            if time.monotonic() >= deadline:
                raise MigrationError("another session is migrating the saved setup")

            time.sleep(0.2)

    def __exit__(self, *_):
        remove_if_empty(self.path)


class Migration:
    def __init__(self, root, state):
        self.root = root
        self.known, self.extra, body = state
        self.app_body, user = split_user(body)
        self.user_text = user_file_text(self.known, user)
        self.slug = slug_from(body)
        self.project = os.path.join(root, "projects", self.slug)
        self.backup = None

    def at_root(self, *parts):
        return os.path.join(self.root, *parts)

    def in_project(self, *parts):
        return os.path.join(self.project, *parts)

    def discard_leftovers(self):
        for name in MOVED_DIRECTORIES:
            source = self.at_root(name)
            target = self.in_project(name)

            if not os.path.lexists(source) and os.path.lexists(target):
                os.rename(target, source)

        for name in ("state.md", ".relink") + PROJECT_FILES:
            remove_file(self.in_project(name))

        shutil.rmtree(self.in_project("memory"), ignore_errors=True)
        remove_file(self.at_root("memory", "preferences.md"))
        remove_file(self.at_root(".cockpit.md.tmp"))

        for name in backup_names(self.root, partial=True):
            shutil.rmtree(self.at_root("backups", name), ignore_errors=True)

        for directory in (self.at_root("memory"), self.project, self.at_root("projects"), self.at_root("backups")):
            remove_if_empty(directory)

    def roll_back(self):
        self.discard_leftovers()

        if self.backup:
            shutil.rmtree(self.backup, ignore_errors=True)

        remove_if_empty(self.at_root("backups"))

    def back_up(self):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        final = self.at_root("backups", "v1-" + stamp)
        repeat = 1

        while os.path.exists(final):
            repeat += 1
            final = self.at_root("backups", "v1-{}-{}".format(stamp, repeat))

        partial = final + ".partial"

        os.makedirs(self.at_root("backups"), mode=0o700, exist_ok=True)
        os.mkdir(partial, 0o700)

        for name in os.listdir(self.root):
            path = self.at_root(name)

            if os.path.isfile(path) and not os.path.islink(path):
                shutil.copy2(path, partial)

        os.rename(partial, final)
        self.backup = final

    def import_memory(self):
        os.makedirs(self.in_project("memory"))

        for topic in PROJECT_TOPICS:
            source = self.at_root(topic + ".md")

            if os.path.isfile(source):
                write_new(self.in_project("memory", topic + ".md"), IMPORTED_HEADING + read_bytes(source))

        preferences = self.at_root("preferences.md")

        if os.path.isfile(preferences):
            os.makedirs(self.at_root("memory"), exist_ok=True)
            write_new(self.at_root("memory", "preferences.md"), IMPORTED_HEADING + read_bytes(preferences))

    def build(self):
        os.makedirs(self.project, exist_ok=True)
        write_new(self.in_project("state.md"), project_file_text(self.known, self.extra, self.app_body), text=True)
        self.import_memory()

        for name in PROJECT_FILES:
            if os.path.isfile(self.at_root(name)):
                shutil.copy2(self.at_root(name), self.in_project(name))

        if any(os.path.lexists(self.at_root(name)) for name in LINKED_DIRECTORIES):
            write_new(self.in_project(".relink"), b"")

    def move_directories(self):
        for name in MOVED_DIRECTORIES:
            source = self.at_root(name)
            target = self.in_project(name)

            if not os.path.lexists(source):
                continue

            if os.path.lexists(target):
                raise MigrationError("projects/{}/{} already exists".format(self.slug, name))

            os.rename(source, target)

    def commit(self):
        temporary = self.at_root(".cockpit.md.tmp")

        with open(temporary, "w", encoding="utf-8", errors="surrogateescape", newline="") as handle:
            handle.write(self.user_text)
            handle.flush()
            os.fsync(handle.fileno())

        os.rename(temporary, self.at_root("cockpit.md"))

    def clean_up(self):
        for name in LEGACY_ROOT_FILES:
            remove_unchanged(self.at_root(name), self.backup)


def describe(error):
    if isinstance(error, MigrationError):
        text = str(error)
    elif isinstance(error, OSError):
        text = "{} ({})".format(error.strerror or "file error", os.path.basename(error.filename or ""))
    else:
        text = type(error).__name__

    return re.sub(r"[^A-Za-z0-9 ._()/-]", "", text)[:100]


def announce_update():
    print("state: updated to version {}".format(SCHEMA_VERSION))
    return 0


def announce_newer():
    print("state: written by a newer cockpit, left untouched")
    return NEWER_SCHEMA_STATUS


def migrate(root, state):
    migration = Migration(root, state)

    try:
        migration.discard_leftovers()
        migration.back_up()
        reach("backed-up")
        migration.build()
        reach("built")
        migration.move_directories()
        reach("renamed")
        migration.commit()
    except Exception:
        migration.roll_back()
        raise

    reach("committed", can_fail=False)
    migration.clean_up()


def finish_cleanup(root, state):
    backup = latest_backup(root)

    if backup is None:
        return False

    migration = Migration(root, state)
    migration.backup = backup
    migration.clean_up()
    return True


def pending_work(root):
    cockpit_path = os.path.join(root, "cockpit.md")
    state_path = os.path.join(root, "state.md")

    if os.path.isfile(cockpit_path):
        installed = read_state(cockpit_path)
        schema = schema_of(installed[0]) if installed else None

        if schema is not None and schema > SCHEMA_VERSION:
            return NEWER, None

        legacy = read_state(state_path) if os.path.isfile(state_path) else None

        if legacy is not None and schema_of(legacy[0]) == 1:
            return CLEANUP, legacy

        return NOTHING, None

    if not os.path.isfile(state_path):
        return NOTHING, None

    state = read_state(state_path)
    schema = schema_of(state[0]) if state else None

    if schema is not None and schema > SCHEMA_VERSION:
        return NEWER, None

    if schema != 1:
        return NOTHING, None

    return MIGRATION, state


def run(root):
    work, _ = pending_work(root)

    if work == NEWER:
        return announce_newer()

    if work == NOTHING:
        return 0

    with Lock(root):
        work, state = pending_work(root)

        if work == NEWER:
            return announce_newer()

        if work == NOTHING:
            return 0

        if work == MIGRATION:
            migrate(root, state)
        elif not finish_cleanup(root, state):
            return 0

    return announce_update()


def main():
    try:
        return run(sys.argv[1])
    except Exception as error:
        print("migration: failed ({})".format(describe(error)))
        return 0


sys.exit(main())
