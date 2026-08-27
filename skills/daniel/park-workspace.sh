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

# jj describe snapshots the working copy before rewriting the description, so
# this is what moves the edits off disk. It touches no commit but this one.
jj describe -m "$2"
jj bookmark create "$bookmark" -r @

printf '\nParked at %s\n' "$bookmark"
jj log --no-graph -r "$bookmark" \
  -T 'change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n"'

printf '\nFiles:\n'
jj diff --summary -r "$bookmark"

scaffolding=$(jj diff --summary -r "$bookmark" \
  | grep -E 'node_modules/|src/modules/api/generated' || true)
if [[ -n $scaffolding ]]; then
  printf '\nScaffolding in the snapshot, must not reach a commit:\n%s\n' "$scaffolding"
fi

printf '\nThis workspace is parked. Run no further command in %s.\n' "$workspace"
