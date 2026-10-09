#!/bin/sh
set -eu

LC_ALL=C
export LC_ALL

if [ "${RP_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN RP_PSQL RP_CLIPBOARD RP_PUBLIC_HOST RP_PUBLIC_PORT RP_PASTE RP_CLEAR_CLIPBOARD GH_BIN RP_BIN_DIR RP_SHELL_PROFILE CLAUDE_SETTINGS
fi

state_home=${RAILWAY_PILOT_HOME:-$HOME/.railway-pilot}
saas_dir=$state_home/saas-project
railway_bin=${RAILWAY_BIN:-railway}
clipboard=${RP_CLIPBOARD:-pbcopy}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='Usage: create-read-role.sh create <tool> --service <postgres service> [--schema public,billing] [--exclude table1,table2] [--database railway]
       create-read-role.sh revoke <tool> --service <postgres service> [--database railway]
create gives <tool>_read read access to exactly the listed schemas (default: public): running it again replaces
the previous schemas and exclusions and renews the password. Each excluded name is hidden in every listed schema.'

schemas=public
exclude=
exclude_given=0
service=
database=railway

fail_usage() {
  printf '%s\n' "$1" >&2
  exit 2
}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

valid_tool() {
  case $1 in
    '' | [!a-z]* | *[!a-z0-9_]*) return 1 ;;
  esac
  [ ${#1} -le 31 ]
}

valid_name() {
  case $1 in
    '' | [!A-Za-z_]* | *[!A-Za-z0-9_]*) return 1 ;;
  esac
  [ ${#1} -le 63 ]
}

valid_name_list() {
  case $1 in
    '' | ,* | *, | *,,*) return 1 ;;
  esac

  list_is_valid=0
  set -f
  old_ifs=$IFS
  IFS=,
  for name in $1; do
    if ! valid_name "$name"; then
      list_is_valid=1
    fi
  done
  IFS=$old_ifs
  set +f

  return "$list_is_valid"
}

names_a_system_schema() {
  case ",$1," in
    *,pg_* | *,information_schema,*) return 0 ;;
  esac
  return 1
}

valid_service() {
  case $1 in
    '' | -* | *[!A-Za-z0-9._\ -]*) return 1 ;;
  esac
  [ ${#1} -le 64 ]
}

valid_host() {
  case $1 in
    '' | -* | *[!A-Za-z0-9.-]*) return 1 ;;
  esac
}

valid_port() {
  case $1 in
    '' | *[!0-9]*) return 1 ;;
  esac
  [ ${#1} -le 5 ]
}

random_hex() {
  generated=$(openssl rand -hex "$1") || return 1

  case $generated in
    '' | *[!0-9a-f]*) return 1 ;;
  esac

  printf '%s' "$generated"
}

read_public_endpoint() {
  if [ -n "${RP_PUBLIC_HOST:-}" ] && [ -n "${RP_PUBLIC_PORT:-}" ]; then
    printf '%s %s\n' "$RP_PUBLIC_HOST" "$RP_PUBLIC_PORT"
    return 0
  fi

  (cd "$saas_dir" && "$railway_bin" variable list -s "$service" --json 2>/dev/null) | python3 "$script_dir/railway_json.py" public-endpoint 2>/dev/null
}

run_sql() {
  if [ -n "${RP_PSQL:-}" ]; then
    sh -c "$RP_PSQL"
    return
  fi

  (cd "$saas_dir" && "$railway_bin" ssh -s "$service" -- psql -U postgres -d "$database" -v ON_ERROR_STOP=1)
}

sql_setting() {
  printf "SELECT set_config('rp.%s', '%s', false) IS NOT NULL AS configured;\n" "$1" "$2"
}

sql_completion() {
  printf "SELECT 'rp-' || md5('%s') AS completion;\n" "$nonce"
}

create_sql() {
  printf '%s\n' '\set ON_ERROR_STOP on'
  sql_setting role "$role"
  sql_setting schemas "$schemas"
  sql_setting excluded "$exclude"
  sql_setting verifier "$verifier"
  cat <<'SQL'
BEGIN;

DO $rp$
DECLARE
  target_role constant text := current_setting('rp.role');
  marker constant text := 'railway-pilot read-only role';
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = target_role) THEN
    EXECUTE format('CREATE ROLE %I', target_role);
    EXECUTE format('COMMENT ON ROLE %I IS %L', target_role, marker);
  ELSIF shobj_description((SELECT oid FROM pg_roles WHERE rolname = target_role), 'pg_authid') IS DISTINCT FROM marker THEN
    RAISE EXCEPTION 'railway-pilot: a database role named % already exists and was not created by railway-pilot, so it is left untouched. Choose another tool name', target_role;
  END IF;

  EXECUTE format('DROP OWNED BY %I', target_role);
  EXECUTE format(
    'ALTER ROLE %I WITH LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L',
    target_role,
    current_setting('rp.verifier')
  );
  EXECUTE format('ALTER ROLE %I SET default_transaction_read_only = on', target_role);
  EXECUTE format('ALTER ROLE %I SET statement_timeout = %L', target_role, '30s');
  EXECUTE format('ALTER ROLE %I SET idle_in_transaction_session_timeout = %L', target_role, '60s');
END
$rp$;

DO $rp$
DECLARE
  target_role constant text := current_setting('rp.role');
  schemas constant text[] := string_to_array(current_setting('rp.schemas'), ',');
  excluded constant text[] := string_to_array(current_setting('rp.excluded'), ',');
  schema_name text;
  owner_name text;
  missing text;
  hidden oid[];
  relation record;
BEGIN
  SELECT string_agg(wanted, ', ') INTO missing
  FROM unnest(schemas) AS wanted
  WHERE NOT EXISTS (SELECT FROM pg_namespace n WHERE n.nspname = wanted);

  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: these schemas do not exist in database %: %. Check the spelling, capital letters count', current_database(), missing;
  END IF;

  SELECT string_agg(wanted, ', ') INTO missing
  FROM unnest(excluded) AS wanted
  WHERE NOT EXISTS (
    SELECT FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = wanted AND n.nspname = ANY (schemas) AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
  );

  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: these excluded tables were not found in the listed schemas: %. Check the spelling, capital letters count', missing;
  END IF;

  EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), target_role);

  FOREACH schema_name IN ARRAY schemas LOOP
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO %I', schema_name, target_role);
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO %I', schema_name, target_role);

    FOR owner_name IN
      SELECT current_user::text
      UNION
      SELECT pg_get_userbyid(c.relowner)::text
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = schema_name AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
    LOOP
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT ON TABLES TO %I', owner_name, schema_name, target_role);
    END LOOP;
  END LOOP;

  WITH RECURSIVE hidden_relations AS (
    SELECT c.oid
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = ANY (excluded) AND n.nspname = ANY (schemas) AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
    UNION
    SELECT i.inhrelid
    FROM pg_inherits i
    JOIN hidden_relations h ON h.oid = i.inhparent
  )
  SELECT coalesce(array_agg(oid), '{}') INTO hidden FROM hidden_relations;

  FOR relation IN
    SELECT n.nspname, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.oid = ANY (hidden)
  LOOP
    EXECUTE format('REVOKE ALL ON TABLE %I.%I FROM %I', relation.nspname, relation.relname, target_role);
  END LOOP;

  PERFORM set_config('rp.hidden', array_to_string(hidden, ','), false);
