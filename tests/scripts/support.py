import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")
SHELL = shutil.which("sh")


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.workspace = workspace.name
        self.home = os.path.join(self.workspace, "cockpit-home")
        os.makedirs(self.home)
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": self.workspace,
            "COCKPIT_HOME": self.home,
            "COCKPIT_TEST": "1",
        }

    def run_script(self, name, *arguments, env=None, cwd=None, stdin=None):
        return subprocess.run(
            [SHELL, os.path.join(SCRIPTS_DIR, name), *arguments],
            env={**self.env, **(env or {})},
            cwd=cwd or self.workspace,
            input=stdin,
            stdin=None if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=120,
        )

    def path(self, *parts):
        return os.path.join(self.workspace, *parts)

    def write(self, relative_path, content):
        target = self.path(relative_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(content)
        return target

    def read(self, relative_path):
        with open(self.path(relative_path), encoding="utf-8") as handle:
            return handle.read()

    def exists(self, relative_path):
        return os.path.exists(self.path(relative_path))

    def build_state_v1(self, home=None):
        subprocess.run(
            [SHELL, os.path.join(FIXTURES_DIR, "state-v1", "fixture.sh")],
            env={**self.env, "COCKPIT_HOME": home or self.home},
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def snapshot(self, directory=None):
        root = directory or self.home
        entries = {}

        for current, directories, files in os.walk(root):
            for name in directories + files:
                full = os.path.join(current, name)
                mode = stat.S_IMODE(os.lstat(full).st_mode)

                if os.path.isdir(full):
                    entries[os.path.relpath(full, root)] = ("directory", mode, None)
                    continue

                with open(full, "rb") as handle:
                    entries[os.path.relpath(full, root)] = ("file", mode, handle.read())

        return entries

    def write_v2_state(self, *slugs, onboarding="complete"):
        self.write(
            "cockpit-home/cockpit.md",
            "---\nschema_version: 2\nlanguage: en\nplugin_version: 1.0.0\ndependencies: git, railway\n---\n\n"
            "## User\n- Name: Alex Morgan\n- Email: alex@example.com\n",
        )
        for slug in slugs:
            self.write(
                "cockpit-home/projects/{}/state.md".format(slug),
                "---\nprovider: railway\nonboarding: {}\nonboarding_step: check\n---\n\n"
                "## SaaS project\n- Project: {} (11111111-1111-1111-1111-111111111111)\n".format(onboarding, slug),
            )

    def install_command(self, name, body, directory="bin"):
        target = self.write(os.path.join(directory, name), "#!/bin/sh\n" + body)
        os.chmod(target, 0o755)
        return target

    def install_fake_railway(self, body):
        self.env["RAILWAY_BIN"] = self.install_command("railway", body)
        return self.env["RAILWAY_BIN"]

    def isolated_path(self, *system_tools):
        directory = self.path("isolated-bin")
        os.makedirs(directory, exist_ok=True)
        for tool in system_tools:
            link = os.path.join(directory, tool)
            if not os.path.exists(link):
                os.symlink(shutil.which(tool), link)
        return directory
