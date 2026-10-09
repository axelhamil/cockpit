#!/bin/sh
set -eu

branch=${GITHUB_REF_NAME:-main}
note_push_attempts=5
note_push_delay=${NOTE_PUSH_DELAY:-5}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

tag=$(git tag --points-at HEAD --list 'v*' | head -n 1)

if [ -z "$tag" ]; then
  fail "No release tag on HEAD: semantic-release failed before tagging, read its log above."
fi

if ! git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null; then
  fail "$tag exists here but was never pushed: semantic-release failed before publishing, read its log above."
fi

git fetch --quiet origin "$branch"

if ! git merge-base --is-ancestor HEAD FETCH_HEAD; then
  fail "$tag was pushed but its commit never reached $branch: another commit landed first. Delete the tag on GitHub, then run the release again."
fi

if gh release view "$tag" >/dev/null 2>&1; then
  fail "GitHub release $tag already exists: semantic-release failed for another reason, read its log above."
fi

note_ref=refs/notes/semantic-release-$tag
attempt=1

if git show-ref --verify --quiet "$note_ref"; then
  until git push origin "$note_ref"; do
    if [ "$attempt" -ge "$note_push_attempts" ]; then
      printf '%s\n' "::warning::GitHub rejected $note_ref $note_push_attempts times. The release is published without it, semantic-release reads a missing note as the default channel."
      break
    fi

    attempt=$((attempt + 1))
    sleep "$note_push_delay"
  done
fi

notes=$(mktemp)
trap 'rm -f "$notes"' EXIT

awk '/^##? \[/ { section++ } section == 1' CHANGELOG.md >"$notes"

if [ ! -s "$notes" ]; then
  fail "CHANGELOG.md has no section to publish for $tag."
fi

gh release create "$tag" --verify-tag --title "$tag" --notes-file "$notes"
