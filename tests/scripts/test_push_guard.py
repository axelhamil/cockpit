import json
import os
import subprocess
import time
import unittest

from support import ScriptTestCase

FAKE_PYTHON = 'touch "$PYTHON_CALLED"\nexit 1\n'


def state(
    onboarding="complete",
    repository="owner/app",
    deployed="main",
    test_branch="staging",
):
    return (
        "---\nprovider: railway\nonboarding: {}\nonboarding_step: check\n---\n\n"
        "## SaaS project\n"
        "- Project: app (11111111-1111-1111-1111-111111111111)\n"
        "- Production environment: production\n"
        "- App service: web, repository {}, deployed branch {}\n"
        "- Postgres service: Postgres\n"
        "- Test environment: staging, branch {}, URL https://staging.example.com\n"
    ).format(onboarding, repository, deployed, test_branch)


class PushGuardTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.write("cockpit-home/cockpit.md", "---\nschema_version: 2\n---\n")

    def save_app(self, slug="app", **values):
        self.write("cockpit-home/projects/{}/state.md".format(slug), state(**values))

    def git(self, directory, *arguments):
        subprocess.run(
            [
                "git",
                "-C",
                directory,
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                *arguments,
            ],
            env=self.env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def make_repo(self, origin="https://github.com/owner/app.git", branch="main"):
        repo = self.path("repo")
        os.makedirs(repo)
        self.git(repo, "init", "-q")
        self.git(repo, "checkout", "-q", "-b", "main")
        self.git(repo, "commit", "-q", "--allow-empty", "-m", "init")
        self.git(repo, "remote", "add", "origin", origin)

        if branch != "main":
            self.git(repo, "checkout", "-q", "-b", branch)

        return repo

    def guard(self, command, cwd):
        payload = json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": command},
                "cwd": cwd,
            }
        )
        return self.run_script("push-guard.sh", stdin=payload)

    def assert_denied(self, command, cwd):
        result = self.guard(command, cwd)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(result.stdout, "", command)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        return output["permissionDecisionReason"]

    def assert_allowed(self, command, cwd):
        result = self.guard(command, cwd)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "", command)

    def test_push_of_the_current_deployed_branch_is_redirected(self):
        self.save_app()
        repo = self.make_repo()

        reason = self.assert_denied("git push", repo)

        self.assertIn("cockpit/", reason)
        self.assertIn("COCKPIT_DIRECT_PUSH=1", reason)
        self.assert_denied("git push 2>&1", repo)
        self.assert_denied("git push >/dev/null", repo)

    def test_push_to_the_test_branch_by_refspec_is_redirected(self):
        self.save_app()
        repo = self.make_repo(branch="feature")

        self.assert_denied("git push origin HEAD:staging", repo)
        self.assert_denied("git push origin +feature:refs/heads/staging", repo)

    def test_push_with_git_dash_c_and_cd_is_seen(self):
        self.save_app()
        self.make_repo(branch="feature")

        self.assert_denied("cd repo && git push origin main", self.workspace)
        self.assert_denied("git -C repo push origin main", self.workspace)
        self.assert_denied(
            "git status\ngit -C repo push origin main 2>&1 | tail -1", self.workspace
        )

    def test_push_of_all_branches_and_deletion_are_redirected(self):
        self.save_app()
        repo = self.make_repo(branch="feature")

        self.assert_denied("git push --all origin", repo)
        self.assert_denied("git push origin --delete main", repo)
        self.assert_denied("git push origin :main", repo)

    def test_cockpit_branch_is_allowed(self):
        self.save_app()
        repo = self.make_repo(branch="cockpit/fix-label")

        self.assert_allowed("git push -u origin cockpit/fix-label", repo)
        self.assert_allowed("git push", repo)

    def test_push_of_a_branch_created_in_the_same_command_is_allowed(self):
        self.save_app()
        repo = self.make_repo()

        self.assert_allowed(
            "git checkout -b cockpit/x && git push -u origin HEAD", repo
        )
        self.assert_allowed("git switch -c cockpit/x && git push -u origin HEAD", repo)
        self.assert_allowed("git checkout -b cockpit/x && git push -u", repo)
        self.assert_allowed(
            "git -C . branch -m cockpit/x && git push origin HEAD", repo
        )

    def test_switching_back_to_the_deployed_branch_is_still_redirected(self):
        self.save_app()
        repo = self.make_repo(branch="feature")

        self.assert_denied("git checkout main && git push", repo)
        self.assert_denied("git switch staging && git push origin HEAD", repo)

    def test_heredoc_body_is_not_a_command(self):
        self.save_app()
        repo = self.make_repo()

        self.assert_allowed("cat > deploy.sh <<'EOF'\ngit push origin main\nEOF", repo)
        self.assert_allowed(
            "cat <<-EOF > deploy.sh\n\tgit push origin main\n\tEOF\necho done", repo
        )
        self.assert_denied(
            "cat > notes.txt <<EOF\nhello\nEOF\ngit push origin main", repo
        )

    def test_dry_run_is_allowed(self):
        self.save_app()
        repo = self.make_repo()

        self.assert_allowed("git push origin main --dry-run", repo)
        self.assert_allowed("git push -n origin main", repo)

    def test_marker_lets_the_push_through(self):
        self.save_app()
        repo = self.make_repo()

        self.assert_allowed("COCKPIT_DIRECT_PUSH=1 git push origin main", repo)

    def test_other_repository_is_allowed(self):
        self.save_app()
        repo = self.make_repo(origin="git@github.com:owner/fork.git")

        self.assert_allowed("git push origin main", repo)

    def test_onboarding_in_progress_is_allowed(self):
        self.save_app(onboarding="in-progress")
        repo = self.make_repo()

        self.assert_allowed("git push origin main", repo)

    def test_second_saved_app_is_guarded_too(self):
        self.save_app("admin", repository="owner/admin", deployed="production")
        self.save_app("shop", repository="owner/app", deployed="release")
        repo = self.make_repo(branch="feature")

        self.assert_allowed("git push origin main", repo)
        self.assert_denied("git push origin release", repo)

    def test_not_a_push_is_allowed(self):
        self.save_app()
        repo = self.make_repo()

        self.assert_allowed("git status", repo)
        self.assert_allowed('echo "git push origin main"', repo)

    def test_tag_push_is_allowed(self):
        self.save_app()
        repo = self.make_repo()
        self.git(repo, "tag", "v1.0.0")

        self.assert_allowed("git push origin v1.0.0", repo)
        self.assert_allowed("git push origin refs/tags/v1.0.0", repo)
        self.assert_allowed("git push --tags origin", repo)

    def test_slow_git_is_allowed_once_the_time_budget_is_spent(self):
        self.save_app()
        repo = self.make_repo()
        fake_git = self.install_command("git", "exec sleep 5\n")
        self.env["PATH"] = os.path.dirname(fake_git) + os.pathsep + self.env["PATH"]
        self.env["COCKPIT_GIT_BUDGET"] = "0.5"
        started = time.monotonic()

        self.assert_allowed("git push origin main", repo)
        self.assertLess(time.monotonic() - started, 3)

    def install_python_trap(self):
        self.install_command("python3", FAKE_PYTHON)
        self.env["PYTHON_CALLED"] = self.path("python-called")
        self.env["PATH"] = self.path("bin") + os.pathsep + self.env["PATH"]

    def test_command_without_push_never_starts_python(self):
        self.save_app()
        repo = self.make_repo()
        self.install_python_trap()

        result = self.guard("git status", repo)

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse(self.exists("python-called"))

    def test_mac_without_command_line_tools_never_starts_python(self):
        self.save_app()
        repo = self.make_repo()
        self.install_python_trap()
        self.install_command("uname", "echo Darwin\n")
        self.install_command("xcode-select", "exit 2\n")

        result = self.guard("git push origin main", repo)

        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertFalse(self.exists("python-called"))

    def test_unreadable_input_exits_zero(self):
        self.save_app()

        result = self.run_script("push-guard.sh", stdin="\x00not json{")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
