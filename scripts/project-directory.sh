#!/bin/sh
set -eu

state_home=${COCKPIT_HOME:-${HOME:-}/.cockpit}
default_slug=app
usage='Usage: project-directory.sh [--project <slug>] | --list'
several_apps_status=4

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-1}"
}

is_slug() {
  case $1 in
    '' | *[!a-z0-9-]*) return 1 ;;
    *) return 0 ;;
  esac
}

list_slugs() {
  for entry in "$state_home"/projects/*/; do
    slug=${entry%/}
    slug=${slug##*/}

    if is_slug "$slug" && [ -f "${entry}state.md" ]; then
      printf '%s\n' "$slug"
    fi
  done
}

is_legacy_layout() {
  [ ! -f "$state_home/cockpit.md" ] && [ -e "$state_home/state.md" ]
}

project=
list_only=0

while [ "$#" -gt 0 ]; do
  case $1 in
    --list)
      list_only=1
      shift
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

if is_legacy_layout; then
  if [ "$list_only" = 0 ]; then
    printf '%s\n' "$state_home"
  fi
  exit 0
fi

if [ "$list_only" = 1 ]; then
  list_slugs
  exit 0
fi

count=0
only=
names=

while IFS= read -r slug; do
  if [ -z "$slug" ]; then
    continue
  fi

  count=$((count + 1))
  only=$slug
  names=${names:+$names, }$slug
done <<EOF
$(list_slugs)
EOF

if [ -n "$project" ]; then
  if ! is_slug "$project"; then
    fail "'$project' is not an app name: an app name has only lowercase letters, digits and dashes."
  fi

  if [ ! -f "$state_home/projects/$project/state.md" ]; then
    fail "There is no app named '$project' here. Apps: ${names:-none}."
  fi

  printf '%s\n' "$state_home/projects/$project"
  exit 0
fi

case $count in
  0) printf '%s\n' "$state_home/projects/$default_slug" ;;
  1) printf '%s\n' "$state_home/projects/$only" ;;
  *) fail "Several apps are saved here ($names). Say which one with --project <app>." "$several_apps_status" ;;
esac
