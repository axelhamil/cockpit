import json
import shlex

from support import ScriptTestCase

PASSWORD = "s3cr3t-p@ss"
PUBLIC_URL = "postgresql://postgres:s3cr3t-p%40ss@shuttle.proxy.rlwy.net:15140/railway"


class DatabaseAccessTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.write("pilot-home/saas-project/.keep", "")
        self.env["RP_CLIPBOARD"] = "cat > " + shlex.quote(self.path("clipboard"))
        self.railway_answers({"DATABASE_PUBLIC_URL": PUBLIC_URL, "PGDATA": "/var/lib/postgresql/data"})

    def railway_answers(self, payload):
        self.write("variables.json", json.dumps(payload))
        self.install_fake_railway('cat "' + self.path("variables.json") + '"\n')

    def access(self, *arguments):
        return self.run_script("database-access.sh", *arguments)

    def test_given_a_public_address_then_the_password_goes_to_the_clipboard_only(self):
        result = self.access("--service", "Postgres")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("clipboard"), PASSWORD)
        self.assertIn("host: shuttle.proxy.rlwy.net", result.stdout)
        self.assertIn("port: 15140", result.stdout)
        self.assertIn("database: railway", result.stdout)
        self.assertIn("user: postgres", result.stdout)
        self.assertNotIn(PASSWORD, result.stdout + result.stderr)
        self.assertNotIn("s3cr3t", result.stdout + result.stderr)

    def test_given_variables_listed_as_name_value_pairs_then_they_are_read_the_same_way(self):
        self.railway_answers([{"name": "DATABASE_PUBLIC_URL", "value": PUBLIC_URL}])

        result = self.access("--service", "Postgres")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read("clipboard"), PASSWORD)

    def test_given_the_private_mode_then_the_internal_address_is_given(self):
        self.railway_answers(
            {
                "DATABASE_PUBLIC_URL": PUBLIC_URL,
                "DATABASE_URL": "postgresql://postgres:s3cr3t-p%40ss@postgres.railway.internal:5432/railway",
            }
        )

        result = self.access("--service", "Postgres", "--private")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("host: postgres.railway.internal", result.stdout)
        self.assertIn("port: 5432", result.stdout)
        self.assertEqual(self.read("clipboard"), PASSWORD)
        self.assertNotIn("s3cr3t", result.stdout + result.stderr)

    def test_given_the_private_mode_without_an_address_then_no_public_address_is_suggested(self):
        self.railway_answers({"PGDATA": "/var/lib/postgresql/data"})

        result = self.access("--service", "Postgres", "--private")

        self.assertEqual(result.returncode, 1)
        self.assertIn("no database address", result.stderr)
        self.assertNotIn("tcp-proxy", result.stderr)
        self.assertFalse(self.exists("clipboard"))

    def test_given_the_private_option_first_then_it_works_the_same(self):
        self.railway_answers({"DATABASE_URL": "postgresql://postgres:s3cr3t-p%40ss@postgres.railway.internal:5432/railway"})

        result = self.access("--private", "--service", "Postgres")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("host: postgres.railway.internal", result.stdout)

    def test_given_an_option_in_place_of_the_service_name_then_the_usage_is_shown(self):
        result = self.access("--service", "--private")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage", result.stderr)

    def test_given_an_unknown_option_then_the_usage_is_shown(self):
        result = self.access("--service", "Postgres", "--public")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage", result.stderr)

    def test_given_no_public_address_then_nothing_is_copied_and_the_message_says_how_to_create_one(self):
        self.railway_answers({"DATABASE_URL": "postgresql://postgres:x@postgres.railway.internal:5432/railway"})

        result = self.access("--service", "Postgres")

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.exists("clipboard"))
        self.assertIn("tcp-proxy create", result.stderr)

    def test_given_an_unreadable_answer_then_the_message_does_not_send_to_the_public_address(self):
        self.write("variables.json", "not json")

        result = self.access("--service", "Postgres")

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.exists("clipboard"))
        self.assertIn("could not be read", result.stderr)
        self.assertNotIn("tcp-proxy", result.stderr)

    def test_given_railway_fails_then_the_message_is_readable(self):
        self.install_fake_railway("exit 1\n")

        result = self.access("--service", "Postgres")

        self.assertEqual(result.returncode, 1)
        self.assertIn("whoami", result.stderr)

    def test_given_no_service_then_the_usage_is_shown(self):
        result = self.access()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage", result.stderr)
