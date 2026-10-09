import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIRECTORY = os.path.join(REPO_ROOT, "scripts")
GUARD_ENTRY_POINT = os.path.join(SCRIPTS_DIRECTORY, "guard.sh")

sys.dont_write_bytecode = True
sys.path.insert(0, SCRIPTS_DIRECTORY)

from guardlib import bash, files
from guardlib.config import GuardContext

HOME = "/Users/client"
STATE_HOME = HOME + "/.railway-pilot"
REPO_CLONE = STATE_HOME + "/repo"
PLUGIN_ROOT = HOME + "/.claude/plugins/cache/acme/railway-pilot/1.0.0"


def context(state_home=STATE_HOME, plugin_root=PLUGIN_ROOT, working_directory=HOME):
    return GuardContext(
        plugin_root=plugin_root,
        state_home=state_home,
        home=HOME,
        working_directory=working_directory,
    )


def run_guard(stdin_text, state_home, working_directory=None, extra_environment=None):
    environment = dict(os.environ, RAILWAY_PILOT_HOME=state_home, **(extra_environment or {}))

    return subprocess.run(
        ["sh", GUARD_ENTRY_POINT],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=environment,
        cwd=working_directory,
        timeout=30,
    )


def hook_input(tool_name, **tool_input):
    return json.dumps({"tool_name": tool_name, "tool_input": tool_input}, separators=(",", ":"))


class GuardTable(unittest.TestCase):
    def assert_commands_allowed(self, commands, guard_context=None):
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNone(bash.blocking_reason(command, guard_context or context()))

    def assert_commands_blocked(self, commands, guard_context=None):
        for command in commands:
            with self.subTest(command=command):
                reason = bash.blocking_reason(command, guard_context or context())

                self.assertTrue(reason, "expected a blocking reason")

    def assert_reason_mentions(self, command, *fragments, guard_context=None):
        reason = bash.blocking_reason(command, guard_context or context())

        self.assertTrue(reason, "expected a blocking reason")

        for fragment in fragments:
            self.assertIn(fragment, reason)

    def assert_paths_allowed(self, paths, guard_context=None):
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(files.blocking_reason(path, guard_context or context()))

    def assert_paths_blocked(self, paths, guard_context=None):
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(files.blocking_reason(path, guard_context or context()))
