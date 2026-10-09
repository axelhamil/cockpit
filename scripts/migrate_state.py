import errno
import fcntl
import filecmp
import os
import re
import shutil
import signal
import stat
import sys
import time
import unicodedata
from datetime import datetime, timezone

SCHEMA_VERSION = 2
NEWER_SCHEMA_STATUS = 3
HEADER_LINE_LIMIT = 50
LOCK_NAME = ".migrating"
LOCK_WAIT_SECONDS = 3
LOCK_RETRY_SECONDS = 0.2
DEFAULT_SLUG = "app"
SLUG_LENGTH_LIMIT = 40
IMPORTED_HEADING = b"## Imported\n\n"
CLONE_LINE = "- Clone: ~/.cockpit/repo"
USER_FILE = "cockpit.md"
TEMPORARY_USER_FILE = ".cockpit.md.tmp"
LEGACY_STATE_FILE = "state.md"
BACKUPS = "backups"
PRIVATE_DIRECTORY_MODE = 0o700
CHANGED_SUFFIX = ".changed-after-backup"
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
    LEGACY_STATE_FILE,
)
HANDLED_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
SIGNAL_STATUS_BASE = 128
NOTHING = "nothing"
NEWER = "newer"
MIGRATION = "migration"
CLEANUP = "cleanup"
CREATED_FILE = "file"
CREATED_DIRECTORY = "directory"
CREATED_BACKUP = "backup"
MOVED = "move"
USER_LINE = re.compile(r"^- User:[ \t]*(.*?)\r?$")
BACKUP_PATH = re.compile(r"backups/v1-[0-9]{8}-[0-9]{6}(-[0-9]+)?")


class MigrationError(Exception):
    pass


class LockBusy(MigrationError):
    pass


class Interrupted(BaseException):
    def __init__(self, number):
        super().__init__(number)
        self.number = number


def interrupt(number, _frame):
    raise Interrupted(number)


def reach(stage, can_fail=True):
    if can_fail and stage in os.environ.get("COCKPIT_MIGRATION_FAIL_AT", "").split(","):
        raise MigrationError("stopped on purpose after " + stage)

    kill_stage, _, signal_name = os.environ.get("COCKPIT_MIGRATION_KILL_AT", "").partition(":")

    if kill_stage != stage:
        return

    if signal_name:
        signal.raise_signal(getattr(signal, "SIG" + signal_name))
        return

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
    try:
        with open(path, encoding="utf-8", errors="surrogateescape", newline="") as handle:
            parsed = split_header(handle.read())
    except FileNotFoundError:
        return None

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
            slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
            return slug[:SLUG_LENGTH_LIMIT].rstrip("-") or DEFAULT_SLUG

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


def as_bytes(text):
    return text.encode("utf-8", "surrogateescape")


def mode_of(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def write_file(path, data, mode=None, replace=False):
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if replace else os.O_EXCL)
    descriptor = os.open(path, flags, 0o666 if mode is None else mode)

    with os.fdopen(descriptor, "wb") as handle:
        if mode is not None:
            os.fchmod(descriptor, mode)

        handle.write(data)
        handle.flush()
        os.fsync(descriptor)


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def is_plain_file(path):
    return os.path.isfile(path) and not os.path.islink(path)


def backup_names(root):
    try:
        names = sorted(os.listdir(os.path.join(root, BACKUPS)))
    except FileNotFoundError:
        return []

    return [name for name in names if BACKUP_PATH.fullmatch(BACKUPS + "/" + name)]


def free_backup_name(root):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = "v1-" + stamp
    repeat = 1

    while any(os.path.lexists(os.path.join(root, BACKUPS, name + suffix)) for suffix in ("", ".partial")):
        repeat += 1
        name = "v1-{}-{}".format(stamp, repeat)

    return name


def free_changed_path(backup, name):
    path = os.path.join(backup, name + CHANGED_SUFFIX)
    repeat = 1

    while os.path.lexists(path):
        repeat += 1
        path = os.path.join(backup, "{}{}-{}".format(name, CHANGED_SUFFIX, repeat))

    return path


def retire_legacy_file(root, name, backup):
    path = os.path.join(root, name)
    saved = os.path.join(backup, name)
    is_link = os.path.islink(path)

    if is_link and name != LEGACY_STATE_FILE:
        return

    if not is_link and not os.path.isfile(path):
        return

    if not is_link and is_plain_file(saved) and filecmp.cmp(path, saved, shallow=False):
        os.remove(path)
        return

    os.rename(path, free_changed_path(backup, name))


def retire_legacy_files(root, backup):
    for name in LEGACY_ROOT_FILES:
        try:
            retire_legacy_file(root, name, backup)
        except OSError:
            pass


def undo_file(root, relative):
    remove_file(os.path.join(root, relative))


def undo_directory(root, relative):
    path = os.path.join(root, relative)

    if os.path.islink(path) or not os.path.isdir(path):
        return

    try:
        os.rmdir(path)
    except OSError as error:
        if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
            raise


