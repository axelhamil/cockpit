#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset GH_BIN GIT_BIN
fi

PATH=$PATH:${HOME:-}/.local/bin
gh_bin=${GH_BIN:-gh}
git_bin=${GIT_BIN:-git}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
project=

while [ "$#" -gt 0 ]; do
  case $1 in
    --project)
      if [ "$#" -lt 2 ]; then
        exit 0
      fi

      project=$2
      shift 2
      ;;
    *)
      exit 0
      ;;
  esac
done

project_directory=$(sh "$script_dir/project-directory.sh" --project "$project" 2>/dev/null) || exit 0
repo_dir=$project_directory/repo

if [ ! -d "$repo_dir" ]; then
  exit 0
fi

if [ "$(uname -s)" = Darwin ] && ! xcode-select -p >/dev/null 2>&1; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

python3 "$script_dir/commit_identity.py" "$repo_dir" "$git_bin" "$gh_bin" >/dev/null 2>&1 || :

exit 0
