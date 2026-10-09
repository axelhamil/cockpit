import os
import signal
import subprocess
import time

from support import SCRIPTS_DIR, SHELL, ScriptTestCase

TOOLS_SECTION = "## Tools project\n"
TOOLS_LINE = "- Project: Acme Studio tools (22222222-2222-2222-2222-222222222222)\n"
SAAS_ID = "11111111-1111-1111-1111-111111111111"
TOOLS_ID = "22222222-2222-2222-2222-222222222222"
APP_STATE = (
    "---\nprovider: railway\nonboarding: complete\nonboarding_step: check\n---\n\n"
    "## SaaS project\n"
    "- Project: Acme Studio ({})\n"
    "- Production environment: production\n"
    "- App service: web, repository acme/app, deployed branch main\n"
    "- Postgres service: Postgres\n\n"
    "## Tools project\n"
    "- Project: Acme Studio tools ({})\n"
).format(SAAS_ID, TOOLS_ID)


class RelinkTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.write_v2_state("acme-studio")
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE)
        self.write("cockpit-home/projects/acme-studio/saas-project/.keep", "")
        self.write("cockpit-home/projects/acme-studio/tools-project/.keep", "")
        self.write("cockpit-home/projects/acme-studio/.relink", "")
        self.log = self.path("railway.log")

    def railway_records(self, exit_code=0):
        self.install_fake_railway('{ pwd; echo "$@"; } >>"' + self.log + '"\nexit ' + str(exit_code) + "\n")

    def relink(self, *arguments):
        return self.run_script("relink.sh", *arguments)

    def test_given_the_folders_were_moved_then_each_one_is_linked_again_and_the_marker_goes(self):
        self.railway_records()
        project = self.path("cockpit-home/projects/acme-studio")

        result = self.relink("--project", "acme-studio")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.read("railway.log").splitlines(),
            [
                project + "/saas-project",
                "link -p {} -e production -s web".format(SAAS_ID),
                project + "/tools-project",
                "link -p {} -e production".format(TOOLS_ID),
            ],
        )
        self.assertFalse(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_railway_refuses_then_the_marker_stays_and_the_error_says_what_to_check(self):
        self.railway_records(exit_code=1)

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertIn("railway whoami", result.stderr)
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_nothing_to_refresh_then_railway_is_not_called(self):
        self.railway_records()
        self.relink()
        self.write("railway.log", "")

        result = self.relink()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("railway.log"), "")

    def test_given_an_id_that_could_pass_for_an_option_then_railway_is_not_called(self):
        self.railway_records()
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE.replace(SAAS_ID, "--help"))

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.exists("railway.log"))
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_railway_refuses_the_tools_folder_then_the_marker_stays(self):
        self.install_fake_railway('case $(pwd) in *tools-project) exit 1 ;; esac\nexit 0\n')

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_a_refused_tools_id_then_railway_is_never_run_and_the_marker_stays(self):
        self.railway_records()
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE.replace(TOOLS_ID, "-x"))

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.exists("railway.log"))
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_a_tools_folder_with_nothing_recorded_then_the_app_folder_is_linked_and_the_marker_goes(self):
        project = self.path("cockpit-home/projects/acme-studio")

        for name, state in (("no-section", APP_STATE.replace(TOOLS_SECTION + TOOLS_LINE, "")), ("no-line", APP_STATE.replace(TOOLS_LINE, ""))):
            with self.subTest(state=name):
                self.railway_records()
                self.write("railway.log", "")
                self.write("cockpit-home/projects/acme-studio/state.md", state)
                self.write("cockpit-home/projects/acme-studio/.relink", "")

                result = self.relink()

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    self.read("railway.log").splitlines(),
                    [project + "/saas-project", "link -p {} -e production -s web".format(SAAS_ID)],
                )
                self.assertFalse(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_a_state_with_windows_line_ends_then_both_folders_are_linked(self):
        self.railway_records()
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE.replace("\n", "\r\n"))

        result = self.relink()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.read("railway.log").splitlines()[1::2],
            ["link -p {} -e production -s web".format(SAAS_ID), "link -p {} -e production".format(TOOLS_ID)],
        )
        self.assertFalse(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_the_relink_is_stopped_while_railway_runs_then_railway_is_stopped_too(self):
        started = self.path("railway.started")
        stopped = self.path("railway.stopped")
        self.install_fake_railway(
            "trap 'kill \"$child\"; : >\"" + stopped + "\"; exit 0' TERM\n"
            "sleep 30 &\nchild=$!\necho $$ >\"" + started + "\"\nwait\n"
        )
        process = subprocess.Popen(
            [SHELL, os.path.join(SCRIPTS_DIR, "relink.sh")],
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(process.kill)
        self.addCleanup(self.stop_fake_railway, started)
        self.assertTrue(self.wait_for(started), "railway was never started")

        process.send_signal(signal.SIGTERM)
        status = process.wait(timeout=10)

        self.assertTrue(self.wait_for(stopped), "railway was left running")
        self.assertEqual(status, 128 + signal.SIGTERM)
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def stop_fake_railway(self, started):
        with open(started, encoding="utf-8") as handle:
            pid = handle.read().strip()

        if not pid:
            return

        deadline = time.monotonic() + 2

        try:
            os.kill(int(pid), signal.SIGTERM)

            while time.monotonic() < deadline:
                os.kill(int(pid), 0)
                time.sleep(0.02)
        except ProcessLookupError:
            pass

    def wait_for(self, path, seconds=5):
        deadline = time.monotonic() + seconds

        while time.monotonic() < deadline:
            if os.path.exists(path):
                return True

            time.sleep(0.02)

        return False