END
$rp$;

DO $rp$
DECLARE
  target_role constant text := current_setting('rp.role');
  schemas constant text[] := string_to_array(current_setting('rp.schemas'), ',');
  hidden constant oid[] := coalesce(string_to_array(nullif(current_setting('rp.hidden'), ''), ',')::oid[], '{}');
  remedy constant text := 'A developer must remove that right from PUBLIC in the database, then this step can run again';
  found text;
BEGIN
  IF EXISTS (SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member WHERE r.rolname = target_role) THEN
    RAISE EXCEPTION 'railway-pilot: the role % is a member of another role, so it may hold more than read access. A developer must review it', target_role;
  END IF;

  IF has_database_privilege(target_role, current_database(), 'CREATE') THEN
    RAISE EXCEPTION 'railway-pilot: every role may create schemas in database %, so % would not be read-only. %', current_database(), target_role, remedy;
  END IF;

  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT quote_ident(n.nspname) AS name
    FROM pg_namespace n
    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' AND has_schema_privilege(target_role, n.oid, 'CREATE')
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: every role may create tables in these schemas, so % would not be read-only: %. %', target_role, found, remedy;
  END IF;

  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT format('%I.%I', n.nspname, c.relname) AS name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
      AND (
        has_table_privilege(target_role, c.oid, 'INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER')
        OR has_any_column_privilege(target_role, c.oid, 'INSERT, UPDATE, REFERENCES')
      )
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: every role may change these tables or some of their columns, so % would not be read-only: %. %', target_role, found, remedy;
  END IF;

  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT format('%I.%I', n.nspname, c.relname) AS name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
      AND CASE WHEN c.relkind = 'S' THEN has_sequence_privilege(target_role, c.oid, 'USAGE, UPDATE') ELSE false END
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: every role may advance these sequences, so % would not be read-only: %. %', target_role, found, remedy;
  END IF;

  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT p.oid::regprocedure::text AS name
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
      AND p.prosecdef
      AND has_function_privilege(target_role, p.oid, 'EXECUTE')
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: every role may run these functions, which act with the rights of their owner, so % would not be read-only: %. %', target_role, found, remedy;
  END IF;

  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT format('%I.%I', n.nspname, c.relname) AS name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.oid = ANY (hidden)
      AND (has_table_privilege(target_role, c.oid, 'SELECT') OR has_any_column_privilege(target_role, c.oid, 'SELECT'))
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: every role may read these excluded tables, so they cannot be hidden from %: %. %', target_role, found, remedy;
  END IF;

  WITH RECURSIVE dependent_views AS (
    SELECT r.ev_class AS oid
    FROM pg_depend d
    JOIN pg_rewrite r ON r.oid = d.objid
    WHERE d.classid = 'pg_rewrite'::regclass
      AND d.refclassid = 'pg_class'::regclass
      AND d.refobjid = ANY (hidden)
      AND r.ev_class <> d.refobjid
    UNION
    SELECT r.ev_class
    FROM pg_depend d
    JOIN pg_rewrite r ON r.oid = d.objid
    JOIN dependent_views v ON v.oid = d.refobjid
    WHERE d.classid = 'pg_rewrite'::regclass
      AND d.refclassid = 'pg_class'::regclass
      AND r.ev_class <> d.refobjid
  )
  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT format('%I.%I', n.nspname, c.relname) AS name
    FROM dependent_views v
    JOIN pg_class c ON c.oid = v.oid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE has_table_privilege(target_role, c.oid, 'SELECT') OR has_any_column_privilege(target_role, c.oid, 'SELECT')
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: these views show the content of an excluded table and would stay readable by %: %. Add their names to --exclude and run this step again', target_role, found;
  END IF;

  SELECT string_agg(name, ', ') INTO found
  FROM (
    SELECT format('%I.%I', n.nspname, c.relname) AS name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = ANY (schemas) AND c.relrowsecurity AND has_table_privilege(target_role, c.oid, 'SELECT')
    ORDER BY 1
    LIMIT 20
  ) AS listed;

  IF found IS NOT NULL THEN
    RAISE WARNING 'railway-pilot: these tables use row level security, so % reads no row from them until a developer adds a policy for it: %', target_role, found;
  END IF;

  SELECT string_agg(DISTINCT pg_get_userbyid(a.defaclrole)::text, ', ') INTO found
  FROM pg_default_acl a
  JOIN pg_namespace n ON n.oid = a.defaclnamespace
  WHERE n.nspname = ANY (schemas);

  RAISE WARNING 'railway-pilot: a table created later is readable only when it is created by one of these database users: %. For a table created by anyone else, run this step again', found;
