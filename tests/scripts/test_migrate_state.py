import os
import shutil
import subprocess
import time

from support import SCRIPTS_DIR, SHELL, ScriptTestCase

PROJECT = "projects/acme-studio"
UPDATED = "state: updated to version 2\n"
NEWER = "state: written by a newer cockpit, left untouched\n"
IMPORTED = "## Imported\n\n".encode()
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

    def backup_directories(self, home=None):
        backups = os.path.join(home or self.home, "backups")
        return sorted(os.listdir(backups)) if os.path.isdir(backups) else []

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
        for rebuildable in ("repo", "saas-project", "tools-project", "secrets"):
            self.assertNotIn("backups/{}/{}".format(backups[0], rebuildable), after)

    def test_given_a_migration_already_done_then_a_rerun_prints_and_changes_nothing(self):
        self.build_state_v1()
        self.migrate()
        done = self.snapshot()

        rerun = self.migrate()

        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(rerun.stdout, "")
        self.assertEqual(self.snapshot(), done)

    def test_given_a_state_without_a_railway_project_yet_then_the_app_is_named_app(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\nlanguage: en\nonboarding: in-progress\nonboarding_step: plan\n---\n\n## Profile\n- User: Alex\n")

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(self.exists("cockpit-home/projects/app/state.md"))
        self.assertIn("- User: Alex\n", self.read("cockpit-home/cockpit.md"))
        self.assertFalse(self.exists("cockpit-home/projects/app/.relink"))

    def test_given_a_project_name_with_accents_and_symbols_then_the_folder_name_is_plain(self):
        self.write("cockpit-home/state.md", "---\nschema_version: 1\n---\n\n## SaaS project\n- Project: Caf\u00e9 & Co! (11111111-1111-1111-1111-111111111111)\n")

        result = self.migrate()

        self.assertEqual(result.stdout, UPDATED)
        self.assertTrue(self.exists("cockpit-home/projects/cafe-co/state.md"))

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

    def test_given_an_interruption_at_any_step_then_the_next_run_ends_in_the_same_state(self):
        reference_home = self.path("reference")
        self.build_state_v1(reference_home)
        self.migrate(reference_home)
        expected = without_backups(self.snapshot(reference_home))

        for stage in ("backed-up", "built", "renamed", "committed"):
            with self.subTest(stage=stage):
                home = self.path("interrupted-" + stage)
                self.build_state_v1(home)

                interrupted = self.migrate(home, COCKPIT_MIGRATION_KILL_AT=stage)
                self.assertNotEqual(interrupted.returncode, 0)

                old = time.time() - 3600
                os.utime(os.path.join(home, ".migrating"), (old, old))
                resumed = self.migrate(home)

                self.assertEqual(resumed.stdout, UPDATED)
                snapshot = without_backups(self.snapshot(home))
                self.assertEqual(snapshot, expected)
                self.assertFalse(os.path.exists(os.path.join(home, ".migrating")))

    def test_given_a_failure_before_the_commit_point_then_version_1_is_left_byte_for_byte(self):
        for stage in ("backed-up", "built", "renamed"):
            with self.subTest(stage=stage):
                home = self.path("failing-" + stage)
                self.build_state_v1(home)
                before = self.snapshot(home)

                result = self.migrate(home, COCKPIT_MIGRATION_FAIL_AT=stage)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("migration: failed (stopped on purpose after {})".format(stage), result.stdout)
                self.assertEqual(self.snapshot(home), before)

    def test_given_a_file_where_the_projects_folder_should_go_then_the_failure_is_real_and_clean(self):
        self.build_state_v1()
        self.write("cockpit-home/projects", "not a folder")
        before = self.snapshot()

        result = self.migrate()

        self.assertIn("migration: failed (", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_given_another_session_is_migrating_then_this_one_leaves_everything_alone(self):
        self.build_state_v1()
        os.makedirs(self.path("cockpit-home/.migrating"))
        before = self.snapshot()

        result = self.migrate(COCKPIT_MIGRATION_LOCK_WAIT="0")

        self.assertIn("migration: failed (another session is migrating the saved setup)", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_given_another_session_finishes_the_migration_first_then_this_one_changes_nothing(self):
        finished_home = self.path("finished")
        self.build_state_v1(finished_home)
        self.migrate(finished_home)
        expected = without_backups(self.snapshot(finished_home))

        self.build_state_v1()
        lock = self.path("cockpit-home/.migrating")
        os.makedirs(lock)
        waiting = subprocess.Popen(
            [SHELL, os.path.join(SCRIPTS_DIR, "migrate-state.sh")],
            env={**self.env, "COCKPIT_MIGRATION_LOCK_WAIT": "60"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.addCleanup(waiting.kill)
        time.sleep(1)

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

        os.rmdir(lock)
        stdout, stderr = waiting.communicate(timeout=60)

        self.assertEqual(without_backups(self.snapshot()), expected)
        self.assertEqual((waiting.returncode, stdout), (0, ""), stderr)
        self.assertEqual(len(self.backup_directories()), 1)

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
