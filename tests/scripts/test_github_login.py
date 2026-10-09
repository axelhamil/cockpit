import os
import shlex

from support import ScriptTestCase

TOKEN = "github_pat_11SECRETSECRETSECRET"

FAKE_GH = """
printf '%s\\n' "$*" >>"$FAKE_GH_LOG"
if [ "$2" = login ]; then
  cat >"$FAKE_GH_STDIN"
  if [ -n "${FAKE_GH_LOGIN_FAILS:-}" ]; then
    echo "error validating token: HTTP 401: Bad credentials" >&2
    exit 1
  fi
fi
"""


class GithubLoginTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.env["GH_BIN"] = self.install_command("gh", FAKE_GH)
        self.env["FAKE_GH_LOG"] = self.path("gh.log")
        self.env["FAKE_GH_STDIN"] = self.path("gh.stdin")
        self.env["RP_PASTE"] = "cat " + shlex.quote(self.write("clipboard", TOKEN + "\n"))
        self.env["RP_CLEAR_CLIPBOARD"] = "cat > " + shlex.quote(self.path("clipboard"))

    def login(self):
        return self.run_script("github-login.sh")

    def gh_calls(self):
        return self.read("gh.log").splitlines() if self.exists("gh.log") else []

    def test_given_a_token_on_the_clipboard_then_gh_receives_it_on_stdin_and_the_clipboard_is_emptied(self):
        result = self.login()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("gh.stdin"), TOKEN)
        self.assertEqual(
            self.gh_calls(),
            ["auth login --with-token --hostname github.com", "auth setup-git --hostname github.com", "auth status --hostname github.com"],
        )
        self.assertEqual(self.read("clipboard"), "")
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        self.assertNotIn(TOKEN, self.read("gh.log"))

    def test_given_github_refuses_the_token_then_the_clipboard_is_still_emptied_and_the_message_is_readable(self):
        self.env["FAKE_GH_LOGIN_FAILS"] = "1"

        result = self.login()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.read("clipboard"), "")
        self.assertIn("token", result.stderr)
        self.assertIn("Bad credentials", result.stderr)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        self.assertEqual(self.gh_calls(), ["auth login --with-token --hostname github.com"])

    def test_given_something_else_on_the_clipboard_then_it_is_left_alone_and_gh_is_not_called(self):
        self.write("clipboard", "my shopping list")

        result = self.login()

        self.assertEqual(result.returncode, 1)
        self.assertIn("token", result.stderr)
        self.assertEqual(self.read("clipboard"), "my shopping list")
        self.assertNotIn("shopping", result.stdout + result.stderr)
        self.assertEqual(self.gh_calls(), [])

    def test_given_overrides_without_the_test_switch_then_the_real_commands_are_used(self):
        del self.env["RP_TEST"]
        self.install_command("pbpaste", "printf '%s' \"$REAL_TOKEN\"\n", "path-bin")
        self.install_command("pbcopy", 'cat >"$REAL_CLEARED"\n', "path-bin")
        self.install_command("gh", 'printf \'%s\\n\' "$*" >>"$REAL_GH_LOG"\ncat >/dev/null\n', "path-bin")
        self.env["PATH"] = self.path("path-bin") + os.pathsep + self.env["PATH"]
        self.env["REAL_TOKEN"] = "github_pat_22REALREALREAL"
        self.env["REAL_CLEARED"] = self.path("real-cleared")
        self.env["REAL_GH_LOG"] = self.path("real-gh.log")

        result = self.login()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(len(self.read("real-gh.log").splitlines()), 3)
        self.assertEqual(self.read("real-cleared"), "")
        self.assertEqual(self.read("clipboard"), TOKEN + "\n")