END
$rp$;

COMMIT;
SQL
  sql_completion
}

revoke_sql() {
  printf '%s\n' '\set ON_ERROR_STOP on'
  sql_setting role "$role"
  cat <<'SQL'
DO $rp$
DECLARE
  target_role constant text := current_setting('rp.role');
  marker constant text := 'railway-pilot read-only role';
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = target_role) THEN
    RETURN;
  END IF;

  IF shobj_description((SELECT oid FROM pg_roles WHERE rolname = target_role), 'pg_authid') IS DISTINCT FROM marker THEN
    RAISE EXCEPTION 'railway-pilot: the database role % was not created by railway-pilot, so it is left untouched. A developer must remove it', target_role;
  END IF;

  EXECUTE format('ALTER ROLE %I NOLOGIN', target_role);
END
$rp$;

DO $rp$
DECLARE
  target_role constant text := current_setting('rp.role');
BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = target_role) THEN
    EXECUTE format('DROP OWNED BY %I', target_role);
  END IF;
END
$rp$;

DO $rp$
DECLARE
  target_role constant text := current_setting('rp.role');
  other_databases text;
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = target_role) THEN
    RETURN;
  END IF;

  SELECT string_agg(DISTINCT d.datname::text, ', ') INTO other_databases
  FROM pg_shdepend s
  JOIN pg_database d ON d.oid = s.dbid
  JOIN pg_roles r ON r.oid = s.refobjid
  WHERE s.refclassid = 'pg_authid'::regclass AND r.rolname = target_role AND d.datname <> current_database();

  IF other_databases IS NOT NULL THEN
    RAISE EXCEPTION 'railway-pilot: the role % can no longer log in and has lost its rights in database %, but it still holds rights in these databases: %. Run revoke again with --database for each of them to finish', target_role, current_database(), other_databases;
  END IF;

  EXECUTE format('DROP ROLE %I', target_role);
