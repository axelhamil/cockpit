#!/bin/sh
set -eu

LC_ALL=C
export LC_ALL

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN COCKPIT_CLIPBOARD COCKPIT_OPEN COCKPIT_OPEN_DELAY GH_BIN COCKPIT_BIN_DIR COCKPIT_SHELL_PROFILE CLAUDE_SETTINGS COCKPIT_PLUGIN_MANIFEST
fi

settings_file=${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
plugin_manifest=${COCKPIT_PLUGIN_MANIFEST:-$script_dir/../.claude-plugin/plugin.json}
usage='Usage: apply-settings.sh --marketplace <name> | apply-settings.sh --remove --marketplace <name>'

marketplace=
mode=apply

fail_usage() {
  printf '%s\n' "$1" >&2
  exit 2
}

valid_marketplace() {
  case $1 in
    '' | [!A-Za-z0-9]* | *[!A-Za-z0-9._-]*) return 1 ;;
  esac
}

while [ $# -gt 0 ]; do
  if [ "$1" = --remove ]; then
    mode=remove
    shift
    continue
  fi

  case $1 in
    --marketplace)
      if [ $# -lt 2 ]; then
        fail_usage "The option $1 needs a value."
      fi
      ;;
    --repo)
      fail_usage "The option --repo is gone: the plugin repository is read from the plugin itself. $usage"
      ;;
    *)
      fail_usage "Unknown option '$1'. $usage"
      ;;
  esac

  marketplace=$2
  shift 2
done

if ! valid_marketplace "$marketplace"; then
  fail_usage "The marketplace name is missing or holds unexpected characters. Use the name written in the plugin marketplace file. $usage"
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' "python3 is missing, so the settings cannot be written. Install the Apple Command Line Tools first, then run this step again." >&2
  exit 1
fi

exec python3 "$script_dir/apply_settings.py" "$mode" "$settings_file" "$script_dir/permissions.json" "$marketplace" "$plugin_manifest"
