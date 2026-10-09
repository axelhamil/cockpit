import os
import shlex
import time

from support import ScriptTestCase

FAKE_GH = """
printf '%s\\n' "$*" >>"$FAKE_GH_LOG"
if [ "$2" = login ] && [ -n "${FAKE_GH_LOGIN_FAILS:-}" ]; then
  echo "error: authorization expired" >&2
  exit 1
fi
if [ "$2" = login ]; then
  sleep 1
fi
"""


class GithubLoginTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.env["GH_BIN"] = self.install_command("gh", FAKE_GH)
        self.env["FAKE_GH_LOG"] = self.path("gh.log")
        self.env["COCKPIT_OPEN"] = "echo >> " + shlex.quote(self.path("opened"))
        self.env["COCKPIT_OPEN_DELAY"] = "0"

    def gh_calls(self):
        return self.read("gh.log").splitlines() if self.exists("gh.log") else []

    def test_given_the_user_approves_then_gh_signs_in_over_https_and_git_is_set_up(self):
        result = self.run_script("github-login.sh")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.gh_calls(),
            [
                "auth login --hostname github.com --git-protocol https --web --clipboard",
                "auth setup-git --hostname github.com",
                "auth status --hostname github.com",
            ],
        )
        self.assertIn("https://github.com/login/device", self.read("opened"))

    def test_given_the_sign_in_does_not_finish_then_git_is_not_set_up_and_the_message_says_to_retry(self):
        self.env["FAKE_GH_LOGIN_FAILS"] = "1"

        result = self.run_script("github-login.sh")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Retry", result.stderr)
        self.assertEqual(len(self.gh_calls()), 1)

    def test_given_the_sign_in_fails_at_once_then_the_page_is_not_opened(self):
        self.env["FAKE_GH_LOGIN_FAILS"] = "1"
        self.env["COCKPIT_OPEN_DELAY"] = "1"

        self.run_script("github-login.sh")
        time.sleep(1.5)

        self.assertFalse(self.exists("opened"))

    def test_given_overrides_without_the_test_switch_then_the_real_gh_is_used(self):
        del self.env["COCKPIT_TEST"]
        self.install_command("open", "exit 0\n", "path-bin")
        self.install_command("gh", 'printf \'%s\\n\' "$*" >>"$REAL_GH_LOG"\nif [ "$2" = login ]; then sleep 4; fi\n', "path-bin")
        self.env["PATH"] = self.path("path-bin") + os.pathsep + self.env["PATH"]
        self.env["REAL_GH_LOG"] = self.path("real-gh.log")

        result = self.run_script("github-login.sh")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(len(self.read("real-gh.log").splitlines()), 3)
