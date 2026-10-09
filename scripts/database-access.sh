#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN COCKPIT_CLIPBOARD COCKPIT_OPEN COCKPIT_OPEN_DELAY GH_BIN COCKPIT_BIN_DIR COCKPIT_SHELL_PROFILE CLAUDE_SETTINGS
fi

railway_bin=${RAILWAY_BIN:-railway}
clipboard_command=${COCKPIT_CLIPBOARD:-pbcopy}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

usage='Usage: database-access.sh --service <postgres service> [--private] [--project <slug>]'
variable_name=DATABASE_PUBLIC_URL
service=
project=

while [ "$#" -gt 0 ]; do
  case $1 in
    --private)
      variable_name=DATABASE_URL
      shift
      ;;
    --service)
      if [ "$#" -lt 2 ]; then
        fail "$usage" 2
      fi

      service=$2
      shift 2
      ;;
    --project)
      if [ "$#" -lt 2 ]; then
        fail "$usage" 2
      fi

      project=$2
      shift 2
      ;;
    *)
      fail "$usage" 2
      ;;
  esac
done

case $service in
  '' | -*) fail "$usage" 2 ;;
esac

project_directory=$(sh "$script_dir/project-directory.sh" --project "$project") || exit 1
saas_dir=$project_directory/saas-project

if [ ! -d "$saas_dir" ]; then
  fail "The folder linked to the app's Railway project is missing ($saas_dir). Run the Railway step of the onboarding first."
fi

if ! variables=$(cd "$saas_dir" && "$railway_bin" variable list -s "$service" --json 2>/dev/null); then
  fail "Railway did not return the settings of the service '$service'. Check the service name with 'railway status --json' and that 'railway whoami' answers."
fi

status=0
printf '%s' "$variables" | python3 "$script_dir/database_access.py" "$clipboard_command" "$variable_name" || status=$?

case $status in
  0)
    printf '%s\n' "The password is on the clipboard and nowhere else."
    ;;
  3)
    if [ "$variable_name" = DATABASE_URL ]; then
      fail "The service '$service' has no database address. Check that '$service' is the Postgres service ('railway status --json'), then retry."
    fi

    fail "The service '$service' has no public database address, so a tool in another project cannot reach it. Check that '$service' is the Postgres service ('railway status --json'), then create the address with 'railway tcp-proxy create --port 5432 -s $service' from $saas_dir, wait for the database to restart, then retry."
    ;;
  4)
    fail "Railway returned settings for '$service' that could not be read. Update the Railway CLI with the install command, then retry."
    ;;
  *)
    fail "The password could not be copied to the clipboard. Retry."
    ;;
esac
