#!/usr/bin/env bash

# Forget and delete /daniel workspaces that hold no unparked work. With names,
# only those; without, every workspace under daniel-workspaces.

set -Eeuo pipefail

if [[ ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: cleanup-workspace.sh [workspace-name...]\n' >&2
  exit 2
fi

source=$(jj workspace root 2>/dev/null || jj root)
root=$(cd -- "$source/.." && pwd)/daniel-workspaces
cd -- "$source"

names=("$@")
if (( ${#names[@]} == 0 )); then
  while read -r name; do names+=("$name"); done < <(jj --ignore-working-copy workspace list -T 'name ++ "\n"')
  for dir in "$root"/*/; do
    [[ -d $dir && ! -d $dir/.jj ]] && printf 'skip %s: not a jj workspace. Delete it by hand.\n' "$dir"
  done
fi

for name in "${names[@]}"; do
  workspace=$(jj --ignore-working-copy workspace root --name "$name" 2>/dev/null) || {
    printf 'skip %s: no such workspace.\n' "$name"
    continue
  }
  [[ $workspace == "$root"/* ]] || {
    (( $# )) && printf 'skip %s: not under %s.\n' "$name" "$root"
    continue
  }
  # Snapshot first, so edits still on disk count as work.
  if [[ -d $workspace ]] && ! jj -R "$workspace" status >/dev/null 2>&1; then
    printf 'skip %s: working copy is stale, edits on disk may be unsnapshotted.\n' "$name"
    continue
  fi
  # Work is a non-empty commit that no bookmark and no other workspace keeps.
  work=$(jj --ignore-working-copy log --no-graph -T 'change_id.shortest(8) ++ " "' -r \
    "(::\"$name\"@ ~ ::(bookmarks() | remote_bookmarks() | (working_copies() ~ \"$name\"@))) ~ empty()")
  if [[ -n $work ]]; then
    printf 'skip %s: unparked work in %s\n' "$name" "${work% }"
    continue
  fi
  jj --ignore-working-copy workspace forget "$name"
  rm -rf -- "$workspace"
  printf 'removed %s\n' "$name"
done
"$(dirname -- "$(realpath -- "$0")")/../daniel-verify/verify.sh" stop --gone || true
