#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN
fi

PATH=$PATH:${HOME:-}/.railway/bin:${HOME:-}/.local/bin
railway_bin=${RAILWAY_BIN:-railway}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='Usage: relink.sh [--project <slug>]'
tools_environment=production
project=

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

while [ "$#" -gt 0 ]; do
  case $1 in
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

project_directory=$(sh "$script_dir/project-directory.sh" --project "$project") || exit 1
state_file=$project_directory/state.md
marker=$project_directory/.relink

if [ ! -e "$marker" ]; then
  printf '%s\n' "The Railway links are already up to date."
  exit 0
fi

if [ ! -f "$state_file" ]; then
  fail "The saved setup of this app cannot be read ($state_file), so its Railway links cannot be rebuilt."
fi

section_line() {
  sed -n "/^## $1\$/,/^## /{/^$2/p;}" "$state_file" | sed -n '1p' | tr -d '\r'
}

is_identifier() {
  case $1 in
    '' | -* | *[!0-9A-Za-z._-]*) return 1 ;;
    *) return 0 ;;
  esac
}

is_name() {
  case $1 in
    '' | -*) return 1 ;;
    *) return 0 ;;
  esac
}

project_id_of() {
  line=$(section_line "$1" '- Project:')
  id=${line##*\(}
  id=${id%\)*}

  if ! is_identifier "$id"; then
    return 1
  fi

  printf '%s' "$id"
}

value_of() {
  line=$(section_line "$1" "$2")
  value=${line#"$2"}
  value=${value#"${value%%[! ]*}"}
  value=${value%%,*}
  value=${value%"${value##*[! ]}"}

  if ! is_name "$value"; then
    return 1
  fi

  printf '%s' "$value"
}

link_folder() {
  if ! (cd "$project_directory/$1" && shift && "$railway_bin" link "$@" </dev/null >/dev/null 2>&1); then
    fail "Railway did not link the folder '$1'. Check that 'railway whoami' answers and that this account is a member of the project, then run this again."
  fi
}

has_saas=false
has_tools=false

if [ -d "$project_directory/saas-project" ]; then
  has_saas=true
  saas_id=$(project_id_of 'SaaS project') || fail "The SaaS project of $state_file has no readable id, so its folder cannot be linked again."
  production=$(value_of 'SaaS project' '- Production environment:') || fail "The production environment of $state_file cannot be read, so the SaaS folder cannot be linked again."
  app_service=$(value_of 'SaaS project' '- App service:') || fail "The app service of $state_file cannot be read, so the SaaS folder cannot be linked again."
fi

if [ -d "$project_directory/tools-project" ]; then
  has_tools=true
  tools_id=$(project_id_of 'Tools project') || fail "The tools project of $state_file has no readable id, so its folder cannot be linked again."
fi

if [ "$has_saas" = true ]; then
  link_folder saas-project -p "$saas_id" -e "$production" -s "$app_service"
fi

if [ "$has_tools" = true ]; then
  link_folder tools-project -p "$tools_id" -e "$tools_environment"
fi

rm -f "$marker"
printf '%s\n' "The Railway links are rebuilt."
