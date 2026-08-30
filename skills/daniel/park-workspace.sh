#!/usr/bin/env bash

# Park an impl workspace's finished work on a handoff/<name> bookmark, which
# outlives the workspace going stale or being forgotten. /daniel-integrate reads it.
# The bookmark carries the work, so the script then forgets the workspace and
# deletes its directory.

set -Eeuo pipefail

if [[ $# -ne 2 || ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: park-workspace.sh <workspace-path> <one-line-message>\n' >&2
  exit 2
fi

source=$(jj workspace root 2>/dev/null || jj root)
workspace=$(cd -- "$1" && pwd)
name=$(basename -- "$workspace")
bookmark=handoff/$name

cd -- "$workspace"

# The only command here without --ignore-working-copy, so the only one that
# takes the working-copy lock. It snapshots the edits off disk and names the
# change they landed in; everything after it addresses that change by ID.
# A stale working copy cannot be snapshotted, so fall back to the last snapshot
# the repo already records for it. Never clear staleness with
# `jj workspace update-stale`: it rewrites the files on disk.
if ! change=$(jj log --no-graph -r @ -T 'change_id.shortest(12)'); then
  change=$(jj --ignore-working-copy log --no-graph -r @ -T 'change_id.shortest(12)')
  if [[ -z $(jj --ignore-working-copy diff --summary -r "$change") ]]; then
    printf 'Stale working copy, and its last snapshot (%s) is empty.\n' "$change" >&2
    exit 1
  fi
  printf 'Working copy is stale, so parking its last snapshot (%s).\n' "$change" >&2
  printf 'Any edit made after that snapshot is NOT in the files listed below.\n' >&2
fi

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

printf '\nThis workspace is parked. Run no further command in it.\n'

# The bookmark holds the work now, so the workspace is disposable. Forget it
# from the source workspace, never from inside the one being removed.
cd -- "$source"
if jj --ignore-working-copy workspace forget "$name"; then
  rm -rf -- "$workspace"
  printf '\nWorkspace forgotten and %s deleted.\n' "$workspace"
else
  printf '\nParked, but could not forget the workspace. Delete %s by hand.\n' "$workspace" >&2
fi