def undo_move(root, relative):
    reach("rollback")
    source = os.path.join(root, os.path.basename(relative))
    target = os.path.join(root, relative)

    if not os.path.lexists(source) and os.path.lexists(target):
        os.rename(target, source)


def undo_backup(root, relative):
    for path in (os.path.join(root, relative) + ".partial", os.path.join(root, relative)):
        if os.path.lexists(path):
            shutil.rmtree(path)


UNDO = {
    CREATED_FILE: undo_file,
    CREATED_DIRECTORY: undo_directory,
    CREATED_BACKUP: undo_backup,
    MOVED: undo_move,
}


def is_safe_entry(kind, relative):
    if kind not in UNDO or not relative or os.path.isabs(relative) or ".." in relative.split("/"):
        return False

    return kind != CREATED_BACKUP or BACKUP_PATH.fullmatch(relative) is not None


class Ledger:
    def __init__(self, descriptor):
        self.descriptor = descriptor

    def entries(self):
        os.lseek(self.descriptor, 0, os.SEEK_SET)
        data = b""

        while True:
            chunk = os.read(self.descriptor, 65536)

            if not chunk:
                break

            data += chunk

        complete_lines = data.decode("utf-8", "ignore").split("\n")[:-1]
        entries = [tuple(line.split(" ", 1)) for line in complete_lines if " " in line]

        return [entry for entry in entries if is_safe_entry(*entry)]

    def record(self, kind, relative):
        os.write(self.descriptor, as_bytes("{} {}\n".format(kind, relative)))
        os.fsync(self.descriptor)

    def replace(self, entries):
        os.ftruncate(self.descriptor, 0)

        for kind, relative in entries:
            os.write(self.descriptor, as_bytes("{} {}\n".format(kind, relative)))

        os.fsync(self.descriptor)

    def discard(self):
        try:
            self.replace([])
        except OSError:
            pass

    def undo(self, root):
        failed = []

        for kind, relative in reversed(self.entries()):
            try:
                UNDO[kind](root, relative)
            except Exception:
                failed.append((kind, relative))

        failed.reverse()
        self.replace(failed)
        return not failed


class Lock:
    def __init__(self, root):
        self.path = os.path.join(root, LOCK_NAME)
        self.descriptor = None

    def is_still_the_lock_file(self, descriptor):
        try:
            return os.path.samestat(os.fstat(descriptor), os.stat(self.path))
        except FileNotFoundError:
            return False

    def try_to_take(self):
        try:
            descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
        except IsADirectoryError:
            raise MigrationError("a folder named {} is in the way".format(LOCK_NAME))

        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(descriptor)
            return False

        if not self.is_still_the_lock_file(descriptor):
            os.close(descriptor)
            return False

        self.descriptor = descriptor
        return True

    def __enter__(self):
        wait = float(os.environ.get("COCKPIT_MIGRATION_LOCK_WAIT", LOCK_WAIT_SECONDS))
        deadline = time.monotonic() + wait
        has_waited = False

        while not self.try_to_take():
            if not has_waited:
                has_waited = True
                reach("waiting", can_fail=False)

            if time.monotonic() >= deadline:
                raise LockBusy("another session is migrating the saved setup")

            time.sleep(LOCK_RETRY_SECONDS)

        return self

    def __exit__(self, *_):
        try:
            if os.fstat(self.descriptor).st_size == 0:
                remove_file(self.path)
        finally:
            os.close(self.descriptor)


