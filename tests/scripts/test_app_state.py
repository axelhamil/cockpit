import os
import sys
import unittest

from support import SCRIPTS_DIR, ScriptTestCase

sys.path.insert(0, SCRIPTS_DIR)

import app_state  # noqa: E402


def state(
    onboarding="complete",
    repository="owner/repo",
    deployed="main",
    test_environment="staging, branch develop, URL https://staging.example.com",
):
    return (
        "---\nprovider: railway\nonboarding: {}\nonboarding_step: check\n---\n\n"
        "## SaaS project\n"
        "- Project: shop (11111111-1111-1111-1111-111111111111)\n"
        "- Production environment: production\n"
        "- App service: web, repository {}, deployed branch {}\n"
        "- Postgres service: Postgres\n"
        "- Test environment: {}\n"
    ).format(onboarding, repository, deployed, test_environment)


class AppStateTest(ScriptTestCase):
    def write_cockpit(self):
        self.write("cockpit-home/cockpit.md", "---\nschema_version: 2\n---\n")

    def test_normalize_accepts_https_ssh_and_plain(self):
        for url in (
            "https://github.com/Owner/Repo.git",
            "git@github.com:Owner/Repo.git",
            "ssh://git@github.com/owner/repo",
            "https://github.com/owner/repo/",
            "owner/repo",
        ):
            with self.subTest(url=url):
                self.assertEqual(app_state.normalize_repository(url), "owner/repo")

        self.assertIsNone(app_state.normalize_repository("not a url"))

    def test_reads_every_saved_app(self):
        self.write_cockpit()
        self.write(
            "cockpit-home/projects/a/state.md",
            state(repository="Acme/Shop", deployed="main"),
        )
        self.write(
            "cockpit-home/projects/b/state.md",
            state(
                onboarding="in-progress",
                repository="https://github.com/acme/admin.git",
                deployed="production",
                test_environment="preview, branch staging, URL https://preview.example.com",
            ),
        )

        apps = sorted(app_state.read_apps(self.home), key=lambda app: app.slug)

        self.assertEqual(
            apps,
            [
                app_state.AppState("a", "complete", "acme/shop", "main", "develop"),
                app_state.AppState(
                    "b", "in-progress", "acme/admin", "production", "staging"
                ),
            ],
        )

    def test_reads_the_legacy_layout(self):
        self.write("cockpit-home/state.md", state())

        self.assertEqual(
            app_state.read_apps(self.home),
            [app_state.AppState("app", "complete", "owner/repo", "main", "develop")],
        )

    def test_test_environment_none_gives_no_test_branch(self):
        self.write_cockpit()
        self.write("cockpit-home/projects/a/state.md", state(test_environment="none"))

        self.assertEqual(
            app_state.read_apps(self.home),
            [app_state.AppState("a", "complete", "owner/repo", "main", None)],
        )

    def test_unreadable_state_is_skipped(self):
        self.write_cockpit()
        self.write("cockpit-home/projects/good/state.md", state())
        garbage = self.path("cockpit-home/projects/bad/state.md")
        os.makedirs(os.path.dirname(garbage))
        with open(garbage, "wb") as handle:
            handle.write(b"\xff\xfe\x00\x81garbage\x00\xc3")

        self.assertEqual(
            app_state.read_apps(self.home),
            [app_state.AppState("good", "complete", "owner/repo", "main", "develop")],
        )


if __name__ == "__main__":
    unittest.main()
