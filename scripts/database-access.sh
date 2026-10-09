#!/bin/sh
set -eu

if [ "${RP_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN RP_CLIPBOARD RP_OPEN RP_OPEN_DELAY GH_BIN RP_BIN_DIR RP_SHELL_PROFILE CLAUDE_SETTINGS
fi

railway_bin=${RAILWAY_BIN:-railway}
clipboard_command=${RP_CLIPBOARD:-pbcopy}
state_home=${RAILWAY_PILOT_HOME:-$HOME/.railway-pilot}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

usage='Usage: database-access.sh --service <postgres service> [--private]'
variable_name=DATABASE_PUBLIC_URL
service=

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
    *)
      fail "$usage" 2
      ;;
  esac
done

case $service in
  '' | -*) fail "$usage" 2 ;;
esac

saas_dir=$state_home/saas-project

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
