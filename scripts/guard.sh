#!/bin/sh
set -eu

newline='
'

block() {
  echo "railway-pilot guard: $1" >&2
  exit 2
}

command_line_tools_are_missing() {
  if [ -n "${RAILWAY_PILOT_GUARD_FORCE_NO_PYTHON:-}" ]; then
    return 0
  fi

  if [ "$(uname -s)" != Darwin ]; then
    return 1
  fi

  ! xcode-select -p >/dev/null 2>&1
}

is_single_bash_call() {
  case $1 in
    *"$newline"*) return 1 ;;
    *'"tool_name":'*'"tool_name":'*) return 1 ;;
    *'"tool_input":'*'"tool_input":'*) return 1 ;;
    *'"command":'*'"command":'*) return 1 ;;
    *'"tool_name":"Bash"'*) return 0 ;;
  esac

  return 1
}

repairs_command_line_tools() {
  is_single_bash_call "$1" || return 1

  for repair in 'xcode-select --install' 'xcode-select -p' 'git --version'; do
    case $1 in
      *"\"tool_input\":{\"command\":\"$repair\"}"*) return 0 ;;
      *"\"tool_input\":{\"command\":\"$repair\","*) return 0 ;;
    esac
  done

  return 1
}

if command_line_tools_are_missing; then
  hook_input=$(cat)

  if repairs_command_line_tools "$hook_input"; then
    exit 0
  fi

  block "Apple Command Line Tools are missing. Run xcode-select --install, wait for the installation to finish, then retry."
fi

scripts_directory=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || block "the guard cannot locate its own directory, so the call is blocked"

if [ -x /usr/bin/python3 ]; then
  python=/usr/bin/python3
elif command -v python3 >/dev/null 2>&1; then
  python=python3
else
  block "python3 is missing, so every guarded call is blocked. Install the Apple Command Line Tools with xcode-select --install"
fi

status=0
"$python" -I -B "$scripts_directory/guard.py" || status=$?

if [ "$status" -eq 0 ]; then
  exit 0
fi

if [ "$status" -ne 2 ]; then
  block "the guard stopped unexpectedly with status $status, so the call is blocked"
fi

exit 2
