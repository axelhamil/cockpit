import json
import os
import stat
import unittest

from support import SCRIPTS_DIR, ScriptTestCase

ARGUMENTS = ["--marketplace", "railway-pilot", "--repo", "acme/railway-pilot"]


def replaced(option, value):
    arguments = list(ARGUMENTS)
    arguments[arguments.index(option) + 1] = value
    return arguments


def shipped_permissions():
    with open(os.path.join(SCRIPTS_DIR, "permissions.json"), encoding="utf-8") as handle:
        return json.load(handle)["permissions"]


class ApplySettingsTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.env["CLAUDE_SETTINGS"] = self.path("claude/settings.json")

    def settings(self):
        return json.loads(self.read("claude/settings.json"))

    def apply(self, arguments=None):
        return self.run_script("apply-settings.sh", *(ARGUMENTS if arguments is None else arguments))

    def test_given_no_settings_file_then_it_is_created_with_the_rules_and_the_marketplace(self):
        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings()["permissions"], shipped_permissions())
        self.assertEqual(
            self.settings()["extraKnownMarketplaces"],
            {"railway-pilot": {"source": {"source": "github", "repo": "acme/railway-pilot"}, "autoUpdate": True}},
        )
        self.assertEqual(os.listdir(self.path("claude")), ["settings.json"])
        self.assertEqual(os.listdir(self.path("pilot-home")), [])

    def test_shipped_permissions_only_allow(self):
        permissions = shipped_permissions()

        self.assertEqual(sorted(permissions), ["additionalDirectories", "allow"])
        self.assertEqual(permissions["additionalDirectories"], ["~/.railway-pilot"])
        self.assertEqual(
            permissions["allow"],
            [
                "Bash(railway *)",
                "Bash(gh *)",
                "Bash(git *)",
                "Read(~/.railway-pilot/**)",
                "Edit(~/.railway-pilot/**)",
                "Bash(sh */scripts/database-access.sh *)",
                "Bash(sh */scripts/install-gh.sh)",
                "Bash(sh */scripts/github-login.sh)",
                "Bash(sh */scripts/session-check.sh)",
            ],
        )

    def test_given_existing_user_settings_then_nothing_is_lost_and_a_backup_is_kept(self):
        existing = {
            "model": "opus",
            "env": {"EDITOR": "nvim"},
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "true"}]}]},
            "permissions": {
                "allow": ["Bash(ls *)", "Bash(git *)"],
                "ask": ["Bash(git push *)"],
                "deny": ["Bash(curl *)"],
                "additionalDirectories": ["~/notes"],
                "defaultMode": "acceptEdits",
            },
            "extraKnownMarketplaces": {
                "other": {"source": {"source": "github", "repo": "someone/other"}},
                "railway-pilot": {"source": {"source": "github", "repo": "old/location"}, "note": "kept"},
            },
        }
        original_text = json.dumps(existing)
        self.write("claude/settings.json", original_text)

        result = self.apply()

        merged = self.settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(merged["model"], "opus")
        self.assertEqual(merged["env"], existing["env"])
        self.assertEqual(merged["hooks"], existing["hooks"])
        self.assertEqual(merged["permissions"]["defaultMode"], "acceptEdits")
        self.assertEqual(merged["permissions"]["ask"], ["Bash(git push *)"])
        self.assertEqual(merged["permissions"]["deny"], ["Bash(curl *)"])
        self.assertEqual(merged["permissions"]["allow"][:2], ["Bash(ls *)", "Bash(git *)"])
        self.assertEqual(merged["permissions"]["allow"].count("Bash(git *)"), 1)
        self.assertEqual(merged["permissions"]["additionalDirectories"], ["~/notes", "~/.railway-pilot"])
        for kind, rules in shipped_permissions().items():
            self.assertTrue(set(rules) <= set(merged["permissions"][kind]), kind)
        self.assertEqual(merged["extraKnownMarketplaces"]["other"], existing["extraKnownMarketplaces"]["other"])
        self.assertEqual(
            merged["extraKnownMarketplaces"]["railway-pilot"],
            {"source": {"source": "github", "repo": "acme/railway-pilot"}, "note": "kept", "autoUpdate": True},
        )
        self.assertEqual(self.read("claude/settings.json.before-railway-pilot"), original_text)

    def test_given_a_second_run_then_nothing_changes_and_the_backup_is_not_replaced(self):
        self.write("claude/settings.json", '{"permissions": {"allow": ["Bash(ls *)"]}}')
        self.apply()
        first_settings = self.read("claude/settings.json")

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("claude/settings.json"), first_settings)
        self.assertEqual(self.read("claude/settings.json.before-railway-pilot"), '{"permissions": {"allow": ["Bash(ls *)"]}}')
        self.assertEqual(sorted(os.listdir(self.path("claude"))), ["settings.json", "settings.json.before-railway-pilot"])

    def test_given_a_later_run_with_another_repository_then_the_first_backup_is_kept(self):
        self.write("claude/settings.json", '{"model": "opus"}')
        self.apply()

        result = self.apply(replaced("--repo", "acme/moved"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings()["extraKnownMarketplaces"]["railway-pilot"]["source"]["repo"], "acme/moved")
        self.assertEqual(self.read("claude/settings.json.before-railway-pilot"), '{"model": "opus"}')

    def test_given_a_second_run_after_creating_the_file_then_no_backup_of_our_own_file_appears(self):
        self.apply()

        self.apply()

        self.assertEqual(os.listdir(self.path("claude")), ["settings.json"])

    def test_given_settings_that_cannot_be_parsed_then_nothing_is_written(self):
        cases = (
            (b'{"permissions": ', "not valid JSON"),
            (b'{"model": "\xff\xfe"}', "UTF-8"),
            (b'["a list"]', "JSON object"),
            (b'{"permissions": {"allow": "Bash(ls *)"}}', "not a list"),
        )

        for content, expected in cases:
            with self.subTest(content=content):
                os.makedirs(self.path("claude"), exist_ok=True)
                with open(self.path("claude/settings.json"), "wb") as handle:
                    handle.write(content)

                result = self.apply()

                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                with open(self.path("claude/settings.json"), "rb") as handle:
                    self.assertEqual(handle.read(), content)
                self.assertEqual(os.listdir(self.path("claude")), ["settings.json"])

    @unittest.skipIf(os.geteuid() == 0, "root ignores folder permissions")
    def test_given_a_settings_folder_that_is_not_writable_then_nothing_is_written(self):
        self.write("claude/settings.json", '{"model": "opus"}')
        os.chmod(self.path("claude"), stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(os.chmod, self.path("claude"), stat.S_IRWXU)

        result = self.apply()

        self.assertEqual(result.returncode, 1)
        self.assertIn("writable", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.read("claude/settings.json"), '{"model": "opus"}')
        self.assertEqual(os.listdir(self.path("claude")), ["settings.json"])

    def test_given_a_symlinked_settings_file_then_the_link_is_kept(self):
        target = self.write("dotfiles/settings.json", '{"model": "opus"}')
        os.makedirs(self.path("claude"))
        os.symlink(target, self.path("claude/settings.json"))

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.islink(self.path("claude/settings.json")))
        self.assertEqual(json.loads(self.read("dotfiles/settings.json"))["model"], "opus")
        self.assertIn("permissions", json.loads(self.read("dotfiles/settings.json")))

    def test_given_a_settings_path_override_without_the_test_switch_then_the_real_location_is_used(self):
        del self.env["RP_TEST"]

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.exists("claude"))
        self.assertIn("permissions", json.loads(self.read(".claude/settings.json")))

    def test_given_invalid_arguments_then_exit_2_and_nothing_is_written(self):
        cases = (
            replaced("--marketplace", "bad name"),
            replaced("--marketplace", ""),
            replaced("--repo", "no-owner"),
            replaced("--repo", "a/b/c"),
            ARGUMENTS[2:],
            ARGUMENTS[:2],
            ARGUMENTS + ["--unknown", "x"],
            ARGUMENTS + ["--saas-project", "11111111-2222-3333-4444-555555555555"],
            ARGUMENTS + ["--deployed-branch", "main"],
            ARGUMENTS + ["--repo"],
        )

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.apply(arguments)

                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.strip())

        self.assertFalse(self.exists("claude"))
