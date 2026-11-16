import os
import subprocess

from support import ScriptTestCase

SLUG = "acme-studio"
REPO = "cockpit-home/projects/{}/repo".format(SLUG)
GH_USER = '{"id": 42, "login": "lea"}'


class CommitIdentityTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.write_v2_state(SLUG)

    def clone_with_email(self, email):
        repo = self.path(REPO)
        os.makedirs(repo)
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "config", "user.email", email], check=True)

    def email(self):
        return subprocess.run(
            ["git", "-C", self.path(REPO), "config", "user.email"],
            env=self.env,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True,
        ).stdout.strip()

    def install_fake_gh(self, body):
        self.env["GH_BIN"] = self.install_command("gh", body)

    def set_identity(self):
        return self.run_script("commit-identity.sh", "--project", SLUG)

    def test_sets_the_noreply_address(self):
        self.clone_with_email("lea@example.com")
        self.install_fake_gh("echo '" + GH_USER + "'\n")

        result = self.set_identity()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.email(), "42+lea@users.noreply.github.com")

    def test_leaves_a_noreply_address_alone(self):
        self.clone_with_email("7+someone@users.noreply.github.com")
        self.install_fake_gh(
            'touch "' + self.path("gh-called") + "\"\necho '" + GH_USER + "'\n"
        )

        result = self.set_identity()

        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.exists("gh-called"))
        self.assertEqual(self.email(), "7+someone@users.noreply.github.com")

    def test_no_clone_does_nothing(self):
        self.install_fake_gh("echo '" + GH_USER + "'\n")
        before = self.snapshot()

        result = self.set_identity()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.snapshot(), before)

    def test_gh_failure_changes_nothing(self):
        self.clone_with_email("lea@example.com")
        self.install_fake_gh("echo 'not signed in' >&2\nexit 1\n")

        result = self.set_identity()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.email(), "lea@example.com")

    def test_an_unexpected_answer_changes_nothing(self):
        self.clone_with_email("lea@example.com")

        for answer in (
            '{"id": "42", "login": "lea"}',
            '{"id": 42, "login": "lea@evil"}',
            "[]",
            "not json",
        ):
            with self.subTest(answer=answer):
                self.install_fake_gh("echo '" + answer + "'\n")

                result = self.set_identity()

                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout + result.stderr, "")
                self.assertEqual(self.email(), "lea@example.com")
