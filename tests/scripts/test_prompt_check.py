import json
import os
import unittest

from support import ScriptTestCase

LOUD_WORDS = ("MANDATORY", "CRITICAL", "MUST")

FAKE_PYTHON = 'touch "$PYTHON_CALLED"\nexit 1\n'


class PromptCheckTest(ScriptTestCase):
    def check(self, stdin=None):
        payload = json.dumps(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "hello",
                "cwd": self.workspace,
            }
        )
        return self.run_script(
            "prompt-check.sh", stdin=payload if stdin is None else stdin
        )

    def assert_one_calm_line(self, output):
        lines = output.splitlines()
        self.assertEqual(len(lines), 1, output)
        self.assertLess(len(lines[0].split()), 40, lines[0])
        for word in LOUD_WORDS:
            self.assertNotIn(word, lines[0])
        return lines[0]

    def test_given_no_state_then_prints_nothing(self):
        result = self.check()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_given_onboarding_in_progress_then_prints_nothing(self):
        self.write_v2_state("shop", onboarding="in-progress")

        result = self.check()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_given_one_complete_app_then_names_it_in_one_short_line(self):
        self.write_v2_state("shop")

        result = self.check()

        self.assertEqual(result.returncode, 0, result.stderr)
        line = self.assert_one_calm_line(result.stdout)
        self.assertIn("shop", line)
        self.assertIn("code-changes", line)

    def test_given_several_complete_apps_then_names_none(self):
        self.write_v2_state("shop", "admin")

        result = self.check()

        self.assertEqual(result.returncode, 0, result.stderr)
        line = self.assert_one_calm_line(result.stdout)
        self.assertNotIn("shop", line)
        self.assertNotIn("admin", line)
        self.assertIn("cockpit skill", line)

    def install_python_trap(self):
        self.install_command("python3", FAKE_PYTHON)
        self.env["PYTHON_CALLED"] = self.path("python-called")
        self.env["PATH"] = self.path("bin") + os.pathsep + self.env["PATH"]

    def test_given_no_state_folder_then_python_is_never_started(self):
        self.install_python_trap()

        self.env["COCKPIT_HOME"] = self.path("missing")

        result = self.check()

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse(self.exists("python-called"))

    def test_given_a_mac_without_command_line_tools_then_python_is_never_started(self):
        self.write_v2_state("shop")
        self.install_python_trap()
        self.install_command("uname", "echo Darwin\n")
        self.install_command("xcode-select", "exit 2\n")

        result = self.check()

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse(self.exists("python-called"))

    def test_given_unreadable_stdin_then_still_exits_zero(self):
        self.write_v2_state("shop")

        result = self.check(stdin="\x00not json{")

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
