#!/bin/sh
set -eu

tests_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

exec python3 -m unittest discover -s "$tests_dir" -p 'test_*.py' "$@"
