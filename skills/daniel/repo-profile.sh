#!/usr/bin/env bash
# Find the private repo profile for a jj workspace and print what it defines.

set -Eeuo pipefail

private_root=${SKILLS_AGENTS_PRIVATE:-$HOME/.config/skills-agents}

usage() {
  cat >&2 <<'EOF'
Usage:
  repo-profile.sh root [path]            jj workspace root that holds path
  repo-profile.sh dir [path]             profile directory, empty when none matches
  repo-profile.sh scaffold-grep [path]   ERE matching scaffolding paths in jj diff --summary
  repo-profile.sh scaffold-revset [path]  jj revset of commits touching those paths
EOF
  exit 2
}

main() {
  local root profile
  [[ $# -ge 1 && $# -le 2 ]] || usage
  root=$(workspace_root "${2:-$PWD}")
  profile=$(match "$root")
  case $1 in
    root) printf '%s\n' "$root" ;;
    dir) [[ -z $profile ]] || printf '%s\n' "$profile" ;;
    scaffold-grep) scaffolding "$profile" | paste -sd'|' - | sed 's/.*/(^|[ \/])(&)(\/|$)/' ;;
    scaffold-revset) scaffolding "$profile" | while read -r path; do printf 'files(glob:"**/%s") | files(glob:"**/%s/**")\n' "$path" "$path"; done | paste -sd'|' - | sed 's/)|f/) | f/g' ;;
    *) usage ;;
  esac
}

workspace_root() {
  local dir
  dir=$(realpath -- "$1")
  while [[ $dir != / && ! -d $dir/.jj ]]; do dir=$(dirname -- "$dir"); done
  printf '%s\n' "$dir"
}

match() {
  local profile
  for profile in "$private_root"/repos/*/; do
    [[ -f $profile/match && -e $1/$(<"$profile/match") ]] && { printf '%s\n' "${profile%/}"; return; }
  done
  return 0
}

scaffolding() {
  printf 'node_modules\n'
  [[ -n $1 && -f $1/scaffolding ]] && grep -v '^\s*$' "$1/scaffolding" || true
}

main "$@"
