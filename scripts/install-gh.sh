#!/bin/sh
set -eu

if [ "${COCKPIT_TEST:-}" != 1 ]; then
  unset RAILWAY_BIN COCKPIT_CLIPBOARD COCKPIT_OPEN COCKPIT_OPEN_DELAY GH_BIN COCKPIT_BIN_DIR COCKPIT_SHELL_PROFILE CLAUDE_SETTINGS
fi

install_dir=${COCKPIT_BIN_DIR:-$HOME/.local/bin}
profile=${COCKPIT_SHELL_PROFILE:-$HOME/.zshrc}
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
release_api=https://api.github.com/repos/cli/cli/releases/latest

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

if [ "$(uname -s)" != Darwin ]; then
  fail "This installer only works on macOS, so nothing was downloaded or changed on this computer."
fi

case $(uname -m) in
  arm64 | aarch64) architecture=arm64 ;;
  x86_64) architecture=amd64 ;;
  *) fail "This Mac has an unsupported processor ($(uname -m)), so GitHub CLI was not installed. A developer has to install it by hand." ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 is missing. Install the Apple Command Line Tools first, then run this step again."
fi

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

if ! curl -fsSL "$release_api" >"$work_dir/release.json" 2>/dev/null; then
  fail "GitHub did not answer the download request (no network, or too many requests from this address). Nothing was installed. Wait a few minutes, then retry."
fi

if ! asset_url=$(python3 "$script_dir/gh_release.py" asset-url "$architecture" <"$work_dir/release.json"); then
  fail "GitHub answered, but the list of downloads does not hold a GitHub CLI for this Mac. Nothing was installed. Retry later, and tell the plugin maintainer if it fails again."
fi

if ! curl -fsSL -o "$work_dir/gh.zip" "$asset_url" 2>/dev/null; then
  fail "The GitHub CLI download failed. Nothing was installed. Check the internet connection, then retry."
fi

if ! python3 "$script_dir/gh_release.py" extract-binary "$work_dir/gh.zip" "$work_dir/gh"; then
  fail "The downloaded GitHub CLI archive does not have the expected content. Nothing was installed. Tell the plugin maintainer."
fi

mkdir -p "$install_dir"
cp "$work_dir/gh" "$install_dir/gh"
chmod 755 "$install_dir/gh"

path_line="export PATH=\"$install_dir:\$PATH\""

if ! grep -qsF "$path_line" "$profile"; then
  printf '\n%s\n' "$path_line" >>"$profile"
fi

"$install_dir/gh" --version
