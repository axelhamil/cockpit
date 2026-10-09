#!/bin/sh
set -eu

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
state_file=$state_home/state.md
header_line_limit=50
carriage_return=$(printf '\r')

trim() {
  trimmed=$1
  trimmed=${trimmed#"${trimmed%%[! ]*}"}
  trimmed=${trimmed%"${trimmed##*[! ]}"}
  printf '%s' "$trimmed"
}

state_value() {
  in_header=0
  lines_read=0

  while IFS= read -r line || [ -n "$line" ]; do
    lines_read=$((lines_read + 1))

    if [ "$lines_read" -gt "$header_line_limit" ]; then
      break
    fi

    line=${line%"$carriage_return"}

    if [ "$line" = '---' ]; then
      if [ "$in_header" = 1 ]; then
        break
      fi
      in_header=1
      continue
    fi

    if [ "$in_header" = 0 ]; then
      break
    fi

    case $line in
      "$1":*)
        trim "${line#"$1":}"
        break
        ;;
    esac
  done <"$state_file"
}

known_schema_version() {
  case $1 in
    '' | *[!0-9]* | ??????*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

known_language() {
  case $1 in
    [a-z][a-z] | [a-z][a-z]-[A-Za-z][A-Za-z]) printf '%s' "$1" ;;
    *) printf 'unknown' ;;
  esac
}

known_step() {
  case $1 in
    profile | plan | dependencies | railway | backups | settings | github | tools | discovery | check) printf '%s' "$1" ;;
    *) printf 'unknown' ;;
  esac
}

known_version() {
  case $1 in
    '' | *[!A-Za-z0-9.+-]* | ????????????????????????????????*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

scripts_directory() {
  CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P
}

plugin_version() {
  manifest=$1/../.claude-plugin/plugin.json

  if [ -f "$manifest" ]; then
    sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" | sed -n '1p'
  fi
}

dependency_status() {
  if [ "$1" = git ] && [ "$(uname -s)" = Darwin ]; then
    if xcode-select -p >/dev/null 2>&1; then
      printf 'present'
    else
      printf 'missing'
    fi
    return 0
  fi

  if PATH="$PATH:${HOME:-}/.railway/bin:${HOME:-}/.local/bin" command -v "$1" >/dev/null 2>&1; then
    printf 'present'
  else
    printf 'missing'
  fi
}

print_dependencies() {
  set -f
  old_ifs=$IFS
  IFS=,
  for entry in $1; do
    IFS=$old_ifs
    name=$(trim "$entry")

    case $name in
      '') ;;
      git | railway | gh | node) printf 'dependency %s: %s\n' "$name" "$(dependency_status "$name")" ;;
      *) printf 'dependency unknown: ignored\n' ;;
    esac
  done
  IFS=$old_ifs
  set +f
}

print_context() {
  printf 'cockpit session context\n'

  current_version=unknown

  if scripts_dir=$(scripts_directory); then
    current_version=$(known_version "$(plugin_version "$scripts_dir")")
    printf 'plugin version: %s\n' "$current_version"
    printf 'scripts directory: %s\n' "$scripts_dir"
  else
    printf 'plugin version: unknown\n'
    printf 'note: the scripts directory of the plugin could not be located\n'
  fi

  printf 'state directory: %s\n' "$state_home"

  if [ ! -e "$state_file" ]; then
    printf 'onboarding: absent (no state file yet, onboarding has to run first)\n'
    return 0
  fi

  if [ ! -r "$state_file" ] || [ ! -f "$state_file" ]; then
    printf 'note: the state file cannot be read, onboarding status is unknown\n'
    return 0
  fi

  printf 'state schema version: %s\n' "$(known_schema_version "$(state_value schema_version)")"
  printf 'language: %s\n' "$(known_language "$(state_value language)")"

  onboarding=$(state_value onboarding)

  case $onboarding in
    complete)
      printf 'onboarding: complete\n'
      ;;
    in-progress)
      printf 'onboarding: in progress, step reached: %s\n' "$(known_step "$(state_value onboarding_step)")"
      ;;
    *)
      printf 'onboarding: unknown\n'
      printf 'note: the state file has no readable onboarding status, rerun onboarding to repair it\n'
      ;;
  esac

  print_dependencies "$(state_value dependencies)"

  if [ "$onboarding" = complete ] && [ -n "${scripts_dir:-}" ]; then
    sh "$scripts_dir/health-check.sh" 2>/dev/null || :
  fi

  recorded_version=$(known_version "$(state_value plugin_version)")

  if [ "$onboarding" != complete ] || [ "$current_version" = unknown ]; then
    return 0
  fi

  if [ "$recorded_version" = unknown ]; then
    printf 'plugin version: not recorded in the state file yet\n'
  elif [ "$recorded_version" != "$current_version" ]; then
    printf 'plugin version changed: from %s to %s since the last session, changelog: %s/CHANGELOG.md\n' "$recorded_version" "$current_version" "$(dirname -- "$scripts_dir")"
  fi
}

(print_context) || printf 'note: cockpit could not finish its session check, the state may need a repair\n'
printf 'Load the cockpit skill before answering the first request of this session.\n'

exit 0