class Migration:
    def __init__(self, root, state, ledger):
        self.root = root
        self.ledger = ledger
        self.known, self.extra, body = state
        self.app_body, user = split_user(body)
        self.user_text = user_file_text(self.known, user)
        self.slug = slug_from(body)
        self.project = os.path.join("projects", self.slug)
        self.state_mode = mode_of(self.at_root(LEGACY_STATE_FILE))
        self.backup = None

    def at_root(self, *parts):
        return os.path.join(self.root, *parts)

    def is_committed(self):
        return os.path.lexists(self.at_root(USER_FILE))

    def ensure_directory(self, relative, mode=0o777):
        path = self.at_root(relative)

        if os.path.isdir(path):
            return

        if os.path.lexists(path):
            raise MigrationError("{} is not a folder".format(relative))

        self.ledger.record(CREATED_DIRECTORY, relative)
        os.mkdir(path, mode)

    def claim(self, *parts):
        relative = os.path.join(*parts)

        if os.path.lexists(self.at_root(relative)):
            raise MigrationError("{} already exists".format(relative))

        self.ledger.record(CREATED_FILE, relative)
        return self.at_root(relative)

    def undo_interrupted_run(self):
        if self.is_committed():
            raise MigrationError("{} is not a file".format(USER_FILE))

        if not self.ledger.undo(self.root):
            raise MigrationError("an interrupted update could not be undone")

    def roll_back(self):
        if self.is_committed():
            return

        for number in HANDLED_SIGNALS:
            signal.signal(number, signal.SIG_IGN)

        try:
            self.ledger.undo(self.root)
        except Exception:
            pass

    def back_up(self):
        self.ensure_directory(BACKUPS, PRIVATE_DIRECTORY_MODE)
        relative = os.path.join(BACKUPS, free_backup_name(self.root))
        final = self.at_root(relative)
        partial = final + ".partial"

        self.ledger.record(CREATED_BACKUP, relative)
        os.mkdir(partial, PRIVATE_DIRECTORY_MODE)

        for name in os.listdir(self.root):
            if name != LOCK_NAME and is_plain_file(self.at_root(name)):
                shutil.copy2(self.at_root(name), partial)

        os.rename(partial, final)
        self.backup = final

    def import_topic(self, source_name, *target):
        source = self.at_root(source_name)

        if os.path.isfile(source):
            write_file(self.claim(*target), IMPORTED_HEADING + read_bytes(source), mode_of(source))

    def import_memory(self):
        self.ensure_directory(os.path.join(self.project, "memory"))

        for topic in PROJECT_TOPICS:
            self.import_topic(topic + ".md", self.project, "memory", topic + ".md")

        if os.path.isfile(self.at_root("preferences.md")):
            self.ensure_directory("memory")
            self.import_topic("preferences.md", "memory", "preferences.md")

    def build(self):
        self.ensure_directory("projects")
        self.ensure_directory(self.project)

        project_text = project_file_text(self.known, self.extra, self.app_body)
        write_file(self.claim(self.project, LEGACY_STATE_FILE), as_bytes(project_text), self.state_mode)
        self.import_memory()

        for name in PROJECT_FILES:
            if os.path.isfile(self.at_root(name)):
                shutil.copy2(self.at_root(name), self.claim(self.project, name))

        if any(os.path.lexists(self.at_root(name)) for name in LINKED_DIRECTORIES):
            write_file(self.claim(self.project, ".relink"), b"")

    def move_directories(self):
        for name in MOVED_DIRECTORIES:
            source = self.at_root(name)
            relative = os.path.join(self.project, name)

            if not os.path.lexists(source):
                continue

            if os.path.lexists(self.at_root(relative)):
                raise MigrationError("{} already exists".format(relative))

            self.ledger.record(MOVED, relative)
            os.rename(source, self.at_root(relative))

    def commit(self):
        temporary = self.at_root(TEMPORARY_USER_FILE)

        self.ledger.record(CREATED_FILE, TEMPORARY_USER_FILE)
        write_file(temporary, as_bytes(self.user_text), self.state_mode, replace=True)
        os.rename(temporary, self.at_root(USER_FILE))


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
    sys.stdout.flush()


def announce_newer():
    print("state: written by a newer cockpit, left untouched")
    return NEWER_SCHEMA_STATUS


def migrate(root, state, ledger):
    migration = Migration(root, state, ledger)

    try:
        migration.undo_interrupted_run()
        migration.back_up()
        reach("backed-up")
        migration.build()
        reach("built")
        migration.move_directories()
        reach("renamed")
        migration.commit()
    except BaseException:
        migration.roll_back()
        raise

    ledger.discard()
    announce_update()
    reach("committed", can_fail=False)
    retire_legacy_files(root, migration.backup)


def finish_cleanup(root):
    names = backup_names(root)

    try:
        if not names:
            os.makedirs(os.path.join(root, BACKUPS), mode=PRIVATE_DIRECTORY_MODE, exist_ok=True)
            names = [free_backup_name(root)]
            os.mkdir(os.path.join(root, BACKUPS, names[-1]), PRIVATE_DIRECTORY_MODE)
    except OSError:
        return

    retire_legacy_files(root, os.path.join(root, BACKUPS, names[-1]))


def pending_work(root):
    cockpit_path = os.path.join(root, USER_FILE)
    state_path = os.path.join(root, LEGACY_STATE_FILE)

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


def carry_out(root, ledger):
    work, state = pending_work(root)

    if work == NEWER:
        return announce_newer()

    if work == MIGRATION:
        migrate(root, state, ledger)

    if work == CLEANUP:
        ledger.discard()
        finish_cleanup(root)

    return 0


def run(root):
    work, _ = pending_work(root)

    if work == NEWER:
        return announce_newer()

    if work == NOTHING:
        return 0

    try:
        with Lock(root) as lock:
            return carry_out(root, Ledger(lock.descriptor))
    except LockBusy:
        if work == CLEANUP:
            return 0

        raise


def main():
    for number in HANDLED_SIGNALS:
        signal.signal(number, interrupt)

    try:
        return run(sys.argv[1])
    except Interrupted as interruption:
        return SIGNAL_STATUS_BASE + interruption.number
    except Exception as error:
        print("migration: failed ({})".format(describe(error)))
        return 0


sys.exit(main())
