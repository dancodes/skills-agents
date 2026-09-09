#!/usr/bin/env bash

# Commit one approved round of an impl workspace's work, leaving the workspace
# and its agent alive: the next round becomes a follow-up commit. No bookmark;
# park-workspace.sh parks the whole stack at the final approval.

set -Eeuo pipefail

if [[ $# -ne 2 || ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: commit-workspace.sh <workspace-path> <one-line-message>\n' >&2
  exit 2
fi

workspace=$(cd -- "$1" && pwd)
name=$(basename -- "$workspace")

cd -- "$workspace"

# The only command without --ignore-working-copy, so the only one that
# snapshots the edits off disk. Everything after it addresses them by change ID.
if ! change=$(jj log --no-graph -r @ -T 'change_id.shortest(12)'); then
  printf 'Working copy is stale, so this round cannot be snapshotted.\n' >&2
  printf 'Park the workspace instead: it parks the last snapshot jj holds.\n' >&2
  exit 1
fi

if [[ -z $(jj --ignore-working-copy diff --summary -r "$change") ]]; then
  printf 'Nothing to commit: %s is empty.\n' "$change" >&2
  exit 1
fi

jj --ignore-working-copy describe -r "$change" -m "$2"

# Moves this workspace's working copy, and only this one, so every later edit
# snapshots into the new child instead of the committed round.
jj new "$change"

printf '\nCommitted %s in %s\n' "$change" "$name"
jj --ignore-working-copy log --no-graph -r "$change" \
  -T 'change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n"'

printf '\nFiles:\n'
jj --ignore-working-copy diff --summary -r "$change"

scaffolding=$(jj --ignore-working-copy diff --summary -r "$change" \
  | grep -E 'node_modules/|src/modules/api/generated' || true)
if [[ -n $scaffolding ]]; then
  printf '\nScaffolding in the commit, must not reach the feature line:\n%s\n' "$scaffolding"
fi

printf '\nThe workspace stays. Further edits land as a follow-up commit.\n'
