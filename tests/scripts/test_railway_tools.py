import os

from support import SAAS_PROJECT_ID, TOOLS_PROJECT_ID, ScriptTestCase

FAKE_RAILWAY = """
printf '%s|%s\\n' "$PWD" "$*" >>"$FAKE_RAILWAY_LOG"
printf '%s\\n' "${RAILWAY_TOKEN:-}${RAILWAY_API_TOKEN:-}${RAILWAY_PROJECT_ID:-}${RAILWAY_ENVIRONMENT_ID:-}${RAILWAY_SERVICE_ID:-}" >>"$FAKE_RAILWAY_ENV"
if [ "$1" = status ]; then
  cat >/dev/null
  if [ -z "${FAKE_LINKED_PROJECT:-}" ]; then
    exit 1
  fi
  printf '{"id": "%s", "name": "demo"}\\n' "$FAKE_LINKED_PROJECT"
fi
if [ "$1" = variable ]; then
  cat >"$FAKE_RAILWAY_STDIN"
fi
if [ "$1" = unlink ] && [ -n "${FAKE_UNLINK_FAILS:-}" ]; then
  exit 1
fi
exit "${FAKE_EXIT_CODE:-0}"
"""


class RailwayToolsTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.install_fake_railway(FAKE_RAILWAY)
        self.env["FAKE_RAILWAY_LOG"] = self.path("railway.log")
        self.env["FAKE_RAILWAY_ENV"] = self.path("railway.env")
        self.env["FAKE_RAILWAY_STDIN"] = self.path("railway.stdin")
        self.env["FAKE_LINKED_PROJECT"] = TOOLS_PROJECT_ID

    def calls(self):
        if not self.exists("railway.log"):
            return []
        return [line.split("|", 1)[1] for line in self.read("railway.log").splitlines()]

    def mutations(self):
        return [call for call in self.calls() if call != "status --json"]

    def working_directories(self):
        return {os.path.realpath(line.split("|", 1)[0]) for line in self.read("railway.log").splitlines()}

    def test_given_the_tools_project_is_linked_then_the_command_runs_in_the_tools_folder(self):
        self.write_guard_conf()

        result = self.run_script("railway-tools.sh", "deploy", "-t", "metabase", "-v", "KEY=some value")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["status --json", "deploy -t metabase -v KEY=some value"])
        self.assertEqual(self.working_directories(), {os.path.realpath(self.path("pilot-home/tools-project"))})

    def test_given_the_saas_project_is_linked_then_every_mutation_is_refused(self):
        self.write_guard_conf()
        self.env["FAKE_LINKED_PROJECT"] = SAAS_PROJECT_ID.upper()

        for arguments in (
            ["deploy", "-t", "metabase"],
            ["variable", "set", "A", "--stdin"],
            ["add", "-d", "postgres"],
            ["redeploy", "-y"],
            ["logs", "--lines", "50"],
            ["service", "restart", "-s", "api"],
        ):
            with self.subTest(arguments=arguments):
                result = self.run_script("railway-tools.sh", *arguments)

                self.assertEqual(result.returncode, 3)
                self.assertIn("SaaS project", result.stderr)

        self.assertEqual(self.mutations(), [])

    def test_given_no_guard_conf_then_mutations_are_refused_without_calling_railway(self):
        result = self.run_script("railway-tools.sh", "deploy", "-t", "metabase")

        self.assertEqual(result.returncode, 3)
        self.assertIn("guard.conf", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_given_no_linked_project_then_mutations_are_refused(self):
        self.write_guard_conf()
        self.env["FAKE_LINKED_PROJECT"] = ""

        result = self.run_script("railway-tools.sh", "domain", "-s", "metabase")

        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.calls(), ["status --json"])

    def test_given_a_command_off_the_list_then_it_is_refused_without_calling_railway(self):
        self.write_guard_conf()

        cases = (
            ["delete"],
            ["down"],
            ["ssh"],
            ["run", "env"],
            ["variable", "delete", "A"],
            ["variable", "list"],
            ["variables", "set", "A", "--stdin"],
            ["volume", "delete"],
            ["-p", "x", "deploy"],
            ["service"],
            ["service", "delete", "-s", "metabase", "-y"],
            ["service", "files", "delete", "-s", "metabase", "/data"],
            ["service", "source", "disconnect"],
            ["service", "scale"],
            ["service", "metabase"],
            ["service", "logs", "-s", "metabase"],
            ["domain", "delete", "tools.example.com", "-y"],
            ["domain", "-s", "metabase", "remove"],
            ["domain", "rm", "x"],
            ["domain", "update", "x"],
            ["domain", "edit", "x"],
            ["domain", "certificate"],
            ["variable", "set", "SECRET=hunter2", "-s", "metabase"],
            ["variable", "set", "SECRET=hunter2", "--stdin"],
            ["variable", "set", "--stdin", "SECRET"],
            ["variable", "set", "SECRET", "-s", "metabase"],
            ["variable", "set", "SECRET", "--stdin", "OTHER=value"],
            ["variable", "set", "SECRET", "--stdin", "--service=metabase"],
            ["logs", "-s", "metabase"],
            ["logs"],
            [],
        )

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.run_script("railway-tools.sh", *arguments)

                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.strip())

        self.assertEqual(self.calls(), [])

    def test_given_a_command_that_names_another_project_or_environment_in_a_hidden_form_then_it_is_refused(self):
        self.write_guard_conf()

        cases = (
            (["variable", "set", "A", "--stdin", "-p", SAAS_PROJECT_ID], 2),
            (["variable", "set", "A", "--stdin", "-s", SAAS_PROJECT_ID], 3),
            (["redeploy", "--project=" + SAAS_PROJECT_ID], 3),
            (["restart", "-p" + SAAS_PROJECT_ID.upper()], 3),
            (["redeploy", "-yp" + SAAS_PROJECT_ID], 3),
            (["redeploy", "-p", "some-project-name"], 2),
            (["redeploy", "-yp", "OtherProjectName"], 2),
            (["redeploy", "-ypOtherProjectName"], 2),
            (["restart", "-ye", "production"], 2),
            (["restart", "-eproduction"], 2),
            (["domain", "--project", "some-project-name"], 2),
            (["domain", "-p8080"], 2),
            (["link", "-pOtherProjectName"], 2),
        )

        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = self.run_script("railway-tools.sh", *arguments)

                self.assertEqual(result.returncode, expected)

        self.assertEqual(self.calls(), [])

    def test_given_the_planned_forms_then_they_reach_railway(self):
        self.write_guard_conf()

        cases = (
            ["domain", "-p", "3000", "-s", "metabase"],
            ["restart", "-s", "metabase", "-e", "production", "-y"],
            ["service", "list"],
            ["service", "status", "-s", "metabase"],
            ["service", "redeploy", "-s", "metabase"],
            ["service", "logs", "-s", "metabase", "--lines", "20"],
            ["logs", "-s", "metabase", "--since", "1h"],
            ["logs", "-n", "50"],
            ["logs", "--tail=20"],
            ["add", "-d", "postgres"],
        )

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.run_script("railway-tools.sh", *arguments)

                self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(self.mutations(), [" ".join(arguments) for arguments in cases])

    def test_given_variable_set_then_the_value_goes_on_stdin_and_never_in_the_arguments(self):
        self.write_guard_conf()

        result = self.run_script("railway-tools.sh", "variable", "set", "MB_DB_PASS", "--stdin", "-s", "metabase", "--skip-deploys", stdin="hunter2")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations(), ["variable set MB_DB_PASS --stdin -s metabase --skip-deploys"])
        self.assertEqual(self.read("railway.stdin"), "hunter2")
        self.assertNotIn("hunter2", self.read("railway.log"))

    def test_given_railway_variables_in_the_environment_then_they_never_reach_railway(self):
        self.write_guard_conf()
        hostile = {
            "RAILWAY_TOKEN": "token",
            "RAILWAY_API_TOKEN": "api-token",
            "RAILWAY_PROJECT_ID": SAAS_PROJECT_ID,
            "RAILWAY_ENVIRONMENT_ID": "environment",
            "RAILWAY_SERVICE_ID": "service",
        }

        for arguments in (["redeploy", "-y"], ["status"], ["link", "-p", "tools"], ["init", "-n", "tools"]):
            with self.subTest(arguments=arguments):
                result = self.run_script("railway-tools.sh", *arguments, env=hostile)

                self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(set(self.read("railway.env").splitlines()), {""})

    def test_given_a_railway_binary_override_without_the_test_switch_then_it_is_ignored(self):
        self.write_guard_conf()
        del self.env["RP_TEST"]
        self.install_command("railway", 'printf "real %s\\n" "$*" >>"$REAL_RAILWAY_LOG"\nprintf \'{"id": "%s"}\\n\' "$FAKE_LINKED_PROJECT"\n', "path-bin")
        self.env["PATH"] = self.path("path-bin") + os.pathsep + self.env["PATH"]
        self.env["REAL_RAILWAY_LOG"] = self.path("real.log")

        result = self.run_script("railway-tools.sh", "redeploy", "-y")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.read("real.log").splitlines(), ["real status --json", "real redeploy -y"])

    def test_init_and_status_run_before_the_safety_settings_exist(self):
        for arguments in (["init", "-n", "tools"], ["status", "--json"]):
            with self.subTest(arguments=arguments):
                result = self.run_script("railway-tools.sh", *arguments)

                self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(self.calls(), ["init -n tools", "status --json"])

    def test_given_link_to_the_tools_project_then_the_link_is_kept(self):
        self.write_guard_conf()

        result = self.run_script("railway-tools.sh", "link", "-p", "tools")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["link -p tools", "status --json"])

    def test_given_link_to_the_saas_project_by_name_then_it_is_unlinked_and_refused(self):
        self.write_guard_conf()
        self.env["FAKE_LINKED_PROJECT"] = SAAS_PROJECT_ID

        result = self.run_script("railway-tools.sh", "link", "-p", "my-saas")

        self.assertEqual(result.returncode, 3)
        self.assertIn("SaaS project", result.stderr)
        self.assertEqual(self.calls(), ["link -p my-saas", "status --json", "unlink --yes"])

    def test_given_link_to_the_saas_project_by_id_then_railway_is_never_called(self):
        self.write_guard_conf()

        result = self.run_script("railway-tools.sh", "link", "-p", SAAS_PROJECT_ID.upper())

        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.calls(), [])

    def test_given_link_without_guard_conf_then_it_is_refused(self):
        result = self.run_script("railway-tools.sh", "link", "-p", "tools")

        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.calls(), [])

    def test_given_link_fails_then_its_exit_code_is_returned(self):
        self.write_guard_conf()
        self.env["FAKE_EXIT_CODE"] = "7"

        result = self.run_script("railway-tools.sh", "link", "-p", "tools")

        self.assertEqual(result.returncode, 7)

    def test_given_the_railway_exit_code_then_it_is_passed_through(self):
        self.write_guard_conf()
        self.env["FAKE_EXIT_CODE"] = "5"

        result = self.run_script("railway-tools.sh", "restart", "-s", "metabase", "-y")

        self.assertEqual(result.returncode, 5)
