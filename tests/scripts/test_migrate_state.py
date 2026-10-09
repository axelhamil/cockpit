import fcntl
import os
import shutil
import signal
import subprocess
import sys
import time

from support import SCRIPTS_DIR, SHELL, ScriptTestCase

PROJECT = "projects/acme-studio"
UPDATED = "state: updated to version 2\n"
SET_ASIDE = "state: version 1 files set aside\n"
NEWER = "state: written by a newer cockpit, left untouched\n"
BUSY = "migration: failed (another session is migrating the saved setup)\n"
UNTRUSTED = "migration: failed (the list left by an interrupted update cannot be trusted)\n"
PROJECT_LINE = "- Project: Acme Studio (11111111-1111-1111-1111-111111111111)\n"
IMPORTED = "## Imported\n\n".encode()
CHANGED = ".changed-after-backup"
HOLD_THE_LOCK = (
    "import fcntl, sys\n"
    "handle = open(sys.argv[1], 'a')\n"
    "fcntl.flock(handle, fcntl.LOCK_EX)\n"
    "print('locked', flush=True)\n"
    "sys.stdin.read()\n"
)
ROOT_TEXT_FILES = (
    "state.md",
    "domain.md",
    "schema.md",
    "codebase.md",
    "tools.md",
    "preferences.md",
    "journal.md",
    "proposals.md",
    "handoff.md",
    "report.txt",
)
MIGRATED_FILES = {
    "cockpit.md",
    "proposals.md",
    "memory/preferences.md",
    PROJECT + "/state.md",
    PROJECT + "/journal.md",
    PROJECT + "/handoff.md",
    PROJECT + "/report.txt",
    PROJECT + "/.relink",
    PROJECT + "/memory/domain.md",
    PROJECT + "/memory/schema.md",
    PROJECT + "/memory/codebase.md",
    PROJECT + "/memory/tools.md",
    PROJECT + "/saas-project/.keep",
    PROJECT + "/tools-project/.keep",
    PROJECT + "/repo/src/app.txt",
    PROJECT + "/secrets/metabase.key",
}
COCKPIT_FILE = (
    "---\n"
    "schema_version: 2\n"
    "language: fr\n"
    "plugin_version: 1.6.0\n"
    "dependencies: git, railway, gh\n"
    "---\n"
    "\n"
    "## User\n"
    "- Name: Alex Morgan\n"
    "- Email: alex@example.com\n"
)
PROJECT_STATE_HEADER = "---\nprovider: railway\nonboarding: complete\nonboarding_step: check\n---\n"


def files_of(snapshot):
    return {name for name, (kind, _, _) in snapshot.items() if kind == "file"}


def without_backups(snapshot):
    return {name: entry for name, entry in snapshot.items() if not name.startswith("backups")}


