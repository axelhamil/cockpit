import json
import os
import stat
import unittest

from support import SAAS_PROJECT_ID, SCRIPTS_DIR, ScriptTestCase

OTHER_PROJECT_ID = "00000000-0000-0000-0000-000000000000"

ARGUMENTS = [
    "--saas-project",
    SAAS_PROJECT_ID,
    "--deployed-branch",
    "main",
    "--test-branch",
    "staging",
    "--marketplace",
    "railway-pilot",
    "--repo",
    "acme/railway-pilot",
]


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

    def test_given_no_settings_file_then_it_is_created_with_rules_marketplace_and_guard_conf(self):
        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings()["permissions"], shipped_permissions())
        self.assertEqual(
            self.settings()["extraKnownMarketplaces"],
            {"railway-pilot": {"source": {"source": "github", "repo": "acme/railway-pilot"}, "autoUpdate": True}},
        )
        self.assertEqual(
            self.read("pilot-home/guard.conf"),
            "SAAS_PROJECT_ID={}\nDEPLOYED_BRANCH=main\nTEST_BRANCH=staging\n".format(SAAS_PROJECT_ID),
        )
        self.assertFalse(self.exists("claude/settings.json.before-railway-pilot"))

    def test_shipped_permissions_open_the_state_folder_and_close_the_secret_stores(self):
        permissions = shipped_permissions()

        self.assertEqual(permissions["additionalDirectories"], ["~/.railway-pilot"])
        for rule in ("Read(~/.railway-pilot/**)", "Edit(~/.railway-pilot/**)", "Bash(sh */scripts/railway-tools.sh status *)"):
            self.assertIn(rule, permissions["allow"])
        for rule in (
            "Read(~/.railway/config.json)",
            "Read(~/.config/gh/**)",
            "Read(~/.railway-pilot/secrets/**)",
            "Bash(gh auth token *)",
            "Bash(git log * --output*)",
            "Bash(railway usage limit set *)",
        ):
            self.assertIn(rule, permissions["deny"])
        for kind in ("allow", "ask", "deny"):
            self.assertEqual(len(permissions[kind]), len(set(permissions[kind])), kind)
            self.assertEqual([rule for rule in permissions[kind] if rule.startswith("Bash(") and not rule.endswith("*)")], [], kind)
        self.assertEqual(set(permissions["allow"]) & set(permissions["deny"]), set())

    def test_given_no_test_branch_then_guard_conf_keeps_it_empty(self):
        result = self.apply(ARGUMENTS[:4] + ARGUMENTS[6:])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TEST_BRANCH=\n", self.read("pilot-home/guard.conf"))

    def test_given_existing_user_settings_then_nothing_is_lost_and_a_backup_is_kept(self):
        existing = {
            "model": "opus",
            "env": {"EDITOR": "nvim"},
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "true"}]}]},
            "permissions": {
                "allow": ["Bash(ls *)", "Bash(railway status *)"],
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
        self.assertEqual(merged["permissions"]["allow"][:2], ["Bash(ls *)", "Bash(railway status *)"])
        self.assertEqual(merged["permissions"]["allow"].count("Bash(railway status *)"), 1)
        self.assertIn("Bash(curl *)", merged["permissions"]["deny"])
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
        first_guard_conf = self.read("pilot-home/guard.conf")

        result = self.apply()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("claude/settings.json"), first_settings)
        self.assertEqual(self.read("pilot-home/guard.conf"), first_guard_conf)
        self.assertEqual(self.read("claude/settings.json.before-railway-pilot"), '{"permissions": {"allow": ["Bash(ls *)"]}}')
        self.assertEqual(sorted(os.listdir(self.path("claude"))), ["settings.json", "settings.json.before-railway-pilot"])
        self.assertEqual(os.listdir(self.path("pilot-home")), ["guard.conf"])

    def test_given_a_second_run_after_creating_the_file_then_no_backup_of_our_own_file_appears(self):
        self.apply()

        self.apply()

        self.assertEqual(os.listdir(self.path("claude")), ["settings.json"])

    def test_given_new_branches_for_the_same_project_then_guard_conf_is_updated(self):
        self.apply()

        result = self.apply(
            ["--saas-project", SAAS_PROJECT_ID.upper(), "--deployed-branch", "release/live", "--marketplace", "railway-pilot", "--repo", "acme/railway-pilot"]
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.read("pilot-home/guard.conf"),
            "SAAS_PROJECT_ID={}\nDEPLOYED_BRANCH=release/live\nTEST_BRANCH=\n".format(SAAS_PROJECT_ID),
        )

    def test_given_another_saas_project_than_the_recorded_one_then_it_is_refused_and_nothing_changes(self):
        self.apply()
        guard_conf = self.read("pilot-home/guard.conf")
        settings = self.read("claude/settings.json")

        result = self.apply(replaced("--saas-project", OTHER_PROJECT_ID))

        self.assertEqual(result.returncode, 1)
        self.assertIn("maintainer", result.stderr)
        self.assertIn("guard.conf", result.stderr)
        self.assertEqual(self.read("pilot-home/guard.conf"), guard_conf)
        self.assertEqual(self.read("claude/settings.json"), settings)

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
                self.assertEqual(os.listdir(self.path("pilot-home")), [])

    @unittest.skipIf(os.geteuid() == 0, "root ignores folder permissions")
    def test_given_a_settings_folder_that_is_not_writable_then_nothing_is_written_at_all(self):
        self.write("claude/settings.json", '{"model": "opus"}')
        os.chmod(self.path("claude"), stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(os.chmod, self.path("claude"), stat.S_IRWXU)

        result = self.apply()

        self.assertEqual(result.returncode, 1)
        self.assertIn("writable", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.read("claude/settings.json"), '{"model": "opus"}')
        self.assertEqual(os.listdir(self.path("pilot-home")), [])

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
            replaced("--saas-project", "not-a-project-id"),
            replaced("--saas-project", "-" * 36),
            replaced("--saas-project", "1111111-12222-3333-4444-555555555555"),
            replaced("--saas-project", SAAS_PROJECT_ID[:-1] + "g"),
            replaced("--saas-project", SAAS_PROJECT_ID + "0"),
            replaced("--deployed-branch", "main\nSAAS_PROJECT_ID=other"),
            replaced("--deployed-branch", ""),
            replaced("--test-branch", "a b"),
            replaced("--marketplace", "bad name"),
            replaced("--repo", "no-owner"),
            ARGUMENTS[2:],
            ARGUMENTS + ["--unknown", "x"],
        )

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.apply(arguments)

                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.strip())

        self.assertFalse(self.exists("pilot-home/guard.conf"))
        self.assertFalse(self.exists("claude"))
