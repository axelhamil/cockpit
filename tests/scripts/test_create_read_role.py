import os
import re
import secrets
import shlex
import subprocess
import time
import unittest

from support import ScriptTestCase

READ_WRITE = "SET default_transaction_read_only = off; "

FAKE_RAILWAY = """
printf '%s|%s\\n' "$PWD" "$*" >>"$FAKE_RAILWAY_LOG"
case $1 in
  variable)
    printf '{"PGUSER": "postgres", "DATABASE_PUBLIC_URL": "postgresql://postgres:owner-secret@proxy.example.net:41234/railway"}\\n'
    ;;
  ssh)
    exec python3 "$FAKE_PSQL_SCRIPT"
    ;;
esac
"""

SEED = """
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE ROLE app LOGIN;
GRANT ALL ON SCHEMA public TO app;
SET ROLE app;
CREATE TABLE customers (id serial PRIMARY KEY, email text);
INSERT INTO customers (email) VALUES ('ada@example.com');
CREATE TABLE payments (id int PRIMARY KEY, amount int);
INSERT INTO payments VALUES (1, 42);
CREATE TABLE secrets (id int, token text);
INSERT INTO secrets VALUES (1, 's3cr3t');
CREATE VIEW secrets_view AS SELECT * FROM secrets;
CREATE VIEW secrets_summary AS SELECT count(*) AS total FROM secrets_view;
CREATE TABLE events (id int, at date, payload text) PARTITION BY RANGE (at);
CREATE TABLE events_2026 PARTITION OF events FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
INSERT INTO events VALUES (1, '2026-05-01', 'private');
CREATE TABLE "User" (id int, name text);
INSERT INTO "User" VALUES (1, 'Ada');
CREATE TABLE rls_notes (id int, owner_name text);
INSERT INTO rls_notes VALUES (1, 'x');
ALTER TABLE rls_notes ENABLE ROW LEVEL SECURITY;
RESET ROLE;
CREATE SCHEMA billing;
CREATE TABLE billing.invoices (id int, amount int);
INSERT INTO billing.invoices VALUES (1, 100);
CREATE SCHEMA internal;
CREATE TABLE internal.audit (id int);
CREATE DATABASE other;
CREATE DATABASE fresh;
\\connect other
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE TABLE notes (id int);
INSERT INTO notes VALUES (5);
"""

RIGHTS_SNAPSHOT = (
    "WITH acls AS ("
    " SELECT 'table ' || c.oid::regclass::text AS object, coalesce(c.relacl, acldefault('r', c.relowner)) AS acl"
    " FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
    " WHERE n.nspname IN ('public', 'billing', 'internal') AND c.relkind IN ('r', 'p', 'v')"
    " UNION ALL SELECT 'schema ' || n.nspname, coalesce(n.nspacl, acldefault('n', n.nspowner)) FROM pg_namespace n"
    " UNION ALL SELECT 'database ' || d.datname, coalesce(d.datacl, acldefault('d', d.datdba)) FROM pg_database d"
    ") SELECT object, grantee::regrole, privilege_type FROM acls, aclexplode(acl) ORDER BY 1, 2, 3;"
    "SELECT count(*) FROM pg_default_acl;"
    "SELECT rolname FROM pg_roles ORDER BY 1;"
)


def docker(*arguments, stdin=None):
    return subprocess.run(
        ["docker", *arguments],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=180,
    )


class CreateReadRoleArgumentsTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.env["RP_PSQL"] = self.fake_psql_command()
        self.env["RP_CLIPBOARD"] = "cat > " + shlex.quote(self.path("clipboard"))
        self.env["RP_PUBLIC_HOST"] = "db.example.net"
        self.env["RP_PUBLIC_PORT"] = "5432"

    def test_given_invalid_names_then_exit_2_before_any_sql(self):
        cases = (
            ["create", "a;drop"],
            ["create", "Metabase"],
            ["create", ""],
            ["create", "a" * 40],
            ["create", "1tool"],
            ["create", 'tool"; DROP TABLE customers; --'],
            ["revoke", "a;drop"],
            ["revoke", "Metabase"],
            ["revoke", ""],
            ["revoke", "a" * 40],
            ["create", "metabase", "--schema", "public;drop"],
            ["create", "metabase", "--schema", "1abc"],
            ["create", "metabase", "--schema", "public,,billing"],
            ["create", "metabase", "--schema", "public, billing"],
            ["create", "metabase", "--schema", "pg_catalog"],
            ["create", "metabase", "--schema", "public,information_schema"],
            ["create", "metabase", "--schema", "s" * 64],
            ["create", "metabase", "--schema", ""],
            ["create", "metabase", "--exclude", "users,a;drop"],
            ["create", "metabase", "--exclude", "users,,payments"],
            ["create", "metabase", "--exclude", "users, payments"],
            ["create", "metabase", "--exclude", "users'--"],
            ["create", "metabase", "--exclude", ""],
            ["create", "metabase", "--exclude", "*"],
            ["create", "metabase", "--database", "rail way"],
            ["create", "metabase", "--unknown", "x"],
            ["create", "metabase", "--schema"],
            ["drop", "metabase"],
            ["create"],
            [],
        )

        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.run_script("create-read-role.sh", *arguments)

                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.strip())

        self.assertFalse(self.exists("received.sql"))
        self.assertFalse(self.exists("clipboard"))

    def test_given_mixed_case_names_then_they_reach_postgres_as_values_never_as_bare_sql(self):
        result = self.run_script("create-read-role.sh", "create", "metabase", "--schema", "Public,billing", "--exclude", "User,Order")

        self.assertEqual(result.returncode, 0, result.stderr)
        received = self.read("received.sql")
        self.assertIn("'Public,billing'", received)
        self.assertIn("'User,Order'", received)
        self.assertEqual(received.count("Public"), 1)
        self.assertEqual(received.count("Order"), 1)
        self.assertEqual(received.count("metabase_read"), 1)

    def test_given_no_service_outside_test_mode_then_exit_2_before_any_sql(self):
        del self.env["RP_PSQL"]
        self.install_fake_railway(FAKE_RAILWAY)
        self.env["FAKE_RAILWAY_LOG"] = self.path("railway.log")

        for arguments in (["create", "metabase"], ["revoke", "metabase"], ["create", "metabase", "--service", "-s injected"]):
            with self.subTest(arguments=arguments):
                result = self.run_script("create-read-role.sh", *arguments)

                self.assertEqual(result.returncode, 2)
                self.assertIn("service", result.stderr)

        self.assertFalse(self.exists("railway.log"))

    def test_given_test_overrides_without_the_test_switch_then_they_are_ignored(self):
        del self.env["RP_TEST"]

        result = self.run_script("create-read-role.sh", "create", "metabase")

        self.assertEqual(result.returncode, 2)
        self.assertIn("service", result.stderr)
        self.assertFalse(self.exists("received.sql"))
        self.assertFalse(self.exists("clipboard"))

    def test_given_the_sql_runner_fails_then_exit_1_and_the_clipboard_stays_empty(self):
        self.env["RP_PSQL"] = "cat >/dev/null; echo 'ERROR:  permission denied to create role' >&2; exit 3"

        result = self.run_script("create-read-role.sh", "create", "metabase")

        self.assertEqual(result.returncode, 1)
        self.assertIn("permission denied to create role", result.stderr)
        self.assertFalse(self.exists("clipboard"))

    def test_given_a_runner_that_only_echoes_the_sql_then_it_is_not_taken_for_a_success(self):
        for runner in ("cat", "cat; echo 'ERROR: connection closed'", "cat >/dev/null"):
            with self.subTest(runner=runner):
                self.env["RP_PSQL"] = runner

                created = self.run_script("create-read-role.sh", "create", "metabase")
                revoked = self.run_script("create-read-role.sh", "revoke", "metabase")

                self.assertEqual(created.returncode, 1)
                self.assertEqual(revoked.returncode, 1)
                self.assertNotIn("SCRAM-SHA-256", created.stdout + created.stderr)
                self.assertFalse(self.exists("clipboard"))

    def test_given_an_error_line_next_to_the_completion_mark_then_exit_1(self):
        for line in ("ERROR:  relation does not exist", "psql: FATAL:  the database system is shutting down"):
            with self.subTest(line=line):
                self.env["FAKE_PSQL_OUTPUT"] = line

                result = self.run_script("create-read-role.sh", "create", "metabase")

                self.assertEqual(result.returncode, 1)
                self.assertFalse(self.exists("clipboard"))


