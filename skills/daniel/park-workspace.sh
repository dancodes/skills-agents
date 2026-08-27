#!/usr/bin/env bash

# Park an impl workspace's finished work on a handoff/<name> bookmark, which
# outlives the workspace going stale or being forgotten. /daniel-integrate reads it.

set -Eeuo pipefail

if [[ $# -ne 2 || ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: park-workspace.sh <workspace-path> <one-line-message>\n' >&2
  exit 2
fi

workspace=$(cd -- "$1" && pwd)
name=$(basename -- "$workspace")
bookmark=handoff/$name

cd -- "$workspace"

# The only command here without --ignore-working-copy, so the only one that
# takes the working-copy lock. It snapshots the edits off disk and names the
# change they landed in; everything after it addresses that change by ID.
change=$(jj log --no-graph -r @ -T 'change_id.shortest(12)')

jj --ignore-working-copy describe -r "$change" -m "$2"
jj --ignore-working-copy bookmark create "$bookmark" -r "$change"

printf '\nParked at %s\n' "$bookmark"
jj --ignore-working-copy log --no-graph -r "$change" \
  -T 'change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n"'

printf '\nFiles:\n'
jj --ignore-working-copy diff --summary -r "$change"

scaffolding=$(jj --ignore-working-copy diff --summary -r "$change" \
  | grep -E 'node_modules/|src/modules/api/generated' || true)
if [[ -n $scaffolding ]]; then
  printf '\nScaffolding in the snapshot, must not reach a commit:\n%s\n' "$scaffolding"
fi

printf '\nThis workspace is parked. Run no further command in %s.\n' "$workspace"
