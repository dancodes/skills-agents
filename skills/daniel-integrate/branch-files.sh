#!/usr/bin/env bash

# Print every file each revision modifies, for the feature line and for each
# handoff/* bookmark, one section per revset. Each section shows the jj command
# first, then its output.

set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  branch-files.sh [root-revset]

Arguments:
  root-revset  Branch root, excluded from the listing (default: trunk()).

Examples:
  ./branch-files.sh
  ./branch-files.sh 'main'
USAGE
}

if [[ ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi

root=${1:-'trunk()'}

template='change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n" ++ diff.files().map(|f| "  " ++ f.path() ++ "\n").join("")'

# The root's own changeset is never listed: `root..head` excludes it.
section() {
  local heading=$1 revset=$2
  printf '\n## %s\n\n$ jj log -r %s --no-graph -T %s\n\n' \
    "$heading" "'$revset'" "'$template'"
  jj log -r "$revset" --no-graph -T "$template"
}

section 'Feature line' "$root..@"

bookmarks=$(jj bookmark list -r 'bookmarks(glob:"handoff/*")' -T 'name ++ "\n"')

if [[ -z $bookmarks ]]; then
  printf '\n## Handoffs\n\nNothing parked: no handoff/* bookmark exists.\n'
  exit 0
fi

while IFS= read -r bookmark; do
  section "$bookmark" "$root..$bookmark"
done <<<"$bookmarks"
