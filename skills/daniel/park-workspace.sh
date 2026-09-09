#!/usr/bin/env bash

# Park an impl workspace's finished work on a handoff/<name> bookmark, which
# outlives the workspace going stale or being forgotten. /daniel-integrate reads
# it. The bookmark points at the tip of whatever stack the workspace built, so it
# carries every round committed with commit-workspace.sh; the script then forgets
# the workspace and deletes its directory.
#
# With --onto <rev>, the workspace was based on that revision rather than the
# branch tip, and the work lands there directly instead of being parked: the
# bookmark on <rev> moves up to the tip, or with --squash the stack is folded
# into <rev> itself.

set -Eeuo pipefail

if [[ $# -lt 2 || ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: park-workspace.sh <workspace-path> <one-line-message> [--onto <rev> [--squash]]\n' >&2
  exit 2
fi

workspace_arg=$1
message=$2
shift 2

onto=
squash=
while [[ $# -gt 0 ]]; do
  case $1 in
    --onto) onto=$2; shift 2 ;;
    --squash) squash=1; shift ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

source=$(jj workspace root 2>/dev/null || jj root)
# The source workspace's working copy: it and everything trunk-ward of it is
# history the impl workspace branched off, so it bounds the stack below. With
# --onto, the workspace branched off that revision instead.
base=$(jj --ignore-working-copy log --no-graph -r "${onto:-@}" -T 'change_id.shortest(12)')
workspace=$(cd -- "$workspace_arg" && pwd)
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

# The stack the workspace built: the rounds commit-workspace.sh described, plus
# the snapshot above. Only its tip is bookmarked; the rest ride along as
# ancestors, and /daniel-integrate walks them from the bookmark.
stack=()
while read -r commit; do
  stack+=("$commit")
done < <(jj --ignore-working-copy log --no-graph --reversed \
  -r "::$change ~ ::$base" -T 'change_id.shortest(12) ++ "\n"')

# An empty tip is the placeholder commit-workspace.sh left for a round that
# never came, so the round below it is the tip that holds work.
if [[ -z $(jj --ignore-working-copy diff --summary -r "$change") ]]; then
  unset "stack[$((${#stack[@]} - 1))]"
  if (( ${#stack[@]} == 0 )); then
    printf 'Nothing to park: %s is empty and no round was committed.\n' "$change" >&2
    exit 1
  fi
  change=${stack[$((${#stack[@]} - 1))]}
  printf 'Tip was empty, so parking the last committed round (%s).\n' "$change" >&2
else
  jj --ignore-working-copy describe -r "$change" -m "$message"
fi

if [[ -z $onto ]]; then
  printf '\nParking at %s, %s commit(s):\n' "$bookmark" "${#stack[@]}"
elif [[ -n $squash ]]; then
  printf '\nSquashing %s commit(s) into %s:\n' "${#stack[@]}" "$base"
else
  printf '\nLanding %s commit(s) on top of %s:\n' "${#stack[@]}" "$base"
fi
for commit in "${stack[@]}"; do
  jj --ignore-working-copy log --no-graph -r "$commit" \
    -T 'change_id.shortest(8) ++ "  " ++ description.first_line() ++ "\n"'
  jj --ignore-working-copy diff --summary -r "$commit" | sed 's/^/    /'
done

scaffolding=$(for commit in "${stack[@]}"; do
    jj --ignore-working-copy diff --summary -r "$commit"
  done | grep -E 'node_modules/|src/modules/api/generated' || true)
if [[ -n $scaffolding ]]; then
  printf '\nScaffolding in the snapshot, must not reach a commit:\n%s\n' "$scaffolding"
fi

# The listing above reads the stack commits, so it runs before a squash
# abandons them.
if [[ -z $onto ]]; then
  jj --ignore-working-copy bookmark create "$bookmark" -r "$change"
elif [[ -n $squash ]]; then
  # Fold the whole stack into the base commit, keeping its description; any
  # bookmark on it stays where it is.
  jj --ignore-working-copy squash --use-destination-message \
    --from "$base::$change ~ $base" --into "$base"
else
  # The work is already commits on top of the base, so landing it is moving
  # whatever bookmark sat on the base up to the tip.
  jj --ignore-working-copy bookmark move --from "$base" --to "$change" \
    || printf 'No bookmark on %s to move; the work is at %s.\n' "$base" "$change" >&2
fi

printf '\nThis workspace is finished. Run no further command in it.\n'

# The repository holds the work now, so the workspace is disposable. Forget it
# from the source workspace, never from inside the one being removed.
cd -- "$source"
if jj --ignore-working-copy workspace forget "$name"; then
  rm -rf -- "$workspace"
  printf '\nWorkspace forgotten and %s deleted.\n' "$workspace"
else
  printf '\nParked, but could not forget the workspace. Delete %s by hand.\n' "$workspace" >&2
fi
