import json
import os
import stat
import unittest

from support import REPO_ROOT, SCRIPTS_DIR, ScriptTestCase

ARGUMENTS = ["--marketplace", "cockpit"]


def replaced(option, value):
    arguments = list(ARGUMENTS)
    arguments[arguments.index(option) + 1] = value
    return arguments


def shipped_permissions():
    with open(os.path.join(SCRIPTS_DIR, "permissions.json"), encoding="utf-8") as handle:
        return json.load(handle)["permissions"]


def shipped_repository():
    with open(os.path.join(REPO_ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
        return json.load(handle)["repository"]


class ApplySettingsTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.env["CLAUDE_SETTINGS"] = self.path("claude/settings.json")
        self.env["COCKPIT_PLUGIN_MANIFEST"] = self.plugin_manifest("https://github.com/acme/cockpit")

    def plugin_manifest(self, repository):
        return self.write("plugin/plugin.json", json.dumps({"name": "cockpit", "repository": repository}))

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
            {"cockpit": {"source": {"source": "github", "repo": "acme/cockpit"}, "autoUpdate": True}},
        )
        self.assertEqual(os.listdir(self.path("claude")), ["settings.json"])
        self.assertEqual(os.listdir(self.path("cockpit-home")), [])

    def test_shipped_permissions_only_allow(self):
        permissions = shipped_permissions()

        self.assertEqual(sorted(permissions), ["additionalDirectories", "allow"])
        self.assertEqual(permissions["additionalDirectories"], ["~/.cockpit"])
        self.assertEqual(
            permissions["allow"],
            [
                "Bash(railway *)",
                "Bash(gh *)",
                "Bash(git *)",
                "Read(~/.cockpit/**)",
                "Edit(~/.cockpit/**)",
                "Bash(sh */scripts/database-access.sh *)",
                "Bash(sh */scripts/install-gh.sh)",
                "Bash(sh */scripts/github-login.sh)",
                "Bash(sh */scripts/session-check.sh)",
                "Bash(sh */scripts/health-check.sh)",
                "Bash(sh */scripts/apply-settings.sh *)",
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
                "cockpit": {"source": {"source": "github", "repo": "old/location"}, "note": "kept"},
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
        self.assertEqual(merged["permissions"]["additionalDirectories"], ["~/notes", "~/.cockpit"])
        for kind, rules in shipped_permissions().items():
            self.assertTrue(set(rules) <= set(merged["permissions"][kind]), kind)
        self.assertEqual(merged["extraKnownMarketplaces"]["other"], existing["extraKnownMarketplaces"]["other"])
        self.assertEqual(
            merged["extraKnownMarketplaces"]["cockpit"],
            {"source": {"source": "github", "repo": "acme/cockpit"}, "note": "kept", "autoUpdate": True},
        )
        self.assertEqual(self.read("claude/settings.json.before-cockpit"), original_text)

    def test_given_a_second_run_then_nothing_changes_and_the_backup_is_not_replaced(self):
        self.write("claude/settings.json", '{"permissions": {"allow": ["Bash(ls *)"]}}')
        self.apply()
        first_settings = self.read("claude/settings.json")

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("claude/settings.json"), first_settings)
        self.assertEqual(self.read("claude/settings.json.before-cockpit"), '{"permissions": {"allow": ["Bash(ls *)"]}}')
        self.assertEqual(sorted(os.listdir(self.path("claude"))), ["settings.json", "settings.json.before-cockpit"])

    def test_given_a_later_run_after_the_plugin_moved_then_the_first_backup_is_kept(self):
        self.write("claude/settings.json", '{"model": "opus"}')
        self.apply()
        self.plugin_manifest("https://github.com/acme/moved")

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings()["extraKnownMarketplaces"]["cockpit"]["source"]["repo"], "acme/moved")
        self.assertEqual(self.read("claude/settings.json.before-cockpit"), '{"model": "opus"}')

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
        del self.env["COCKPIT_TEST"]

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.exists("claude"))
        written = json.loads(self.read(".claude/settings.json"))
        self.assertIn("permissions", written)
        self.assertEqual(
            "https://github.com/" + written["extraKnownMarketplaces"]["cockpit"]["source"]["repo"],
            shipped_repository(),
        )

    def test_given_invalid_arguments_then_exit_2_and_nothing_is_written(self):
        cases = (
            replaced("--marketplace", "bad name"),
            replaced("--marketplace", ""),
            [],
            ARGUMENTS + ["--unknown", "x"],
            ARGUMENTS + ["--saas-project", "11111111-2222-3333-4444-555555555555"],
            ARGUMENTS + ["--deployed-branch", "main"],
            ARGUMENTS + ["--repo", "attacker/cockpit"],
            ["--remove"] + ARGUMENTS + ["--repo", "acme/cockpit"],
        )

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.apply(arguments)

                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.strip())

        self.assertFalse(self.exists("claude"))

    def test_given_applied_settings_then_remove_takes_back_only_what_the_plugin_added(self):
        before = {
            "permissions": {"allow": ["Bash(ls *)", "Bash(git *)"]},
            "extraKnownMarketplaces": {"other": {"autoUpdate": False}},
            "model": "opus",
        }
        self.write("claude/settings.json", json.dumps(before))
        self.apply()

        result = self.apply(["--remove", "--marketplace", "cockpit"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings(), before)
        self.assertFalse(self.exists("claude/settings.json.before-cockpit"))

    def test_given_a_marketplace_of_the_same_name_before_the_plugin_then_remove_puts_it_back(self):
        before = {"extraKnownMarketplaces": {"cockpit": {"source": {"source": "directory", "path": "/src"}}}}
        self.write("claude/settings.json", json.dumps(before))
        self.apply()

        self.apply(["--remove", "--marketplace", "cockpit"])

        self.assertEqual(self.settings(), before)

    def test_given_settings_created_by_the_plugin_then_remove_leaves_no_rule_and_no_backup(self):
        self.apply()

        result = self.apply(["--remove", "--marketplace", "cockpit"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings(), {})
        self.assertFalse(self.exists("claude/settings.json.before-cockpit"))

    def test_given_no_settings_file_then_remove_creates_nothing(self):
        result = self.apply(["--remove", "--marketplace", "cockpit"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.exists("claude/settings.json"))

    def test_given_a_plugin_file_without_a_github_repository_then_nothing_is_written(self):
        cases = (
            "https://example.com/acme/cockpit",
            "https://github.com/acme",
            "https://github.com/acme/cockpit/tree/main",
            "https://github.com/acme/..",
            "https://github.com/../cockpit",
            "acme/cockpit",
            "",
        )

        for repository in cases:
            with self.subTest(repository=repository):
                self.plugin_manifest(repository)

                result = self.apply()

                self.assertEqual(result.returncode, 1)
                self.assertIn("Nothing was changed", result.stderr)

        self.assertFalse(self.exists("claude"))

    def test_given_the_shipped_plugin_file_then_its_repository_is_the_marketplace_source(self):
        del self.env["COCKPIT_PLUGIN_MANIFEST"]

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            "https://github.com/" + self.settings()["extraKnownMarketplaces"]["cockpit"]["source"]["repo"],
            shipped_repository(),
        )