class CreateReadRoleRailwayPathTest(ScriptTestCase):
    def setUp(self):
        super().setUp()
        self.fake_psql_command()
        self.install_fake_railway(FAKE_RAILWAY)
        self.env["FAKE_PSQL_SCRIPT"] = self.path("fake_psql.py")
        self.env["FAKE_RAILWAY_LOG"] = self.path("railway.log")
        self.env["RP_CLIPBOARD"] = "cat > " + shlex.quote(self.path("clipboard"))
        os.makedirs(self.path("pilot-home/saas-project"))

    def test_create_reads_the_public_address_and_sends_the_sql_on_stdin_from_the_saas_folder(self):
        result = self.run_script("create-read-role.sh", "create", "metabase", "--service", "Postgres", "--database", "app")

        self.assertEqual(result.returncode, 0, result.stderr)
        saas_folder = os.path.realpath(self.path("pilot-home/saas-project"))
        calls = [line.split("|", 1) for line in self.read("railway.log").splitlines()]
        self.assertEqual({os.path.realpath(folder) for folder, _ in calls}, {saas_folder})
        self.assertEqual(
            [arguments for _, arguments in calls],
            ["variable list -s Postgres --json", "ssh -s Postgres -- psql -U postgres -d app -v ON_ERROR_STOP=1"],
        )
        password = self.read("clipboard")
        self.assertRegex(password, r"\A[0-9a-f]{48}\Z")
        self.assertIn("CREATE ROLE", self.read("received.sql"))
        for secret in (password, "owner-secret"):
            self.assertNotIn(secret, result.stdout + result.stderr)
            self.assertNotIn(secret, self.read("railway.log"))
            self.assertNotIn(secret, self.read("received.sql"))
        self.assertEqual(
            result.stdout.splitlines()[:5],
            [
                "Read-only access for metabase is ready. The password is on the clipboard: paste it in the password field of the tool.",
                "host: proxy.example.net",
                "port: 41234",
                "database: app",
                "user: metabase_read",
            ],
        )

    def test_given_no_saas_folder_then_exit_1_with_a_readable_message(self):
        os.rmdir(self.path("pilot-home/saas-project"))

        result = self.run_script("create-read-role.sh", "create", "metabase", "--service", "Postgres")

        self.assertEqual(result.returncode, 1)
        self.assertIn("SaaS project", result.stderr)
        self.assertFalse(self.exists("railway.log"))