END
$rp$;
SQL
  sql_completion
}

apply_sql() {
  sql_status=0
  sql_output=$(printf '%s\n' "$1" | run_sql 2>&1) || sql_status=$?
  sql_errors=$(printf '%s\n' "$sql_output" | grep -E '(ERROR|FATAL|PANIC|psql: error):' | grep -v 'SCRAM-SHA-256') || sql_errors=

  if [ "$sql_status" -eq 0 ] && [ -z "$sql_errors" ]; then
    case $sql_output in
      *"$completion_mark"*) return 0 ;;
    esac
  fi

  if [ -z "$sql_errors" ]; then
    fail "The database did not confirm the change, so it must be considered as not done. Check the Railway login and the Postgres service name, then try again."
  fi

  printf '%s\n' "$2" >&2
  printf '%s\n' "$sql_errors" | while IFS= read -r line; do
    case $line in
      *'railway-pilot: '*) printf '%s.\n' "${line#*railway-pilot: }" ;;
      *) printf '%s\n' "$line" ;;
    esac
  done >&2
  exit 1
}

print_warnings() {
  printf '%s\n' "$sql_output" | while IFS= read -r line; do
    case $line in
      *'WARNING:  railway-pilot: '*) printf 'warning: %s.\n' "${line#*railway-pilot: }" ;;
    esac
  done
}

if [ $# -lt 2 ]; then
  fail_usage "$usage"
fi

mode=$1
tool=$2
shift 2

while [ $# -gt 0 ]; do
  case $1 in
    --schema | --exclude | --service | --database)
      if [ $# -lt 2 ]; then
        fail_usage "The option $1 needs a value."
      fi
      ;;
    *)
      fail_usage "Unknown option '$1'.
$usage"
      ;;
  esac

  case $1 in
    --schema) schemas=$2 ;;
    --exclude)
      exclude=$2
      exclude_given=1
      ;;
    --service) service=$2 ;;
    --database) database=$2 ;;
  esac
  shift 2
