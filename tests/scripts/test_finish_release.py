import os
import subprocess

from support import REPO_ROOT, ScriptTestCase

RELEASE_SCRIPTS_DIR = os.path.join(REPO_ROOT, ".github", "scripts")

FAKE_GH = """
printf '%s\\n' "$*" >>"$FAKE_GH_LOG"
case "$1 $2" in
  "release view") exit 1 ;;
  "release create")
    while [ $# -gt 1 ]; do
      if [ "$1" = --notes-file ]; then
        cp "$2" "$FAKE_GH_NOTES"
      fi
      shift
    done
    ;;
esac
"""

REJECT_NOTES = """#!/bin/sh
while read -r _ _ ref; do
  case $ref in
    refs/notes/*) exit 1 ;;
  esac
done
"""

CHANGELOG = """# [2.1.0](https://example.com/compare/v2.0.0...v2.1.0) (2026-10-09)


### Features

* update the saved setup by itself

## [2.0.1](https://example.com/compare/v2.0.0...v2.0.1) (2026-10-08)


### Bug Fixes

* an older fix
"""


class FinishReleaseTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.install_command("gh", FAKE_GH)
        self.env["PATH"] = self.path("bin") + os.pathsep + self.env["PATH"]
        self.env["FAKE_GH_LOG"] = self.path("gh.log")
        self.env["FAKE_GH_NOTES"] = self.path("published-notes.md")
        self.env["NOTE_PUSH_DELAY"] = "0"
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_SYSTEM"] = os.devnull
        self.env["GIT_AUTHOR_NAME"] = "release bot"
        self.env["GIT_AUTHOR_EMAIL"] = "bot@example.com"
        self.env["GIT_COMMITTER_NAME"] = "release bot"
        self.env["GIT_COMMITTER_EMAIL"] = "bot@example.com"
        self.remote = self.path("remote.git")
        self.checkout = self.path("checkout")
        self.git("init", "--quiet", "--bare", self.remote, cwd=self.workspace)
        self.git("init", "--quiet", "--initial-branch", "main", self.checkout, cwd=self.workspace)
        self.git("remote", "add", "origin", self.remote)
        self.git("commit", "--quiet", "--allow-empty", "--message", "feat: update the saved setup by itself")
        self.git("push", "--quiet", "origin", "HEAD:main")
        self.write("checkout/CHANGELOG.md", CHANGELOG)
        self.git("add", "CHANGELOG.md")
        self.git("commit", "--quiet", "--message", "chore(release): 2.1.0 [skip ci]")

    def git(self, *arguments, cwd=None):
        return subprocess.run(
            ["git", *arguments],
            env=self.env,
            cwd=cwd or self.checkout,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        ).stdout

    def tag_the_release_as_semantic_release_does(self):
        self.git("tag", "v2.1.0")
        self.git("notes", "--ref", "semantic-release-v2.1.0", "add", "--message", '{"channels":[null]}', "v2.1.0")

    def push_the_release(self):
        self.tag_the_release_as_semantic_release_does()
        self.git("push", "--quiet", "--tags", "origin", "HEAD:main")

    def finish_release(self):
        return self.run_script("finish_release.sh", cwd=self.checkout, directory=RELEASE_SCRIPTS_DIR)

    def remote_refs(self):
        return self.git("ls-remote", "origin")

    def test_given_a_pushed_tag_without_its_note_then_the_note_is_pushed_and_the_release_published(self):
        self.push_the_release()

        result = self.finish_release()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("refs/notes/semantic-release-v2.1.0", self.remote_refs())
        self.assertIn("release create v2.1.0", self.read("gh.log"))
        self.assertIn("update the saved setup by itself", self.read("published-notes.md"))
        self.assertNotIn("an older fix", self.read("published-notes.md"))

    def test_given_github_keeps_rejecting_the_note_then_the_release_is_still_published(self):
        self.push_the_release()
        hook = self.write("remote.git/hooks/pre-receive", REJECT_NOTES)
        os.chmod(hook, 0o755)

        result = self.finish_release()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("refs/notes/", self.remote_refs())
        self.assertIn("::warning::", result.stdout)
        self.assertIn("release create v2.1.0", self.read("gh.log"))

    def test_given_no_release_tag_on_head_then_it_fails_and_publishes_nothing(self):
        result = self.finish_release()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No release tag on HEAD", result.stderr)
        self.assertFalse(self.exists("gh.log"))

    def test_given_the_tag_was_pushed_but_its_commit_never_reached_main_then_it_fails_and_publishes_nothing(self):
        self.tag_the_release_as_semantic_release_does()
        self.git("push", "--quiet", "origin", "v2.1.0")

        result = self.finish_release()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("never reached main", result.stderr)
        self.assertFalse(self.exists("gh.log"))
