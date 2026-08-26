#!/usr/bin/env bash

# Install this repository's skills/, agents/ and hooks/ for Claude Code under
# ~/.claude (or the directory specified by CLAUDE_HOME).

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  install.sh

Environment:
  CLAUDE_HOME  Override Claude's home directory (default: ~/.claude).

Examples:
  ./install.sh
  CLAUDE_HOME=/tmp/claude-test ./install.sh
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

if [[ ${1:-} == '-h' || ${1:-} == '--help' ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  usage >&2
  exit 2
fi

source_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
claude_home=${CLAUDE_HOME:-$HOME/.claude}

skills_source="$source_root/skills"
agents_source="$source_root/agents"
hooks_source="$source_root/hooks"
[[ -d $skills_source ]] || die "No skills/ directory next to install.sh."
[[ -d $agents_source ]] || die "No agents/ directory next to install.sh."
[[ -d $hooks_source ]] || die "No hooks/ directory next to install.sh."

skills_destination="$claude_home/skills"
agents_destination="$claude_home/agents"
hooks_destination="$claude_home/hooks"
mkdir -p "$skills_destination" "$agents_destination" "$hooks_destination"

cp -a "$skills_source/." "$skills_destination/"
cp -a "$agents_source/." "$agents_destination/"
cp -a "$hooks_source/." "$hooks_destination/"

printf 'Installed skills into %s\n' "$skills_destination"
printf 'Installed agents into %s\n' "$agents_destination"
printf 'Installed hooks into %s\n' "$hooks_destination"