done

case $mode in
  create | revoke) ;;
  *) fail_usage "$usage" ;;
esac

name_rule='A name holds only letters, digits and underscores, does not start with a digit, and is 63 characters long at most. Several names are separated by commas, without spaces.'

if ! valid_tool "$tool"; then
  fail_usage "The tool name is not accepted. It starts with a lowercase letter and holds only lowercase letters, digits and underscores, 31 characters at most."
fi

if ! valid_name_list "$schemas"; then
  fail_usage "The schema list is not accepted. $name_rule"
fi

if names_a_system_schema "$schemas"; then
  fail_usage "The schema list names a system schema of Postgres. Give only the schemas that hold the business tables."
fi

if ! valid_name "$database"; then
  fail_usage "The database name is not accepted. $name_rule"
fi

if [ "$exclude_given" = 1 ] && ! valid_name_list "$exclude"; then
  fail_usage "The list of excluded tables is not accepted. $name_rule"
fi

role=${tool}_read

endpoint_overridden=0
if [ -n "${RP_PUBLIC_HOST:-}" ] && [ -n "${RP_PUBLIC_PORT:-}" ]; then
  endpoint_overridden=1
fi

railway_needed=0
if [ -z "${RP_PSQL:-}" ]; then
  railway_needed=1
fi
if [ "$mode" = create ] && [ "$endpoint_overridden" = 0 ]; then
  railway_needed=1
fi

if [ "$railway_needed" = 1 ]; then
  if [ -z "$service" ]; then
    fail_usage "The Postgres service name is missing. Add --service with the name of the Postgres service of the SaaS project."
  fi

  if ! valid_service "$service"; then
    fail_usage "The Postgres service name holds unexpected characters. Copy it as Railway shows it."
  fi

  if [ ! -d "$saas_dir" ]; then
    fail "The folder linked to the SaaS project is missing ($saas_dir). Onboarding has to link the SaaS project first."
  fi
fi

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 is missing. Install the Apple Command Line Tools first, then run this step again."
fi

nonce=$(random_hex 16) || fail "openssl could not produce random values, so nothing was changed. Ask a developer to check openssl on this Mac."
completion_mark=$(python3 "$script_dir/postgres_secrets.py" completion-mark "$nonce") || fail "The check value could not be prepared. Nothing was changed."

if [ "$mode" = revoke ]; then
  apply_sql "$(revoke_sql)" "The read-only access for $tool could not be fully removed:"
  printf 'Read-only access for %s is removed: the database role %s no longer exists.\n' "$tool" "$role"
  exit 0
fi

endpoint=$(read_public_endpoint) || fail "The public address of the database could not be read. Check the Postgres service name and that public networking (TCP proxy) is switched on for it in Railway, then try again."
host=${endpoint% *}
port=${endpoint#* }

if ! valid_host "$host" || ! valid_port "$port"; then
  fail "The public address of the database is not readable. Check that public networking (TCP proxy) is switched on for the Postgres service in Railway, then try again."
fi

password=$(random_hex 24) || fail "openssl could not produce a password, so nothing was changed. Ask a developer to check openssl on this Mac."
verifier=$(printf '%s' "$password" | python3 "$script_dir/postgres_secrets.py" scram-verifier) || fail "The password could not be prepared. Nothing was changed."

apply_sql "$(create_sql)" "The database refused to set up the read-only access for $tool. Nothing was changed."

if ! printf '%s' "$password" | sh -c "$clipboard" >/dev/null 2>&1; then
  fail "The read-only access for $tool is ready but the password could not be copied to the clipboard. Run the same command again to get a fresh one."
fi

printf 'Read-only access for %s is ready. The password is on the clipboard: paste it in the password field of the tool.\n' "$tool"
printf 'host: %s\n' "$host"
printf 'port: %s\n' "$port"
printf 'database: %s\n' "$database"
printf 'user: %s\n' "$role"
print_warnings
