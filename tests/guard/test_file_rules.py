import os
import tempfile

from support import HOME, PLUGIN_ROOT, REPO_CLONE, STATE_HOME, GuardTable, context


class ProtectedFiles(GuardTable):
    def test_plugin_files_are_blocked(self):
        self.assert_paths_blocked([
            PLUGIN_ROOT + "/skills/railway-pilot/SKILL.md",
            PLUGIN_ROOT + "/scripts/guard.py",
            PLUGIN_ROOT + "/hooks/hooks.json",
            PLUGIN_ROOT + "/new-file.md",
            PLUGIN_ROOT,
            PLUGIN_ROOT + "/skills/../scripts/guard.sh",
            "/tmp/../" + PLUGIN_ROOT.lstrip("/") + "/scripts/guard.py",
            "~/.claude/plugins/cache/acme/railway-pilot/1.0.0/scripts/guard.py",
            PLUGIN_ROOT.upper() + "/scripts/guard.py",
        ])

    def test_installed_plugins_are_blocked(self):
        self.assert_paths_blocked([
            HOME + "/.claude/plugins/installed_plugins.json",
            HOME + "/.claude/plugins/cache/other/plugin/1.0.0/hooks/hooks.json",
            "~/.claude/plugins/known_marketplaces.json",
            HOME + "/.claude/settings/../plugins/config.json",
            HOME + "/.Claude/Plugins/config.json",
        ])

    def test_the_guard_configuration_is_blocked(self):
        self.assert_paths_blocked([
            STATE_HOME + "/guard.conf",
            "~/.railway-pilot/guard.conf",
            STATE_HOME + "/repo/../guard.conf",
            STATE_HOME + "/GUARD.CONF",
        ])

    def test_sensitive_files_of_the_repo_clone_are_blocked(self):
        self.assert_paths_blocked([
            REPO_CLONE + "/.github/workflows/ci.yml",
            REPO_CLONE + "/.github/workflows/nested/deploy.yaml",
            REPO_CLONE + "/.env",
            REPO_CLONE + "/.env.local",
            REPO_CLONE + "/.env.production",
            REPO_CLONE + "/.env.example",
            REPO_CLONE + "/railway.json",
            REPO_CLONE + "/railway.toml",
            REPO_CLONE + "/railway.ts",
            REPO_CLONE + "/.railway/config.json",
            REPO_CLONE + "/.railway/nested/file",
            REPO_CLONE + "/.git/hooks/pre-commit",
            REPO_CLONE + "/.git/config",
            REPO_CLONE + "/.GIT/hooks/pre-push",
            REPO_CLONE + "/vendor/lib/.git/config",
            "~/.railway-pilot/repo/.git/info/attributes",
            REPO_CLONE + "/apps/web/.env",
            REPO_CLONE + "/apps/api/railway.toml",
            REPO_CLONE + "/src/../.env",
            REPO_CLONE + "/.ENV",
            REPO_CLONE + "/Railway.json",
            REPO_CLONE + "/.GitHub/Workflows/ci.yml",
            "~/.railway-pilot/repo/.env",
        ])

    def test_a_relative_path_is_resolved_from_the_working_directory(self):
        inside_clone = context(working_directory=REPO_CLONE)

        self.assert_paths_blocked([".env", "./railway.json", ".github/workflows/ci.yml"], inside_clone)
        self.assert_paths_allowed(["src/footer.tsx", "README.md"], inside_clone)

    def test_a_symbolic_link_into_the_plugin_is_blocked(self):
        with tempfile.TemporaryDirectory() as sandbox:
            plugin_root = os.path.join(sandbox, "plugin")
            os.makedirs(os.path.join(plugin_root, "scripts"))
            link = os.path.join(sandbox, "shortcut")
            os.symlink(os.path.join(plugin_root, "scripts"), link)

            self.assert_paths_blocked([os.path.join(link, "guard.py")], context(plugin_root=plugin_root))


class OrdinaryFiles(GuardTable):
    def test_other_files_are_allowed(self):
        self.assert_paths_allowed([
            REPO_CLONE + "/src/components/Footer.tsx",
            REPO_CLONE + "/README.md",
            REPO_CLONE + "/.github/ISSUE_TEMPLATE/bug.md",
            REPO_CLONE + "/.github/dependabot.yml",
            REPO_CLONE + "/src/environment.ts",
            REPO_CLONE + "/src/railway.tsx",
            REPO_CLONE + "/.envrc",
            REPO_CLONE + "/.gitignore",
            REPO_CLONE + "/.gitattributes",
            REPO_CLONE + "/docs/workflows/notes.md",
            STATE_HOME + "/state.md",
            STATE_HOME + "/journal.md",
            STATE_HOME + "/proposals.md",
            STATE_HOME + "/guard.conf.md",
            "/tmp/notes.md",
            HOME + "/project/.env",
            HOME + "/project/railway.json",
            HOME + "/.claude/settings.json",
            HOME + "/.claude/plugins-notes.md",
        ])