class PostgresRoleScenarios:
    image = None
    public_schema_open_by_default = False
    container = None

    @classmethod
    def setUpClass(cls):
        try:
            available = docker("info").returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            available = False

        if not available:
            raise unittest.SkipTest("Docker is not available: the read-only role is not proven against a real Postgres in this run")

        name = "railway-pilot-test-" + secrets.token_hex(4)
        started = docker(
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--env",
            "POSTGRES_PASSWORD=" + secrets.token_hex(12),
            "--env",
            "POSTGRES_DB=railway",
            cls.image,
        )

        if started.returncode != 0:
            raise unittest.SkipTest("The {} container could not start: {}".format(cls.image, started.stderr.strip()))

        cls.container = name
        cls.addClassCleanup(docker, "rm", "--force", "--volumes", name)
        cls.wait_until_ready()
        cls.host = docker("inspect", "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name).stdout.strip()
        seeded = cls.admin(SEED)
        assert seeded.returncode == 0, seeded.stderr

    @classmethod
    def wait_until_ready(cls):
        deadline = time.time() + 90

        while time.time() < deadline:
            probe = docker("exec", cls.container, "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "railway", "-c", "SELECT 1")

            if probe.returncode == 0:
                return

            time.sleep(0.5)

        raise AssertionError("Postgres did not become ready in the test container")

    @classmethod
    def admin(cls, sql, database="railway"):
        return docker("exec", "-i", cls.container, "psql", "-U", "postgres", "-d", database, "-v", "ON_ERROR_STOP=1", "-At", stdin=sql)

    def setUp(self):
        super().setUp()
        self.use_database("railway")
        self.env["RP_CLIPBOARD"] = "cat > " + shlex.quote(self.path("clipboard"))
        self.env["RP_PUBLIC_HOST"] = self.host
        self.env["RP_PUBLIC_PORT"] = "5432"

    def use_database(self, database):
        self.env["RP_PSQL"] = "docker exec -i {} psql -U postgres -d {}".format(self.container, database)

    def create(self, tool, *options):
        self.tool = tool
        return self.run_script("create-read-role.sh", "create", tool, *options)

    def revoke(self, tool):
        return self.run_script("create-read-role.sh", "revoke", tool)

    def created(self, tool, *options):
        result = self.create(tool, *options)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def connection_string(self, password, database="railway"):
        return "postgresql://{}_read:{}@{}:5432/{}".format(self.tool, password, self.host, database)

    def query(self, connection_string, sql):
        return docker("exec", "-i", self.container, "psql", connection_string, "-v", "ON_ERROR_STOP=1", "-At", stdin=sql)

    def as_role(self, sql, database="railway"):
        return self.query(self.connection_string(self.read("clipboard"), database), sql)

    def role_exists(self, role):
        return self.admin("SELECT count(*) FROM pg_roles WHERE rolname = '{}'".format(role)).stdout.strip() == "1"

    def assert_denied(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, "permission denied|must be owner")

    def test_given_a_created_role_then_it_reads_but_every_write_is_denied(self):
        self.addCleanup(self.revoke, "metabase")

        self.created("metabase")

        self.assertEqual(self.as_role("SELECT email FROM customers").stdout.strip(), "ada@example.com")
        self.assertEqual(self.as_role("SHOW default_transaction_read_only").stdout.strip(), "on")
        self.assertEqual(self.as_role("SHOW statement_timeout").stdout.strip(), "30s")
        self.assertIn("read-only transaction", self.as_role("INSERT INTO payments VALUES (2, 1)").stderr)
        for statement in (
            "INSERT INTO payments VALUES (2, 1)",
            "INSERT INTO customers (email) VALUES ('x')",
            "UPDATE customers SET email = 'x'",
            "DELETE FROM customers",
            "TRUNCATE customers",
            "CREATE TABLE notes (id int)",
            "CREATE TABLE public.junk (id int)",
            "CREATE SCHEMA mine",
            "DROP TABLE customers",
            "SELECT * FROM billing.invoices",
            "SELECT * FROM internal.audit",
            "SELECT nextval('customers_id_seq')",
            "SET ROLE postgres",
        ):
            with self.subTest(statement=statement):
                self.assert_denied(self.as_role(READ_WRITE + statement))
        self.assertEqual(self.admin("SELECT count(*) FROM customers").stdout.strip(), "1")

    def test_given_the_clipboard_then_it_holds_only_the_password_which_is_never_printed(self):
        self.addCleanup(self.revoke, "n8n")

        created = self.created("n8n")

        password = self.read("clipboard")
        self.assertRegex(password, r"\A[0-9a-f]{48}\Z")
        self.assertNotIn(password, created.stdout + created.stderr)
        self.assertEqual(
            created.stdout.splitlines()[1:5],
            ["host: " + self.host, "port: 5432", "database: railway", "user: n8n_read"],
        )
        self.assertIn("clipboard", created.stdout.splitlines()[0])
        self.assertEqual(self.as_role("SELECT current_user").stdout.strip(), "n8n_read")
        wrong = self.query(self.connection_string("0" * 48), "SELECT 1")
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("password authentication failed", wrong.stderr)
        self.assertNotIn(password, self.admin("SELECT rolpassword FROM pg_authid WHERE rolname = 'n8n_read'").stdout)

    def test_given_excluded_tables_then_they_are_unreadable_and_the_others_stay_readable(self):
        self.addCleanup(self.revoke, "grafana")

        self.created("grafana", "--exclude", "payments,User")

        self.assert_denied(self.as_role("SELECT * FROM payments"))
        self.assert_denied(self.as_role('SELECT * FROM "User"'))
        self.assert_denied(self.as_role("SELECT amount FROM payments"))
        self.assertEqual(self.as_role("SELECT email FROM customers").stdout.strip(), "ada@example.com")

    def test_given_an_excluded_partitioned_table_then_its_partitions_are_unreadable_too(self):
        self.addCleanup(self.revoke, "hex")

        self.created("hex", "--exclude", "events")

        self.assert_denied(self.as_role("SELECT * FROM events"))
        self.assert_denied(self.as_role("SELECT payload FROM events_2026"))

    def test_given_views_over_an_excluded_table_then_create_fails_until_they_are_excluded_too(self):
        self.addCleanup(self.revoke, "mode")

        refused = self.create("mode", "--exclude", "secrets")

        self.assertEqual(refused.returncode, 1)
        self.assertIn("secrets_view", refused.stderr)
        self.assertIn("secrets_summary", refused.stderr)
        self.assertIn("--exclude", refused.stderr)
        self.assertFalse(self.role_exists("mode_read"))
        self.assertFalse(self.exists("clipboard"))

        self.created("mode", "--exclude", "secrets,secrets_view,secrets_summary")

        for relation in ("secrets", "secrets_view", "secrets_summary"):
            self.assert_denied(self.as_role("SELECT * FROM " + relation))

    def test_given_a_table_created_afterwards_by_the_application_role_then_it_is_readable_but_not_writable(self):
        self.addCleanup(self.revoke, "superset")
        self.addCleanup(self.admin, "DROP TABLE IF EXISTS invoices_later")
        self.created("superset")

        self.admin("SET ROLE app; CREATE TABLE invoices_later (id int); INSERT INTO invoices_later VALUES (7)")

        self.assertEqual(self.as_role("SELECT id FROM invoices_later").stdout.strip(), "7")
        self.assert_denied(self.as_role(READ_WRITE + "INSERT INTO invoices_later VALUES (8)"))

    def test_given_a_second_create_with_one_more_exclusion_then_it_applies_and_the_password_is_renewed(self):
        self.addCleanup(self.revoke, "redash")
        self.created("redash", "--exclude", "User")
        first_password = self.read("clipboard")
        self.assertEqual(self.as_role("SELECT amount FROM payments").stdout.strip(), "42")

        self.created("redash", "--exclude", "User,payments")

        self.assertNotEqual(self.read("clipboard"), first_password)
        self.assert_denied(self.as_role("SELECT * FROM payments"))
        self.assert_denied(self.as_role('SELECT * FROM "User"'))
        self.assertEqual(self.as_role("SELECT email FROM customers").stdout.strip(), "ada@example.com")
        self.assertIn("password authentication failed", self.query(self.connection_string(first_password), "SELECT 1").stderr)

    def test_given_a_second_create_without_the_exclusion_then_the_table_is_readable_again(self):
        self.addCleanup(self.revoke, "lightdash")
        self.created("lightdash", "--exclude", "payments")

        self.created("lightdash")

        self.assertEqual(self.as_role("SELECT amount FROM payments").stdout.strip(), "42")

    def test_given_a_schema_list_then_exactly_those_schemas_are_readable(self):
        self.addCleanup(self.revoke, "evidence")

        self.created("evidence", "--schema", "public,billing", "--exclude", "payments")

        self.assertEqual(self.as_role("SELECT email FROM customers").stdout.strip(), "ada@example.com")
        self.assertEqual(self.as_role("SELECT amount FROM billing.invoices").stdout.strip(), "100")
        self.assert_denied(self.as_role("SELECT * FROM payments"))
        self.assert_denied(self.as_role("SELECT * FROM internal.audit"))

        self.created("evidence", "--schema", "billing")

        self.assertEqual(self.as_role("SELECT amount FROM billing.invoices").stdout.strip(), "100")
        self.assert_denied(self.as_role("SELECT * FROM customers"))

    def test_given_a_schema_that_does_not_exist_then_no_role_is_created(self):
        created = self.create("ghost", "--schema", "public,Billing")

        self.assertEqual(created.returncode, 1)
        self.assertIn("Billing", created.stderr)
        self.assertFalse(self.role_exists("ghost_read"))

    def test_given_revoke_then_the_role_is_gone_and_a_second_revoke_still_succeeds(self):
        self.created("retool")
        self.assertTrue(self.role_exists("retool_read"))

        revoked = self.revoke("retool")
        revoked_again = self.revoke("retool")

        self.assertEqual(revoked.returncode, 0, revoked.stderr)
        self.assertFalse(self.role_exists("retool_read"))
        self.assertNotEqual(self.as_role("SELECT 1").returncode, 0)
        self.assertEqual(revoked_again.returncode, 0, revoked_again.stderr)
        self.assertEqual(self.admin("SELECT count(*) FROM customers").stdout.strip(), "1")

    def test_given_a_role_with_rights_in_two_databases_then_revoke_closes_the_access_and_names_the_other_database(self):
        self.created("nocodb")
        self.use_database("other")
        self.created("nocodb", "--database", "other")
        self.assertEqual(self.as_role("SELECT id FROM notes", "other").stdout.strip(), "5")
        self.use_database("railway")

        first = self.revoke("nocodb")

        self.assertEqual(first.returncode, 1)
        self.assertIn("other", first.stderr)
        self.assertIn("--database", first.stderr)
        self.assertTrue(self.role_exists("nocodb_read"))
        for database in ("railway", "other"):
            self.assertIn("not permitted to log in", self.as_role("SELECT 1", database).stderr)

        self.use_database("other")
        second = self.revoke("nocodb")

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(self.role_exists("nocodb_read"))

    def test_given_a_role_of_the_client_with_the_same_name_then_it_is_left_untouched(self):
        self.addCleanup(self.admin, "DROP OWNED BY legacy_read; DROP ROLE legacy_read")
        self.admin("CREATE ROLE legacy_read LOGIN; GRANT SELECT ON internal.audit TO legacy_read")
        grants = "SELECT has_table_privilege('legacy_read', 'internal.audit', 'SELECT'), rolcanlogin FROM pg_roles WHERE rolname = 'legacy_read'"

        created = self.create("legacy")
        revoked = self.revoke("legacy")

        self.assertEqual(created.returncode, 1)
        self.assertIn("was not created by railway-pilot", created.stderr)
        self.assertFalse(self.exists("clipboard"))
        self.assertEqual(revoked.returncode, 1)
        self.assertEqual(self.admin(grants).stdout.strip(), "t|t")

    def test_given_an_excluded_table_that_does_not_exist_then_no_role_is_created(self):
        created = self.create("typo", "--exclude", "paymets")

        self.assertEqual(created.returncode, 1)
        self.assertIn("paymets", created.stderr)
        self.assertFalse(self.role_exists("typo_read"))
        self.assertFalse(self.exists("clipboard"))

    def test_given_any_write_path_open_to_every_role_then_no_role_is_created_and_the_object_is_named(self):
        cases = (
            ("GRANT INSERT, DELETE ON billing.invoices TO PUBLIC", "REVOKE ALL ON billing.invoices FROM PUBLIC", "public", "billing.invoices"),
            ("GRANT UPDATE (email) ON customers TO PUBLIC", "REVOKE UPDATE (email) ON customers FROM PUBLIC", "public", "public.customers"),
            ("GRANT REFERENCES ON payments TO PUBLIC", "REVOKE ALL ON payments FROM PUBLIC", "public", "public.payments"),
            ("GRANT TRIGGER ON internal.audit TO PUBLIC", "REVOKE ALL ON internal.audit FROM PUBLIC", "public", "internal.audit"),
            (
                "CREATE FUNCTION wipe_customers() RETURNS void LANGUAGE sql SECURITY DEFINER AS 'DELETE FROM public.customers'",
                "DROP FUNCTION wipe_customers()",
                "public",
                "wipe_customers()",
            ),
            ("GRANT CREATE ON SCHEMA public TO PUBLIC", "REVOKE CREATE ON SCHEMA public FROM PUBLIC", "billing", "public"),
            (
                "CREATE SEQUENCE billing.counter; GRANT USAGE ON SEQUENCE billing.counter TO PUBLIC",
                "DROP SEQUENCE billing.counter",
                "public",
                "billing.counter",
            ),
        )

        for opening, closing, schema, offender in cases:
            with self.subTest(opening=opening):
                self.assertEqual(self.admin(opening).returncode, 0)
                try:
                    created = self.create("open", "--schema", schema)
                finally:
                    self.assertEqual(self.admin(closing).returncode, 0)

                self.assertEqual(created.returncode, 1)
                self.assertIn(offender, created.stderr)
                self.assertIn("PUBLIC", created.stderr)
                self.assertIn("developer", created.stderr)
                self.assertFalse(self.role_exists("open_read"))
                self.assertFalse(self.exists("clipboard"))

    def test_given_a_database_left_with_its_default_rights_then_the_outcome_follows_the_postgres_version(self):
        self.addCleanup(self.revoke, "blank")
        self.use_database("fresh")

        created = self.create("blank", "--database", "fresh")

        if self.public_schema_open_by_default:
            self.assertEqual(created.returncode, 1)
            self.assertIn("public", created.stderr)
            self.assertIn("PUBLIC", created.stderr)
            self.assertFalse(self.role_exists("blank_read"))
        else:
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assert_denied(self.as_role(READ_WRITE + "CREATE TABLE public.junk (id int)", "fresh"))

    def test_given_tables_under_row_level_security_then_a_warning_names_them(self):
        self.addCleanup(self.revoke, "posthog")

        created = self.created("posthog")

        warnings = [line for line in created.stdout.splitlines() if line.startswith("warning: ")]
        self.assertEqual(len(warnings), 2, created.stdout)
        self.assertIn("row level security", warnings[0])
        self.assertIn("public.rls_notes", warnings[0])
        self.assertIn("created later", warnings[1])
        self.assertIn("app", warnings[1])
        self.assertEqual(self.as_role("SELECT count(*) FROM rls_notes").stdout.strip(), "0")

    def test_create_and_revoke_leave_the_rights_of_public_and_other_roles_unchanged(self):
        before = self.admin(RIGHTS_SNAPSHOT).stdout

        self.created("budibase", "--schema", "public,billing", "--exclude", "payments")
        self.revoke("budibase")

        self.assertEqual(self.admin(RIGHTS_SNAPSHOT).stdout, before)


class CreateReadRolePostgres17Test(PostgresRoleScenarios, ScriptTestCase):
    image = "postgres:17"


class CreateReadRolePostgres14Test(PostgresRoleScenarios, ScriptTestCase):
    image = "postgres:14"
    public_schema_open_by_default = True
