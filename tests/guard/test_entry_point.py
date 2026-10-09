import json
import os
import tempfile
import unittest

from support import REPO_ROOT, hook_input, run_guard

ALLOW = 0
BLOCK = 2
REASON_PREFIX = "railway-pilot guard: "
MISSING_TOOLS_REASON = (
    "railway-pilot guard: Apple Command Line Tools are missing. Run xcode-select --install, "
    "wait for the installation to finish, then retry."
)
WITHOUT_COMMAND_LINE_TOOLS = {"RAILWAY_PILOT_GUARD_FORCE_NO_PYTHON": "1"}


class EntryPoint(unittest.TestCase):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(sandbox.cleanup)
        self.state_home = sandbox.name

    def guard(self, stdin_text, working_directory=None):
        return run_guard(stdin_text, self.state_home, working_directory)

    def assert_allowed(self, stdin_text):
        result = self.guard(stdin_text)

        self.assertEqual(result.returncode, ALLOW, result.stderr)
        self.assertEqual(result.stderr, "")

    def assert_blocked(self, stdin_text, *fragments):
        result = self.guard(stdin_text)

        self.assertEqual(result.returncode, BLOCK, result.stderr)
        self.assertTrue(result.stderr.startswith(REASON_PREFIX), result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
        self.assertTrue(result.stderr.isascii(), result.stderr)

        for fragment in fragments:
            self.assertIn(fragment, result.stderr)

    def test_an_allowed_command_exits_zero_without_output(self):
        self.assert_allowed(hook_input("Bash", command="railway status --json"))
        self.assert_allowed(hook_input("Bash", command="ls -la"))

    def test_a_forbidden_command_exits_two_with_a_one_line_reason(self):
        self.assert_blocked(hook_input("Bash", command="railway -e prod delete"), "railway delete")
        self.assert_blocked(hook_input("Bash", command="bash -c \"railway down\""), "railway")
        self.assert_blocked(hook_input("Bash", command="gh api -X DELETE repos/acme/app"), "gh api")

    def test_a_multi_line_command_still_gets_a_one_line_reason(self):
        self.assert_blocked(hook_input("Bash", command="railway \"de\nlete\"\nls"))

    def test_input_the_guard_cannot_read_is_blocked(self):
        for stdin_text in (
            "",
            "   \n",
            "not json",
            "{\"tool_name\": \"Bash\"",
            "[]",
            "null",
            "\"Bash\"",
            json.dumps({}),
            json.dumps({"tool_input": {"command": "ls"}}),
            json.dumps({"tool_name": 7, "tool_input": {"command": "ls"}}),
            json.dumps({"tool_name": "Bash"}),
            json.dumps({"tool_name": "Bash", "tool_input": None}),
            json.dumps({"tool_name": "Bash", "tool_input": {}}),
            json.dumps({"tool_name": "Bash", "tool_input": {"command": None}}),
            json.dumps({"tool_name": "Bash", "tool_input": {"command": ["ls"]}}),
            json.dumps({"tool_name": "Bash", "tool_input": {"command": ""}}),
            json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo \"unbalanced"}}),
            json.dumps({"tool_name": "Write", "tool_input": {}}),
            json.dumps({"tool_name": "Edit", "tool_input": {"file_path": ""}}),
            json.dumps({"tool_name": "Edit", "tool_input": {"file_path": 3}}),
        ):
            with self.subTest(stdin=stdin_text):
                self.assert_blocked(stdin_text)

    def test_a_tool_the_guard_does_not_cover_is_allowed(self):
        self.assert_allowed(hook_input("Read", file_path=os.path.join(REPO_ROOT, "scripts", "guard.py")))
        self.assert_allowed(hook_input("WebFetch", url="https://railway.com"))
        self.assert_allowed(json.dumps({"tool_name": "Grep"}))

    def test_the_plugin_root_is_the_parent_of_the_scripts_directory(self):
        plugin_file = os.path.join(REPO_ROOT, "skills", "railway-pilot", "SKILL.md")
        plugin_script = os.path.join(REPO_ROOT, "scripts", "railway-tools.sh")

        self.assert_blocked(hook_input("Write", file_path=plugin_file, content="x"), "plugin")
        self.assert_blocked(hook_input("Edit", file_path=plugin_file, old_string="a", new_string="b"))
        self.assert_blocked(hook_input("NotebookEdit", notebook_path=os.path.join(REPO_ROOT, "x.ipynb")))
        self.assert_blocked(hook_input("Bash", command="rm -rf " + REPO_ROOT))
        self.assert_allowed(hook_input("Bash", command="sh " + plugin_script + " deploy -t metabase"))
        self.assert_allowed(hook_input("Bash", command="sh \"$CLAUDE_PLUGIN_ROOT/scripts/railway-tools.sh\" link"))
        self.assert_allowed(hook_input("Write", file_path="/tmp/railway-pilot-notes.md", content="x"))

    def test_the_state_directory_comes_from_the_environment(self):
        guard_configuration = os.path.join(self.state_home, "guard.conf")
        repo_secret = os.path.join(self.state_home, "repo", ".env")
        repo_source = os.path.join(self.state_home, "repo", "src", "footer.tsx")

        self.assert_blocked(hook_input("Write", file_path=guard_configuration, content="x"), "guard.conf")
        self.assert_blocked(hook_input("Edit", file_path=repo_secret, old_string="a", new_string="b"))
        self.assert_allowed(hook_input("Edit", file_path=repo_source, old_string="a", new_string="b"))

    def test_a_relative_file_path_is_resolved_from_the_hook_working_directory(self):
        payload = {
            "tool_name": "Write",
            "cwd": os.path.join(self.state_home, "repo"),
            "tool_input": {"file_path": ".env", "content": "x"},
        }

        self.assert_blocked(json.dumps(payload))

    def test_pushes_stay_closed_before_onboarding_writes_the_configuration(self):
        self.assert_blocked(hook_input("Bash", command="git push origin main"), "pushing to main is blocked")
        self.assert_allowed(hook_input("Bash", command="git push -u origin pilot/fix-footer"))

    def test_the_configured_deployed_branch_is_protected(self):
        with open(os.path.join(self.state_home, "guard.conf"), "w", encoding="utf-8") as configuration:
            configuration.write("SAAS_PROJECT_ID=1234\nDEPLOYED_BRANCH=pilot/live\nTEST_BRANCH=\n")

        self.assert_blocked(hook_input("Bash", command="git push origin pilot/live"), "pilot/live")
        self.assert_allowed(hook_input("Bash", command="git push origin pilot/fix-footer"))

    def test_the_liveness_probes_of_onboarding_are_blocked(self):
        self.assert_blocked(hook_input("Bash", command="railway down --help"))
        self.assert_blocked(hook_input("Bash", command="git push --dry-run origin main"))

    def guard_without_command_line_tools(self, stdin_text):
        return run_guard(stdin_text, self.state_home, extra_environment=WITHOUT_COMMAND_LINE_TOOLS)

    def test_without_command_line_tools_only_the_repair_commands_pass(self):
        for command in ("xcode-select --install", "xcode-select -p", "git --version"):
            with self.subTest(command=command):
                result = self.guard_without_command_line_tools(hook_input("Bash", command=command))

                self.assertEqual(result.returncode, ALLOW, result.stderr)

        described = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git --version", "description": "Check git"}},
            separators=(",", ":"),
        )

        self.assertEqual(self.guard_without_command_line_tools(described).returncode, ALLOW)

    def test_without_command_line_tools_everything_else_is_blocked(self):
        smuggled = {"command": "rm -rf /tmp/x", "extra": {"tool_input": {"command": "git --version"}}}

        for stdin_text in (
            hook_input("Bash", command="railway status"),
            hook_input("Bash", command="ls"),
            hook_input("Bash", command="xcode-select --install; rm -rf /tmp/x"),
            hook_input("Bash", command="xcode-select --install && railway down"),
            hook_input("Bash", command=" git --version"),
            hook_input("Bash", command="echo '\"tool_input\":{\"command\":\"git --version\"}'"),
            hook_input("Bash", command="git --version\nrailway down"),
            hook_input("Write", file_path="/tmp/x", content="git --version"),
            hook_input("Write", command="git --version"),
            hook_input("Read", command="git --version"),
            json.dumps({"tool_name": "Bash", "tool_input": smuggled}, separators=(",", ":")),
            json.dumps({"tool_name": "Bash", "tool_input": {"command": "git --version"}}, indent=2),
            "",
            "not json",
        ):
            with self.subTest(stdin=stdin_text):
                result = self.guard_without_command_line_tools(stdin_text)

                self.assertEqual(result.returncode, BLOCK, result.stderr)
                self.assertEqual(result.stderr.strip(), MISSING_TOOLS_REASON)

    def test_the_guard_works_from_any_working_directory(self):
        result = self.guard(hook_input("Bash", command="railway down"), working_directory=self.state_home)

        self.assertEqual(result.returncode, BLOCK, result.stderr)
