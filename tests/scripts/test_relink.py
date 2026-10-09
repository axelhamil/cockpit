from support import ScriptTestCase

SAAS_ID = "11111111-1111-1111-1111-111111111111"
TOOLS_ID = "22222222-2222-2222-2222-222222222222"
APP_STATE = (
    "---\nprovider: railway\nonboarding: complete\nonboarding_step: check\n---\n\n"
    "## SaaS project\n"
    "- Project: Acme Studio ({})\n"
    "- Production environment: production\n"
    "- App service: web, repository acme/app, deployed branch main\n"
    "- Postgres service: Postgres\n\n"
    "## Tools project\n"
    "- Project: Acme Studio tools ({})\n"
).format(SAAS_ID, TOOLS_ID)


class RelinkTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.write_v2_state("acme-studio")
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE)
        self.write("cockpit-home/projects/acme-studio/saas-project/.keep", "")
        self.write("cockpit-home/projects/acme-studio/tools-project/.keep", "")
        self.write("cockpit-home/projects/acme-studio/.relink", "")
        self.log = self.path("railway.log")

    def railway_records(self, exit_code=0):
        self.install_fake_railway('{ pwd; echo "$@"; } >>"' + self.log + '"\nexit ' + str(exit_code) + "\n")

    def relink(self, *arguments):
        return self.run_script("relink.sh", *arguments)

    def test_given_the_folders_were_moved_then_each_one_is_linked_again_and_the_marker_goes(self):
        self.railway_records()
        project = self.path("cockpit-home/projects/acme-studio")

        result = self.relink("--project", "acme-studio")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.read("railway.log").splitlines(),
            [
                project + "/saas-project",
                "link -p {} -e production -s web".format(SAAS_ID),
                project + "/tools-project",
                "link -p {} -e production".format(TOOLS_ID),
            ],
        )
        self.assertFalse(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_railway_refuses_then_the_marker_stays_and_the_error_says_what_to_check(self):
        self.railway_records(exit_code=1)

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertIn("railway whoami", result.stderr)
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))

    def test_given_nothing_to_refresh_then_railway_is_not_called(self):
        self.railway_records()
        self.relink()
        self.write("railway.log", "")

        result = self.relink()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("railway.log"), "")

    def test_given_an_id_that_could_pass_for_an_option_then_railway_is_not_called(self):
        self.railway_records()
        self.write("cockpit-home/projects/acme-studio/state.md", APP_STATE.replace(SAAS_ID, "--help"))

        result = self.relink()

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.exists("railway.log"))
        self.assertTrue(self.exists("cockpit-home/projects/acme-studio/.relink"))
