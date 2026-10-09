import os
import tempfile

from support import GuardTable, context


class ProtectedBranches(GuardTable):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(sandbox.cleanup)
        self.state_home = sandbox.name

    def write_configuration(self, content):
        with open(os.path.join(self.state_home, "guard.conf"), "w", encoding="utf-8") as configuration:
            configuration.write(content)

    def test_without_configuration_the_default_branches_are_protected(self):
        guard_context = context(state_home=self.state_home)

        for branch in ("main", "master", "production", "prod"):
            with self.subTest(branch=branch):
                self.assert_reason_mentions(
                    "git push origin " + branch,
                    "pushing to " + branch + " is blocked",
                    guard_context=guard_context,
                )

        self.assert_commands_allowed(["git push -u origin pilot/fix-footer"], guard_context)

    def test_the_configured_branches_are_protected_even_under_the_pilot_prefix(self):
        self.write_configuration("SAAS_PROJECT_ID=1234\nDEPLOYED_BRANCH=pilot/live\nTEST_BRANCH=pilot/staging\n")
        guard_context = context(state_home=self.state_home)

        self.assert_reason_mentions(
            "git push origin pilot/live",
            "pushing to pilot/live is blocked",
            guard_context=guard_context,
        )
        self.assert_commands_blocked(["git push -u origin pilot/staging"], guard_context)
        self.assert_commands_allowed(["git push -u origin pilot/fix-footer"], guard_context)

    def test_the_default_branches_stay_protected_with_a_configuration(self):
        self.write_configuration("SAAS_PROJECT_ID=1234\nDEPLOYED_BRANCH=release\nTEST_BRANCH=\n")
        guard_context = context(state_home=self.state_home)

        self.assert_commands_blocked(["git push origin release", "git push origin main"], guard_context)
        self.assert_commands_allowed(["git push origin pilot/fix-footer"], guard_context)

    def test_a_malformed_configuration_does_not_open_pushes(self):
        self.write_configuration("not a setting\n=\nDEPLOYED_BRANCH\n")
        guard_context = context(state_home=self.state_home)

        self.assert_commands_blocked(["git push origin main", "git push origin master"], guard_context)
        self.assert_commands_allowed(["git push origin pilot/fix-footer"], guard_context)
