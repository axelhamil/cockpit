#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN COCKPIT_HEALTH_WAIT
fi

PATH=$PATH:${HOME:-}/.railway/bin:${HOME:-}/.local/bin
railway_bin=${RAILWAY_BIN:-railway}
wait_seconds=${COCKPIT_HEALTH_WAIT:-6}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='Usage: health-check.sh [--project <slug>]'
project=

while [ "$#" -gt 0 ]; do
  case $1 in
    --project)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' "$usage" >&2
        exit 2
      fi

      project=$2
      shift 2
      ;;
    *)
      printf '%s\n' "$usage" >&2
      exit 2
      ;;
  esac
done

project_directory=$(sh "$script_dir/project-directory.sh" --project "$project" 2>/dev/null) || exit 0
saas_dir=$project_directory/saas-project

if [ ! -d "$saas_dir" ]; then
  exit 0
fi

if [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1 || ! command -v "$railway_bin" >/dev/null 2>&1; then
  exit 0
fi

answer=$(mktemp)
trap 'rm -f "$answer"' EXIT

(cd "$saas_dir" && exec "$railway_bin" status --json >"$answer" 2>/dev/null) &
status_pid=$!

(sleep "$wait_seconds" && kill "$status_pid" 2>/dev/null && sleep 1 && kill -9 "$status_pid" 2>/dev/null) >/dev/null 2>&1 &
watchdog=$!

if wait "$status_pid"; then
  python3 "$script_dir/deployment_health.py" <"$answer"
else
  printf '%s\n' "health: not checked, Railway did not answer (sign-in expired or no network)"
fi

kill "$watchdog" 2>/dev/null || :
