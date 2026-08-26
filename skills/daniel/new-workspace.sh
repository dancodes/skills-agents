#!/usr/bin/env bash

# Create the jj workspace for a /daniel feature and link the current
# workspace's dependencies into it. Prints the new workspace path.

set -Eeuo pipefail

if [[ $# -ne 1 || ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: new-workspace.sh <feature-name>\n' >&2
  exit 2
fi

source=$(pwd)
workspace=$source/../daniel-workspaces/$1

mkdir -p "$(dirname -- "$workspace")"
jj workspace add "$workspace"
workspace=$(cd -- "$workspace" && pwd)

# Link the contents of each node_modules rather than the directory itself, so
# every workspace gets its own .vite: a shared dep cache is re-bundled by
# whichever workspace runs vitest next, which breaks runs in the others
# mid-flight.
for modules in node_modules */node_modules; do
  [[ -d $modules && ! -e $workspace/$modules ]] || continue
  mkdir -p "$workspace/$modules"
  find "$source/$modules" -mindepth 1 -maxdepth 1 \
    ! -name '.vite*' ! -name '.cache' \
    -exec ln -s {} "$workspace/$modules/" \;
done

# Without the generated API client, typecheck in the workspace fails with
# `Cannot find module 'src/modules/api/generated'`.
generated=frontend/src/modules/api/generated
if [[ -e $generated && ! -e $workspace/$generated ]]; then
  mkdir -p "$(dirname -- "$workspace/$generated")"
  ln -s "$source/$generated" "$workspace/$generated"
fi

printf '%s\n' "$workspace"
