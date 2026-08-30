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

# jj snapshots the whole working copy, so the links below would land in the
# parked commit and keep it alive as a dangling head after integration. A
# .gitignore listing itself keeps both the links and itself out of every snapshot.
ignore() {
  mkdir -p -- "$1"
  [[ -e $1/.gitignore ]] || printf '%s\n.gitignore\n' "$2" > "$1/.gitignore"
}

mkdir -p "$(dirname -- "$workspace")"
jj workspace add "$workspace"
workspace=$(cd -- "$workspace" && pwd)

# Link the contents of each node_modules rather than the directory itself, so
# every workspace gets its own .vite: a shared dep cache is re-bundled by
# whichever workspace runs vitest next, which breaks runs in the others
# mid-flight.
for modules in node_modules */node_modules; do
  [[ -d $modules && ! -e $workspace/$modules ]] || continue
  ignore "$workspace/$modules" '*'
  find "$source/$modules" -mindepth 1 -maxdepth 1 \
    ! -name '.vite*' ! -name '.cache' \
    -exec ln -s {} "$workspace/$modules/" \;
done

# Without the generated API client, typecheck in the workspace fails with
# `Cannot find module 'src/modules/api/generated'`.
generated=frontend/src/modules/api/generated
if [[ -e $generated && ! -e $workspace/$generated ]]; then
  ignore "$(dirname -- "$workspace/$generated")" "$(basename -- "$generated")"
  ln -s "$source/$generated" "$workspace/$generated"
fi

# Seed the incremental typecheck cache. TypeScript records paths relative to the
# buildinfo, resolved through symlinks, so the ./node_modules prefix is rebased.
buildinfo=frontend/tsconfig.tsbuildinfo
if [[ -f $source/$buildinfo && ! -e $workspace/$buildinfo ]]; then
  modules_prefix=$(realpath --relative-to="$workspace/frontend" "$source/frontend/node_modules")
  sed "s|\"\./node_modules/|\"$modules_prefix/|g" "$source/$buildinfo" > "$workspace/$buildinfo"
fi

# Copy the CodeGraph index rather than indexing the workspace from scratch. The
# database holds no absolute paths, and .codegraph/.gitignore keeps it out of
# every snapshot. daemon.sock, daemon.pid and daemon.log belong to the source's
# running daemon, so the workspace starts its own.
if [[ -d $source/.codegraph && ! -e $workspace/.codegraph ]]; then
  mkdir -- "$workspace/.codegraph"
  find "$source/.codegraph" -mindepth 1 -maxdepth 1 \
    ! -name 'daemon.*' -exec cp -a {} "$workspace/.codegraph/" \;
  codegraph sync --quiet "$workspace" || true
fi

printf '%s\n' "$workspace"
