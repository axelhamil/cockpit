#!/bin/sh
set -eu

if [ "${RP_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN RP_PSQL RP_CLIPBOARD RP_PUBLIC_HOST RP_PUBLIC_PORT RP_PASTE RP_CLEAR_CLIPBOARD GH_BIN RP_BIN_DIR RP_SHELL_PROFILE CLAUDE_SETTINGS
fi

unset RAILWAY_TOKEN RAILWAY_API_TOKEN RAILWAY_PROJECT_ID RAILWAY_ENVIRONMENT_ID RAILWAY_SERVICE_ID

state_home=${RAILWAY_PILOT_HOME:-$HOME/.railway-pilot}
tools_dir=$state_home/tools-project
guard_conf=$state_home/guard.conf
railway_bin=${RAILWAY_BIN:-railway}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
allowed_commands='init, link, status, deploy, add, domain, variable set <KEY> --stdin, redeploy, restart, logs, service list|status|logs|redeploy|restart'

refuse() {
  printf '%s\n' "$2" >&2
  exit "$1"
}

lowercase() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

saas_project_id() {
  while IFS='=' read -r key value || [ -n "$key" ]; do
    if [ "$key" = SAAS_PROJECT_ID ]; then
      lowercase "$value"
    fi
  done <"$guard_conf"
}

linked_project_id() {
  "$railway_bin" status --json </dev/null 2>/dev/null | python3 "$script_dir/railway_json.py" project-id 2>/dev/null
}

require_bounded_logs() {
  for argument in "$@"; do
    case $argument in
      --since | --since=* | -S | --until | --until=* | -U | --lines | --lines=* | -n | --tail | --tail=*) return 0 ;;
    esac
  done

  refuse 2 "Logs must be bounded so the command ends: add --lines <number> or --since <duration>, for example --lines 100."
}

require_stdin_variable() {
  case ${3:-} in
    '' | [!A-Za-z_]* | *[!A-Za-z0-9_]*)
      refuse 2 "Give the variable name alone right after 'variable set', and send its value on standard input with --stdin. A value is never written in the command."
      ;;
  esac

  shift 3
  stdin_requested=0

  while [ $# -gt 0 ]; do
    case $1 in
      --stdin) stdin_requested=1 ;;
      --skip-deploys | --json) ;;
      -s | --service | -e | --environment)
        if [ $# -lt 2 ]; then
          refuse 2 "The option $1 needs a value."
        fi
        shift
        ;;
      *)
        refuse 2 "This form of 'variable set' is not accepted. Use: variable set <KEY> --stdin [-s <service>] [-e <environment>] [--skip-deploys] [--json]."
        ;;
    esac
    shift
  done

  if [ "$stdin_requested" = 0 ]; then
    refuse 2 "Add --stdin and send the value on standard input. A value is never written in the command."
  fi
}

if [ $# -eq 0 ]; then
  refuse 2 "No Railway command was given. Allowed commands: $allowed_commands."
fi

case $1 in
  init | link | status | deploy | add | redeploy | restart)
    subcommand=$1
    ;;
  logs)
    subcommand=$1
    require_bounded_logs "$@"
    ;;
  domain)
    subcommand=$1
    for argument in "$@"; do
      case $argument in
        delete | remove | rm | update | edit | certificate)
          refuse 2 "Domains are only created or listed from here. Removing or changing a domain is done by a developer."
          ;;
      esac
    done
    ;;
  service)
    subcommand=$1
    case ${2:-} in
      list | status | redeploy | restart) ;;
      logs) require_bounded_logs "$@" ;;
      *)
        refuse 2 "After 'service', only list, status, logs, redeploy and restart are allowed. Services are never deleted or rewired from here."
        ;;
    esac
    ;;
  variable)
    if [ "${2:-}" != set ]; then
      refuse 2 "Only 'variable set' is allowed here. Variables are never listed or deleted through this script."
    fi
    subcommand='variable set'
    require_stdin_variable "$@"
    ;;
  *)
    refuse 2 "The Railway command '$1' is not allowed on the tools project. Allowed commands: $allowed_commands."
    ;;
esac

mkdir -p "$tools_dir"
cd "$tools_dir"

if [ "$subcommand" = init ] || [ "$subcommand" = status ]; then
  exec "$railway_bin" "$@"
fi

if [ ! -f "$guard_conf" ]; then
  refuse 3 "The safety settings are not written yet (guard.conf is missing), so nothing can be changed on Railway. Finish onboarding first."
fi

saas_id=$(saas_project_id)

if [ -z "$saas_id" ]; then
  refuse 3 "The safety settings do not name the SaaS project (guard.conf has no SAAS_PROJECT_ID), so nothing can be changed on Railway. Rerun onboarding to repair them."
fi

for argument in "$@"; do
  case $(lowercase "$argument") in
    *"$saas_id"*)
      refuse 3 "This command names the SaaS project. Changes to the SaaS project are never made from here, a developer has to make them."
      ;;
  esac
done

for argument in "$@"; do
  case $argument in
    --project | --project=*)
      if [ "$subcommand" != link ]; then
        refuse 2 "Remove the project option: this script always works on the linked tools project."
      fi
      ;;
    --*) ;;
    -p)
      if [ "$subcommand" != link ] && [ "$subcommand" != domain ]; then
        refuse 2 "Remove the project option: this script always works on the linked tools project."
      fi
      ;;
    -[!-]*[pe]* | -[pe]?*)
      refuse 2 "Write each option separately, with its value as the next word (for example -s metabase -y). Grouped short options are not accepted here."
      ;;
  esac
done

if [ "$subcommand" = link ]; then
  "$railway_bin" "$@" || exit $?

  linked_id=$(linked_project_id) || linked_id=

  if [ -n "$linked_id" ] && [ "$linked_id" != "$saas_id" ]; then
    exit 0
  fi

  if ! "$railway_bin" unlink --yes </dev/null >/dev/null 2>&1; then
    refuse 3 "The tools folder was linked to a project that is not a safe tools project and the link could not be removed. No change will be accepted until a tools project is linked instead."
  fi

  if [ -z "$linked_id" ]; then
    refuse 3 "The linked project could not be identified, so the link was removed. Check the Railway login, then link the tools project again."
  fi

  refuse 3 "That project is the SaaS project, so the link was removed. Tools always live in their own Railway project: link the tools project instead."
fi

linked_id=$(linked_project_id) || linked_id=

if [ -z "$linked_id" ]; then
  refuse 3 "No tools project is linked yet, or Railway could not be reached. Check the Railway login, then create or link the tools project first."
fi

if [ "$linked_id" = "$saas_id" ]; then
  refuse 3 "The tools folder is linked to the SaaS project, so the command was not run. Link the tools project instead."
fi

exec "$railway_bin" "$@"
