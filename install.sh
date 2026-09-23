#!/usr/bin/env bash

# Install this repository's skills/, agents/ and hooks/ for Claude Code under
# ~/.claude (or the directory specified by CLAUDE_HOME). When the pi coding
# agent is installed, also install Pi-rendered skills and agents under
# PI_CODING_AGENT_DIR (default: ~/.pi/agent). Pi never gets hooks.

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  install.sh

Environment:
  CLAUDE_HOME          Override Claude's home directory (default: ~/.claude).
  PI_CODING_AGENT_DIR  Override Pi's agent directory (default: ~/.pi/agent).
                       Only used when the pi command is installed.

Claude Code always gets skills/, agents/ and hooks/ copied verbatim. When the
`pi` command exists, skills/ and agents/ are also rendered for Pi (hooks
stripped, Claude tool names mapped to Pi tool names, config path expressions
rewritten) and installed there; hooks/ are never installed for Pi. Without
`pi`, the Pi install is skipped and nothing outside Claude's directory is
created.

Examples:
  ./install.sh
  CLAUDE_HOME=/tmp/claude-test ./install.sh
  PI_CODING_AGENT_DIR=/tmp/pi-test ./install.sh
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
renderer="$source_root/scripts/render-pi-markdown.py"

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

if ! command -v pi >/dev/null 2>&1; then
  printf 'Skipping Pi install: pi command not found.\n'
  exit 0
fi

[[ -f $renderer ]] || die "No renderer at $renderer."

pi_agent_dir=${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}
pi_skills_destination="$pi_agent_dir/skills"
pi_agents_destination="$pi_agent_dir/agents"
mkdir -p "$pi_skills_destination" "$pi_agents_destination"

# Rendered SKILL.md overwrites the copied one; cp -a keeps executable bits.
cp -a "$skills_source/." "$pi_skills_destination/"
find "$pi_skills_destination" -name SKILL.md -type f -print0 | while IFS= read -r -d '' skill; do
  rel=${skill#"$pi_skills_destination"/}
  python3 "$renderer" skill "$skill" > "$skill.rendered"
  mv "$skill.rendered" "$skill"
  printf 'Rendered Pi skill %s\n' "$rel"
done

for agent in "$agents_source"/*.md; do
  name=$(basename "$agent")
  python3 "$renderer" agent "$agent" > "$pi_agents_destination/$name"
  printf 'Rendered Pi agent %s\n' "$name"
done

printf 'Installed Pi skills into %s\n' "$pi_skills_destination"
printf 'Installed Pi agents into %s\n' "$pi_agents_destination"
