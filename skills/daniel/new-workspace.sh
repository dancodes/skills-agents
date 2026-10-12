#!/usr/bin/env bash

# Create the jj workspace for a /daniel feature and run the repo profile's
# workspace setup. Prints the new workspace path.

set -Eeuo pipefail

if [[ $# -lt 1 || $# -gt 2 || ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  printf 'Usage: new-workspace.sh <feature-name> [base-revision]\n' >&2
  exit 2
fi

# Derive the repo root from jj instead of pwd, so running the script from a
# subdirectory still finds the right profile and links.
source=$(jj workspace root 2>/dev/null || jj root)
workspace=$source/../daniel-workspaces/$1

mkdir -p "$(dirname -- "$workspace")"
# With a base revision the working copy starts as `jj new <rev>`, so the work
# builds on that commit instead of on the current branch tip.
if [[ -n ${2:-} ]]; then
  jj workspace add --revision "$2" "$workspace"
else
  jj workspace add "$workspace"
fi
workspace=$(cd -- "$workspace" && pwd)

# The private repo profile links dependencies and generated files that the new
# working copy lacks.
profile=$("$(dirname -- "$(realpath -- "$0")")/repo-profile.sh" dir "$source")
if [[ -n $profile && -x $profile/setup-workspace.sh ]]; then
  "$profile/setup-workspace.sh" "$source" "$workspace"
fi

printf '%s\n' "$workspace"
