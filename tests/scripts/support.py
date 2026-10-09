import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
SHELL = shutil.which("sh")

SAAS_PROJECT_ID = "11111111-2222-3333-4444-555555555555"
TOOLS_PROJECT_ID = "99999999-8888-7777-6666-555555555555"

FAKE_PSQL = """
import hashlib
import os
import re
import sys

sql = sys.stdin.read()
with open(os.environ["FAKE_SQL"], "a") as handle:
    handle.write(sql)
if os.environ.get("FAKE_PSQL_OUTPUT"):
    print(os.environ["FAKE_PSQL_OUTPUT"])
nonce = re.search(r"md5\\('([0-9a-f]+)'\\)", sql).group(1)
print(" rp-" + hashlib.md5(nonce.encode()).hexdigest())
"""


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.workspace = workspace.name
        self.home = os.path.join(self.workspace, "pilot-home")
        os.makedirs(self.home)
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": self.workspace,
            "RAILWAY_PILOT_HOME": self.home,
            "RP_TEST": "1",
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

    def write_guard_conf(self, saas_project_id=SAAS_PROJECT_ID):
        self.write(
            "pilot-home/guard.conf",
            "SAAS_PROJECT_ID={}\nDEPLOYED_BRANCH=main\nTEST_BRANCH=\n".format(saas_project_id),
        )

    def install_command(self, name, body, directory="bin"):
        target = self.write(os.path.join(directory, name), "#!/bin/sh\n" + body)
        os.chmod(target, 0o755)
        return target

    def install_fake_railway(self, body):
        self.env["RAILWAY_BIN"] = self.install_command("railway", body)
        return self.env["RAILWAY_BIN"]

    def fake_psql_command(self):
        script = self.write("fake_psql.py", FAKE_PSQL)
        self.env["FAKE_SQL"] = self.path("received.sql")
        return "python3 " + shlex.quote(script)

    def isolated_path(self, *system_tools):
        directory = self.path("isolated-bin")
        os.makedirs(directory, exist_ok=True)
        for tool in system_tools:
            link = os.path.join(directory, tool)
            if not os.path.exists(link):
                os.symlink(shutil.which(tool), link)
        return directory