class MigrateStateTest(ScriptTestCase):
    def migrate(self, home=None, **environment):
        return self.run_script("migrate-state.sh", env={"COCKPIT_HOME": home or self.home, **environment})

    def start_migration(self, **environment):
        process = subprocess.Popen(
            [SHELL, os.path.join(SCRIPTS_DIR, "migrate-state.sh")],
            env={**self.env, **environment},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.addCleanup(process.kill)
        return process

    def wait_until_stopped(self, process):
        deadline = time.monotonic() + 60

        while time.monotonic() < deadline:
            pid, status = os.waitpid(process.pid, os.WUNTRACED | os.WNOHANG)

            if pid == 0:
                time.sleep(0.01)
                continue

            self.assertTrue(os.WIFSTOPPED(status), "the migration ended instead of waiting for the lock")
            return

        self.fail("the migration never waited for the lock")

    def backup_directories(self, home=None):
        backups = os.path.join(home or self.home, "backups")
        return sorted(os.listdir(backups)) if os.path.isdir(backups) else []

    def finished_tree(self):
        home = self.path("finished")
        self.build_state_v1(home)
        self.migrate(home)
        return home

    def test_given_a_version_1_state_then_the_app_gets_its_own_folder_and_nothing_is_lost(self):
        self.build_state_v1()
        before = self.snapshot()

        result = self.migrate()
        after = self.snapshot()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, UPDATED)
        self.assertEqual(files_of(without_backups(after)), MIGRATED_FILES)
        self.assertEqual(after["cockpit.md"][2].decode(), COCKPIT_FILE)

        project_state = after[PROJECT + "/state.md"][2].decode()
        self.assertTrue(project_state.startswith(PROJECT_STATE_HEADER + "\n## Profile\n"))
        self.assertNotIn("- User:", project_state)
        self.assertNotIn("- Clone:", project_state)
        self.assertIn("- Project: Acme Studio (11111111-1111-1111-1111-111111111111)", project_state)
        self.assertIn("- Project: Acme Studio tools (22222222-2222-2222-2222-222222222222)", project_state)
        self.assertIn("- 2026-10-08: signup page fails on Safari", project_state)

        for topic in ("domain", "schema", "codebase", "tools"):
            self.assertEqual(after["{}/memory/{}.md".format(PROJECT, topic)][2], IMPORTED + before[topic + ".md"][2])
        self.assertEqual(after["memory/preferences.md"][2], IMPORTED + before["preferences.md"][2])

        for name in ("journal.md", "handoff.md", "report.txt"):
            self.assertEqual(after[PROJECT + "/" + name], before[name])
        self.assertEqual(after["proposals.md"], before["proposals.md"])

        for name in ("saas-project/.keep", "tools-project/.keep", "repo/src/app.txt", "secrets/metabase.key"):
            self.assertEqual(after[PROJECT + "/" + name], before[name])
        self.assertEqual(after[PROJECT + "/secrets/metabase.key"][1], 0o600)
        self.assertEqual(after[PROJECT + "/secrets"][1], 0o700)

        self.assertFalse(self.exists("cockpit-home/.migrating"))
        for leftover in ("state.md", "domain.md", "preferences.md", "journal.md", "repo", "secrets", "saas-project"):
            self.assertFalse(self.exists("cockpit-home/" + leftover), leftover)

    def test_given_a_version_1_state_then_every_root_text_file_is_in_the_backup(self):
        self.build_state_v1()
        before = self.snapshot()

        self.migrate()
        after = self.snapshot()
        backups = self.backup_directories()

        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].startswith("v1-"))
        for name in ROOT_TEXT_FILES:
            self.assertEqual(after["backups/{}/{}".format(backups[0], name)], before[name], name)
        for rebuildable in ("repo", "saas-project", "tools-project", "secrets", ".migrating"):
            self.assertNotIn("backups/{}/{}".format(backups[0], rebuildable), after)

    def test_given_a_migration_already_done_then_a_rerun_prints_and_changes_nothing(self):
        self.build_state_v1()
        self.migrate()
        done = self.snapshot()

        rerun = self.migrate()

        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(rerun.stdout, "")
        self.assertEqual(self.snapshot(), done)

    def test_given_private_version_1_files_then_what_is_rebuilt_from_them_stays_private(self):
        self.build_state_v1()
        for name in ("state.md", "domain.md", "preferences.md"):
            os.chmod(self.path("cockpit-home", name), 0o600)

        self.migrate()
        after = self.snapshot()

        for name in ("cockpit.md", PROJECT + "/state.md", PROJECT + "/memory/domain.md", "memory/preferences.md"):
            self.assertEqual(after[name][1], 0o600, name)

    def test_given_windows_line_ends_and_bytes_that_are_not_utf_8_then_they_survive_untouched(self):
        body = b"\r\n## Profile\r\n- Usages: caf\xe9 \xff\r\n\r\n## SaaS project\r\n- Project: Acme Studio (1)\r\n"
        domain = b"- Client actif : pay\xe9 \xff\r\n- Essai\r\n"
        os.makedirs(self.home, exist_ok=True)
        with open(self.path("cockpit-home/state.md"), "wb") as handle:
            handle.write(b"---\r\nschema_version: 1\r\nlanguage: fr\r\n---\r\n" + body)
        with open(self.path("cockpit-home/domain.md"), "wb") as handle:
            handle.write(domain)
        before = self.snapshot()

        result = self.migrate()
        after = self.snapshot()
        backup = "backups/" + self.backup_directories()[0]

        self.assertEqual(result.stdout, UPDATED)
        self.assertEqual(after[PROJECT + "/state.md"][2], b"---\nprovider: railway\n---\n" + body)
        self.assertEqual(after[PROJECT + "/memory/domain.md"][2], IMPORTED + domain)
        self.assertEqual(after[backup + "/state.md"], before["state.md"])
        self.assertEqual(after[backup + "/domain.md"], before["domain.md"])

    def test_given_a_state_without_a_railway_project_yet_then_the_app_is_named_app(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\nlanguage: en\nonboarding: in-progress\nonboarding_step: plan\n---\n\n## Profile\n- User: Alex\n")

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(self.exists("cockpit-home/projects/app/state.md"))
        self.assertIn("- User: Alex\n", self.read("cockpit-home/cockpit.md"))
        self.assertFalse(self.exists("cockpit-home/projects/app/.relink"))

    def test_given_a_project_name_with_accents_and_symbols_then_the_folder_name_is_plain(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n\n## SaaS project\n- Project: Café & Co! (11111111-1111-1111-1111-111111111111)\n")

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(self.exists("cockpit-home/projects/cafe-co/state.md"))

    def test_given_a_very_long_project_name_then_the_folder_name_stops_at_40_characters(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n\n## SaaS project\n- Project: {}(1)\n".format("abcd " * 60))

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertEqual(os.listdir(self.path("cockpit-home/projects")), ["-".join(["abcd"] * 8)])

    def test_given_a_state_folder_with_spaces_and_brackets_then_the_migration_still_works(self):
        home = self.path("my home [work]/.cockpit")
        self.build_state_v1(home)

        result = self.migrate(home)

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(os.path.isfile(os.path.join(home, "projects", "acme-studio", "secrets", "metabase.key")))

    def test_given_a_state_whose_header_never_closes_then_nothing_is_attempted(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\nlanguage: fr\n")
        before = self.snapshot()

        result = self.migrate()

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(self.snapshot(), before)

    def test_given_a_mac_without_python_then_the_failure_is_reported_and_version_1_is_left_alone(self):
        self.build_state_v1()
        before = self.snapshot()

        result = self.migrate(PATH=self.isolated_path("dirname", "uname"))

        self.assertIn("migration: failed (python3 is not available)", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_given_a_run_cut_dead_at_any_step_then_the_next_run_ends_in_the_same_state(self):
        expected = without_backups(self.snapshot(self.finished_tree()))

        for stage in ("backed-up", "built", "renamed", "committed"):
            with self.subTest(stage=stage):
                home = self.path("interrupted-" + stage)
                self.build_state_v1(home)
                announced_first = UPDATED if stage == "committed" else ""

                interrupted = self.migrate(home, COCKPIT_MIGRATION_KILL_AT=stage)
                resumed = self.migrate(home)
                later = self.migrate(home)

                self.assertNotEqual(interrupted.returncode, 0)
                self.assertEqual(interrupted.stdout + resumed.stdout, UPDATED)
                self.assertEqual(interrupted.stdout, announced_first)
                self.assertEqual((later.returncode, later.stdout), (0, ""))
                self.assertEqual(without_backups(self.snapshot(home)), expected)

    def test_given_a_run_stopped_before_it_could_announce_then_the_next_run_announces_once(self):
        expected = without_backups(self.snapshot(self.finished_tree()))

        for stop, status in (("written", 70), ("written:TERM", 128 + signal.SIGTERM)):
            with self.subTest(stop=stop):
                home = self.path("unannounced-" + stop.replace(":", "-"))
                self.build_state_v1(home)

                stopped = self.migrate(home, COCKPIT_MIGRATION_KILL_AT=stop)
                resumed = self.migrate(home)
                later = self.migrate(home)

                self.assertEqual((stopped.returncode, stopped.stdout), (status, ""))
                self.assertEqual((resumed.returncode, resumed.stdout), (0, UPDATED))
                self.assertEqual((later.returncode, later.stdout), (0, ""))
                self.assertEqual(without_backups(self.snapshot(home)), expected)

    def test_given_a_recovery_list_naming_client_files_then_the_run_fails_and_none_of_them_is_touched(self):
        self.build_state_v1()
        self.write("cockpit-home/backups/v1-20200101-000000/state.md", "an older backup\n")
        self.write("cockpit-home/projects/other-app/state.md", "another app\n")
        self.write("cockpit-home/memory/notes.md", "mine\n")
        self.write(
            "cockpit-home/.migrating",
            "file domain.md\n"
            "file state.md\n"
            "file secrets/metabase.key\n"
            "file memory/notes.md\n"
            "file projects/other-app/state.md\n"
            "file projects/acme-studio/../../journal.md\n"
            "directory secrets\n"
            "directory repo\n"
            "move secrets\n"
            "move projects/other-app/repo\n"
            "backup backups/v1-20200101-000000\n"
            "backup backups\n",
        )
        before = self.snapshot()

        result = self.migrate()
        rerun = self.migrate()

        self.assertEqual(result.stdout, UNTRUSTED)
        self.assertEqual(rerun.stdout, UNTRUSTED)
        self.assertEqual(self.snapshot(), before)

    def test_given_the_app_got_its_name_after_a_run_cut_dead_then_one_folder_holds_everything(self):
        expected = without_backups(self.snapshot(self.finished_tree()))

        for stage in ("built", "renamed"):
            with self.subTest(stage=stage):
                home = self.path("named-after-" + stage)
                self.build_state_v1(home)
                state = os.path.join(home, "state.md")
                with open(state, encoding="utf-8") as handle:
                    named = handle.read()
                with open(state, "w", encoding="utf-8") as handle:
                    handle.write(named.replace(PROJECT_LINE, ""))

                interrupted = self.migrate(home, COCKPIT_MIGRATION_KILL_AT=stage)
                with open(state, "w", encoding="utf-8") as handle:
                    handle.write(named)
                resumed = self.migrate(home)
                later = self.migrate(home)

                self.assertEqual(interrupted.stdout + resumed.stdout, UPDATED)
                self.assertEqual((later.returncode, later.stdout), (0, ""))
                self.assertEqual(os.listdir(os.path.join(home, "projects")), ["acme-studio"])
                self.assertEqual(without_backups(self.snapshot(home)), expected)

    def test_given_a_root_file_changed_after_the_commit_then_it_is_set_aside_in_the_backup(self):
        self.build_state_v1()
        self.migrate(COCKPIT_MIGRATION_KILL_AT="committed")
        with open(self.path("cockpit-home/state.md"), "a", encoding="utf-8") as handle:
            handle.write("- written by a session of the old version\n")
        changed = self.snapshot()["state.md"]

        resumed = self.migrate()
        after = self.snapshot()
        later = self.migrate()

        self.assertEqual((resumed.returncode, resumed.stdout), (0, SET_ASIDE))
        self.assertEqual(files_of(without_backups(after)), MIGRATED_FILES)
        self.assertEqual(after["backups/{}/state.md{}".format(self.backup_directories()[0], CHANGED)], changed)
        self.assertEqual((later.returncode, later.stdout), (0, ""))
        self.assertEqual(self.snapshot(), after)

    def test_given_version_1_files_written_after_the_move_then_they_are_set_aside_and_said_once(self):
        self.build_state_v1()
        self.migrate()
        migrated = self.snapshot()
        backup = "backups/" + self.backup_directories()[0]
        self.write("cockpit-home/journal.md", "- 2026-10-09: written by a window opened before the update\n")
        self.write("cockpit-home/domain.md", "- Churn: an account with no paid invoice for 60 days.\n")
        written = self.snapshot()

        result = self.migrate()
        after = self.snapshot()
        rerun = self.migrate()

        self.assertEqual((result.returncode, result.stdout), (0, SET_ASIDE))
        self.assertEqual(after.pop(backup + "/journal.md" + CHANGED), written["journal.md"])
        self.assertEqual(after.pop(backup + "/domain.md" + CHANGED), written["domain.md"])
        self.assertEqual(after, migrated)
        self.assertEqual((rerun.returncode, rerun.stdout), (0, ""))

        self.write("cockpit-home/journal.md", "- 2026-10-10: written again by the same window\n")
        again = self.snapshot()["journal.md"]

        self.assertEqual(self.migrate().stdout, SET_ASIDE)
        self.assertEqual(self.snapshot()[backup + "/journal.md" + CHANGED + "-2"], again)
        self.assertEqual(self.snapshot()[backup + "/journal.md" + CHANGED], written["journal.md"])

    def test_given_the_backup_was_deleted_before_the_cleanup_then_the_root_files_get_a_new_one(self):
        self.build_state_v1()
        before = self.snapshot()
        self.migrate(COCKPIT_MIGRATION_KILL_AT="committed")
        shutil.rmtree(self.path("cockpit-home/backups"))

        resumed = self.migrate()
        after = self.snapshot()

        self.assertEqual((resumed.returncode, resumed.stdout), (0, SET_ASIDE))
        self.assertEqual(files_of(without_backups(after)), MIGRATED_FILES)
        self.assertEqual(after["backups/{}/journal.md{}".format(self.backup_directories()[0], CHANGED)], before["journal.md"])

    def test_given_a_state_file_that_is_a_link_then_the_link_ends_in_the_backup(self):
        self.build_state_v1()
        real = self.path("real-state.md")
        os.rename(self.path("cockpit-home/state.md"), real)
        os.symlink(real, self.path("cockpit-home/state.md"))

        result = self.migrate()
        saved = self.path("cockpit-home/backups", self.backup_directories()[0], "state.md" + CHANGED)

        self.assertEqual(result.stdout, UPDATED + SET_ASIDE)
        self.assertFalse(os.path.lexists(self.path("cockpit-home/state.md")))
        self.assertTrue(os.path.islink(saved))
        self.assertTrue(os.path.isfile(real))
        self.assertEqual(self.migrate().stdout, "")

    def test_given_a_failure_before_the_commit_point_then_version_1_is_left_byte_for_byte(self):
        for stage in ("backed-up", "built", "renamed"):
            with self.subTest(stage=stage):
                home = self.path("failing-" + stage)
                self.build_state_v1(home)
                before = self.snapshot(home)

                result = self.migrate(home, COCKPIT_MIGRATION_FAIL_AT=stage)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "migration: failed (stopped on purpose after {})\n".format(stage))
                self.assertEqual(self.snapshot(home), before)

    def test_given_a_stop_signal_before_the_commit_point_then_version_1_is_left_byte_for_byte(self):
        for name in ("TERM", "HUP", "INT"):
            with self.subTest(signal=name):
                home = self.path("signalled-" + name)
                self.build_state_v1(home)
                before = self.snapshot(home)

                result = self.migrate(home, COCKPIT_MIGRATION_KILL_AT="renamed:" + name)

                self.assertEqual(result.returncode, 128 + getattr(signal, "SIG" + name), result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(self.snapshot(home), before)

    def test_given_a_stop_signal_after_the_commit_point_then_nothing_is_undone(self):
        expected = without_backups(self.snapshot(self.finished_tree()))
        self.build_state_v1()

        stopped = self.migrate(COCKPIT_MIGRATION_KILL_AT="committed:TERM")
        resumed = self.migrate()

        self.assertEqual((stopped.returncode, stopped.stdout), (128 + signal.SIGTERM, UPDATED))
        self.assertEqual((resumed.returncode, resumed.stdout), (0, ""))
        self.assertEqual(without_backups(self.snapshot()), expected)

    def test_given_an_undo_that_fails_in_part_then_the_cause_is_reported_and_the_next_run_finishes(self):
        expected = without_backups(self.snapshot(self.finished_tree()))
        self.build_state_v1()

        failed = self.migrate(COCKPIT_MIGRATION_FAIL_AT="renamed,rollback")
        left = self.snapshot()
        resumed = self.migrate()

        self.assertEqual(failed.stdout, "migration: failed (stopped on purpose after renamed)\n")
        self.assertNotIn("cockpit.md", left)
        self.assertNotIn(PROJECT + "/state.md", left)
        self.assertNotIn(PROJECT + "/memory", left)
        self.assertIn(PROJECT + "/secrets/metabase.key", left)
        self.assertIn("journal.md", left)
        self.assertEqual(resumed.stdout, UPDATED)
        self.assertEqual(without_backups(self.snapshot()), expected)

    def test_given_files_already_where_the_new_ones_go_then_the_run_fails_and_they_survive(self):
        self.build_state_v1()
        self.write("cockpit-home/memory/preferences.md", "mine\n")
        self.write("cockpit-home/" + PROJECT + "/journal.md", "mine too\n")
        before = self.snapshot()

        for seams in ({}, {"COCKPIT_MIGRATION_FAIL_AT": "backed-up"}):
            with self.subTest(seams=seams):
                result = self.migrate(**seams)

                self.assertTrue(result.stdout.startswith("migration: failed ("), result.stdout)
                self.assertEqual(self.snapshot(), before)

    def test_given_a_file_where_the_projects_folder_should_go_then_the_failure_is_real_and_clean(self):
        self.build_state_v1()
        self.write("cockpit-home/projects", "not a folder")
        before = self.snapshot()

        result = self.migrate()

        self.assertEqual(result.stdout, "migration: failed (projects is not a folder)\n")
        self.assertEqual(self.snapshot(), before)

    def test_given_a_folder_where_the_lock_file_should_go_then_the_failure_is_plain_and_clean(self):
        self.build_state_v1()
        os.makedirs(self.path("cockpit-home/.migrating"))
        before = self.snapshot()

        result = self.migrate()

        self.assertEqual(result.stdout, "migration: failed (a folder named .migrating is in the way)\n")
        self.assertEqual(self.snapshot(), before)

    def test_given_a_link_where_the_lock_file_should_go_then_the_link_is_not_followed(self):
        self.build_state_v1()
        self.write("elsewhere.md", "file domain.md\n")
        os.symlink(self.path("elsewhere.md"), self.path("cockpit-home/.migrating"))
        before = self.snapshot()

        result = self.migrate()

        self.assertEqual(result.stdout, "migration: failed (a link named .migrating is in the way)\n")
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(os.path.islink(self.path("cockpit-home/.migrating")))
        self.assertEqual(self.read("elsewhere.md"), "file domain.md\n")

    def test_given_a_lock_that_fails_for_another_reason_then_no_other_session_is_blamed(self):
        self.build_state_v1()
        before = self.snapshot()
        self.write(
            "patches/sitecustomize.py",
            "import errno\nimport fcntl\n\n\n"
            "def flock(*_):\n    raise OSError(errno.ENOLCK, 'No locks available')\n\n\n"
            "fcntl.flock = flock\n",
        )

        result = self.migrate(PYTHONPATH=self.path("patches"), COCKPIT_MIGRATION_LOCK_WAIT="600")
        after = self.snapshot()
        after.pop(".migrating", None)

        self.assertEqual(result.stdout, "migration: failed (the saved setup could not be locked)\n")
        self.assertEqual(after, before)

    def test_given_another_session_is_migrating_then_this_one_leaves_everything_alone(self):
        self.build_state_v1()
        holder = subprocess.Popen(
            [sys.executable, "-c", HOLD_THE_LOCK, self.path("cockpit-home/.migrating")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        self.addCleanup(holder.wait)
        self.addCleanup(holder.stdin.close)
        self.addCleanup(holder.stdout.close)
        self.assertEqual(holder.stdout.readline(), "locked\n")
        before = self.snapshot()

        result = self.migrate(COCKPIT_MIGRATION_LOCK_WAIT="0.3")

        self.assertEqual((result.returncode, result.stdout), (0, BUSY))
        self.assertEqual(self.snapshot(), before)

    def test_given_another_session_finishes_the_migration_first_then_this_one_changes_nothing(self):
        finished_home = self.finished_tree()
        expected = without_backups(self.snapshot(finished_home))
        self.build_state_v1()

        with open(self.path("cockpit-home/.migrating"), "a") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            waiting = self.start_migration(COCKPIT_MIGRATION_LOCK_WAIT="60", COCKPIT_MIGRATION_KILL_AT="waiting:STOP")
            self.wait_until_stopped(waiting)

            for name in os.listdir(self.home):
                path = os.path.join(self.home, name)

                if name == ".migrating":
                    continue

                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

            for name in os.listdir(finished_home):
                os.rename(os.path.join(finished_home, name), os.path.join(self.home, name))

            os.kill(waiting.pid, signal.SIGCONT)

        stdout, stderr = waiting.communicate(timeout=60)

        self.assertEqual(without_backups(self.snapshot()), expected)
        self.assertEqual((waiting.returncode, stdout), (0, ""), stderr)
        self.assertEqual(len(self.backup_directories()), 1)

    def test_given_another_session_holds_the_lock_during_the_cleanup_then_this_one_stays_silent(self):
        self.build_state_v1()
        self.migrate(COCKPIT_MIGRATION_KILL_AT="committed")
        before = self.snapshot()

        with open(self.path("cockpit-home/.migrating"), "a") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            result = self.migrate(COCKPIT_MIGRATION_LOCK_WAIT="0.3")

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(self.snapshot(), before)

    def test_given_a_state_written_by_a_newer_cockpit_then_it_is_left_untouched(self):
        for name, content in (
            ("cockpit.md", "---\nschema_version: 3\nlanguage: fr\n---\n"),
            ("state.md", "---\nschema_version: 3\nlanguage: fr\n---\n"),
        ):
            with self.subTest(file=name):
                home = self.path("newer-" + name)
                os.makedirs(home)
                with open(os.path.join(home, name), "w", encoding="utf-8") as handle:
                    handle.write(content)
                before = self.snapshot(home)

                result = self.migrate(home)

                self.assertEqual(result.returncode, 3)
                self.assertEqual(result.stdout, NEWER)
                self.assertEqual(self.snapshot(home), before)

    def test_given_no_state_then_nothing_happens(self):
        result = self.migrate()

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(self.snapshot(), {})
