#!/bin/sh
set -eu

LC_ALL=C
export LC_ALL

if [ "${RP_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN RP_PSQL RP_CLIPBOARD RP_PUBLIC_HOST RP_PUBLIC_PORT RP_PASTE RP_CLEAR_CLIPBOARD GH_BIN RP_BIN_DIR RP_SHELL_PROFILE CLAUDE_SETTINGS
fi

state_home=${RAILWAY_PILOT_HOME:-$HOME/.railway-pilot}
guard_conf=$state_home/guard.conf
settings_file=${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

saas_project=
deployed_branch=
test_branch=
marketplace=
repo=

fail_usage() {
  printf '%s\n' "$1" >&2
  exit 2
}

valid_project_id() {
  case $1 in
    ????????-????-????-????-????????????) ;;
    *) return 1 ;;
  esac

  digits=$(printf '%s' "$1" | tr -d '-')

  case $digits in
    *[!0-9a-fA-F]*) return 1 ;;
  esac
  [ ${#digits} -eq 32 ]
}

valid_branch() {
  case $1 in
    '' | -* | *[!A-Za-z0-9._/-]*) return 1 ;;
  esac
}

valid_marketplace() {
  case $1 in
    '' | [!A-Za-z0-9]* | *[!A-Za-z0-9._-]*) return 1 ;;
  esac
}

valid_repo() {
  case $1 in
    */*/* | *[!A-Za-z0-9._/-]*) return 1 ;;
    ?*/?*) return 0 ;;
  esac
  return 1
}

while [ $# -gt 0 ]; do
  case $1 in
    --saas-project | --deployed-branch | --test-branch | --marketplace | --repo)
      if [ $# -lt 2 ]; then
        fail_usage "The option $1 needs a value."
      fi
      ;;
    *)
      fail_usage "Unknown option '$1'. Usage: apply-settings.sh --saas-project <id> --deployed-branch <branch> [--test-branch <branch>] --marketplace <name> --repo <owner/repo>"
      ;;
  esac

  case $1 in
    --saas-project) saas_project=$2 ;;
    --deployed-branch) deployed_branch=$2 ;;
    --test-branch) test_branch=$2 ;;
    --marketplace) marketplace=$2 ;;
    --repo) repo=$2 ;;
  esac
  shift 2
done

if ! valid_project_id "$saas_project"; then
  fail_usage "The SaaS project id is missing or is not a Railway project id (five groups of digits and letters a to f, such as 1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d5e6f). Copy it again from 'railway status --json'."
fi

if ! valid_branch "$deployed_branch"; then
  fail_usage "The deployed branch is missing or holds unexpected characters. Give the branch Railway deploys, for example main."
fi

if [ -n "$test_branch" ] && ! valid_branch "$test_branch"; then
  fail_usage "The test branch holds unexpected characters. Give a plain branch name, for example staging."
fi

if ! valid_marketplace "$marketplace"; then
  fail_usage "The marketplace name is missing or holds unexpected characters. Use the name written in the plugin marketplace file."
fi

if ! valid_repo "$repo"; then
  fail_usage "The plugin repository is missing or is not written as owner/repo."
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' "python3 is missing, so the settings cannot be written. Install the Apple Command Line Tools first, then run this step again." >&2
  exit 1
fi

exec python3 "$script_dir/apply_settings.py" "$guard_conf" "$settings_file" "$script_dir/permissions.json" "$saas_project" "$deployed_branch" "$test_branch" "$marketplace" "$repo"
