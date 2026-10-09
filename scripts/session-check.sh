#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset COCKPIT_MIGRATION_WAIT
fi

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
header_line_limit=50
carriage_return=$(printf '\r')
newline='
'
newer_schema_status=3
several_apps_status=4
migration_wait_seconds=${COCKPIT_MIGRATION_WAIT:-20}
migration_grace_seconds=5
updated_state_line='state: updated to version 2'
newer_state_line='state: written by a newer cockpit, left untouched'
failed_migration_prefix='migration: failed ('
reason_characters='A-Za-z0-9 ._()/-'
reason_length_limit=100

trim() {
  trimmed=$1
  trimmed=${trimmed#"${trimmed%%[! ]*}"}
  trimmed=${trimmed%"${trimmed##*[! ]}"}
  printf '%s' "$trimmed"
}

state_value() {
  in_header=0
  lines_read=0

  if [ ! -f "$2" ] || [ ! -r "$2" ]; then
    return 0
  fi

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
  done <"$2"
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

known_slug() {
  case $1 in
    '' | *[!a-z0-9-]*) printf 'unknown' ;;
    *) printf '%s' "$1" ;;
  esac
}

known_reason() {
  case $1 in
    '' | *[!$reason_characters]*) printf 'reason not readable' ;;
    *) printf "%.${reason_length_limit}s" "$1" ;;
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

stop_after() {
  elapsed=0

  while [ "$elapsed" -lt "$2" ]; do
    sleep 1
    elapsed=$((elapsed + 1))
  done

  kill "$1" 2>/dev/null || return 0

  elapsed=0

  while [ "$elapsed" -lt "$migration_grace_seconds" ]; do
    sleep 1
    elapsed=$((elapsed + 1))
  done

  kill -9 "$1" 2>/dev/null || :
}

migrate_within_the_wait() {
  sh "$scripts_dir/migrate-state.sh" 2>/dev/null &
  migration_pid=$!

  (stop_after "$migration_pid" "$migration_wait_seconds") >/dev/null 2>&1 &
  watchdog=$!

  migration_exit=0
  wait "$migration_pid" || migration_exit=$?
  kill "$watchdog" 2>/dev/null || :

  return "$migration_exit"
}

run_migration() {
  migration_status=0
  migration_output=

  if [ -z "${scripts_dir:-}" ]; then
    return 0
  fi

  migration_output=$(migrate_within_the_wait) || migration_status=$?
  migration_line=${migration_output%%"$newline"*}
  migration_line=${migration_line%"$carriage_return"}

  if [ "$migration_status" = "$newer_schema_status" ] || [ "$migration_line" = "$newer_state_line" ]; then
    migration_status=$newer_schema_status
    printf '%s\n' "$newer_state_line"
    return 0
  fi

  case $migration_line in
    "$updated_state_line")
      printf '%s\n' "$updated_state_line"
      ;;
    "$failed_migration_prefix"*')')
      reason=${migration_line#"$failed_migration_prefix"}
      printf '%s%s)\n' "$failed_migration_prefix" "$(known_reason "${reason%')'}")"
      ;;
    *)
      if [ "$migration_status" != 0 ]; then
        printf '%sstopped before the end, status %s)\n' "$failed_migration_prefix" "$migration_status"
      fi
      ;;
  esac
}

find_project() {
  project_status=0
  project_directory=
  project_slug=

  if [ -z "${scripts_dir:-}" ]; then
    project_status=1
    return 0
  fi

  project_directory=$(sh "$scripts_dir/project-directory.sh" 2>/dev/null) || project_status=$?

  if [ "$project_status" != 0 ]; then
    return 0
  fi

  case $project_directory in
    "$state_home") project_slug=legacy ;;
    "$state_home"/projects/*) project_slug=$(known_slug "${project_directory#"$state_home"/projects/}") ;;
    *) project_slug=unknown ;;
  esac

  if [ "$project_slug" = unknown ]; then
    project_status=1
  fi
}

announce_project() {
  find_project

  if [ "$project_status" = 0 ]; then
    project_file=$project_directory/state.md
    printf 'active project: %s\n' "$project_slug"
    printf 'project directory: %s\n' "$project_directory"

    if [ -e "$project_directory/.relink" ]; then
      printf 'railway links: to refresh\n'
    fi
    return 0
  fi

  project_file=$user_file
  printf 'active project: none\n'

  if [ "$user_file" != "$state_home/cockpit.md" ]; then
    return 0
  fi

  project_file=

  if [ "$project_status" = "$several_apps_status" ]; then
    printf 'note: several apps are saved here, this version of cockpit works on one app at a time\n'
  else
    printf 'note: the app folder could not be found, its saved setup was not read\n'
  fi
}

print_health() {
  health_project=$project_slug

  if [ "$project_slug" = legacy ]; then
    health_project=
  fi

  sh "$scripts_dir/health-check.sh" --project "$health_project" 2>/dev/null || :
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

  run_migration

  if [ "$migration_status" = "$newer_schema_status" ]; then
    return 0
  fi

  user_file=$state_home/state.md

  if [ -f "$state_home/cockpit.md" ]; then
    user_file=$state_home/cockpit.md
  fi

  announce_project

  if [ ! -e "$user_file" ]; then
    printf 'onboarding: absent (no state file yet, onboarding has to run first)\n'
    return 0
  fi

  if [ ! -r "$user_file" ] || [ ! -f "$user_file" ]; then
    printf 'note: the state file cannot be read, onboarding status is unknown\n'
    return 0
  fi

  printf 'state schema version: %s\n' "$(known_schema_version "$(state_value schema_version "$user_file")")"
  printf 'language: %s\n' "$(known_language "$(state_value language "$user_file")")"

  if [ -z "$project_file" ]; then
    print_dependencies "$(state_value dependencies "$user_file")"
    return 0
  fi

  onboarding=$(state_value onboarding "$project_file")
  onboarding_step=$(state_value onboarding_step "$project_file")

  if [ "$project_file" != "$user_file" ] && [ ! -e "$project_file" ]; then
    onboarding=in-progress
    onboarding_step=profile
  fi

  case $onboarding in
    complete)
      printf 'onboarding: complete\n'
      ;;
    in-progress)
      printf 'onboarding: in progress, step reached: %s\n' "$(known_step "$onboarding_step")"
      ;;
    *)
      printf 'onboarding: unknown\n'
      printf 'note: the state file has no readable onboarding status, rerun onboarding to repair it\n'
      ;;
  esac

  print_dependencies "$(state_value dependencies "$user_file")"

  if [ "$onboarding" = complete ] && [ -n "${scripts_dir:-}" ]; then
    print_health
  fi

  recorded_version=$(known_version "$(state_value plugin_version "$user_file")")

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
