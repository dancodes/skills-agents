#!/usr/bin/env bash
# Test install.sh in temp dirs with a fake pi on PATH. Covers: pi absent
# (skip, no Pi dirs created), pi present (rendered install, hook removal,
# Agent tool mapping, Pi path expressions, executable scripts preserved,
# idempotence), and renderer failure on an unknown tool.

set -Eeuo pipefail

source_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# Fake pi that answers command -v via an executable on PATH.
mkdir -p "$tmp/bin" "$tmp/emptybin"
printf '#!/usr/bin/env sh\nexit 0\n' > "$tmp/bin/pi"
chmod +x "$tmp/bin/pi"

claude_home="$tmp/absent/claude"
out=$(PATH="$tmp/emptybin:/usr/bin:/bin" PI_CODING_AGENT_DIR="$tmp/absent/pi" \
  CLAUDE_HOME="$claude_home" "$source_root/install.sh")
[[ $out == *"Skipping Pi install"* ]] || fail "no skip message when pi absent: $out"
[[ -d ${tmp:-}/absent/pi ]] && fail "created Pi dir when pi absent"
[[ -f $claude_home/skills/daniel/SKILL.md ]] || fail "Claude skills not installed when pi absent"
[[ -f $claude_home/hooks/forbidden-commands.py ]] || fail "Claude hooks not installed when pi absent"
echo "ok: pi absent skips cleanly"

claude_home="$tmp/present/claude"
pi_home="$tmp/present/pi-agent"
PATH="$tmp/bin:$PATH" PI_CODING_AGENT_DIR="$pi_home" CLAUDE_HOME="$claude_home" \
  "$source_root/install.sh" > "$tmp/install.log"

[[ -f $pi_home/agents/impl.md ]] || fail "Pi agents not installed"
[[ -f $pi_home/skills/no-comments/SKILL.md ]] || fail "Pi skills not installed"
[[ -f $claude_home/hooks/forbidden-commands.py ]] || fail "Claude hooks missing"
# Claude copies stay verbatim: canonical hooks frontmatter must survive.
grep -q "^hooks:" "$claude_home/agents/impl.md" || fail "Claude impl.md lost hooks frontmatter"
grep -q "^hooks:" "$claude_home/agents/jj.md" || fail "Claude jj.md lost hooks frontmatter"
grep -q "^hooks:" "$claude_home/skills/daniel/SKILL.md" || fail "Claude daniel skill lost hooks frontmatter"
grep -q "^hooks:" "$claude_home/skills/daniel-commit-clean/SKILL.md" || fail "Claude commit-clean skill lost hooks frontmatter"
! grep -rq "hooks:" "$pi_home/agents" "$pi_home/skills" || fail "hooks survived into Pi install"
# Pi skills must not carry unmapped Claude tool names.
! grep -rEq 'tools:.*\\b(Bash|Read|Grep|Glob|Edit|Write|Agent)\\b' "$pi_home/skills" \
  || fail "unmapped Claude tool names survived into Pi skills"
grep -q "^tools: bash, read, grep, find, edit" \
  "$pi_home/agents/jj.md" || fail "jj agent tools wrong"
grep -q "^systemPromptMode: replace$" "$pi_home/agents/impl.md" || fail "systemPromptMode missing"
grep -q "^inheritProjectContext: true$" "$pi_home/agents/impl.md" || fail "inheritProjectContext missing"
! grep -rq "CLAUDE_CONFIG_DIR" "$pi_home" || fail "Claude config expression survived into Pi install"
grep -rq 'PI_CODING_AGENT_DIR:-$HOME/.pi/agent' "$pi_home/skills/daniel/SKILL.md" \
  || fail "Pi path expression missing"
grep -q "^skills: no-comments$" "$pi_home/agents/impl.md" || fail "skills not preserved"
! grep -q "^tools:" "$pi_home/agents/impl.md" || fail "impl should inherit Pi's default tools"
[[ -x "$pi_home/skills/daniel/new-workspace.sh" ]] || fail "skill script lost executable bit"
[[ -x "$pi_home/skills/daniel/typecheck.py" ]] || fail "typecheck.py lost executable bit"
grep -q "You implement code changes" "$pi_home/agents/impl.md" || fail "agent body lost"
echo "ok: pi present renders skills and agents"

mkdir -p "$tmp/broken/agents"
printf -- '---\nname: broken\ntools: Bash, Teleport\n---\nbody\n' > "$tmp/broken/agents/broken.md"
broken_root="$tmp/broken"
cp "$source_root/install.sh" "$broken_root/install.sh"
cp -a "$source_root/scripts" "$source_root/skills" "$source_root/agents" "$broken_root/"
mkdir -p "$broken_root/hooks"
out=$(PATH="$tmp/bin:$PATH" PI_CODING_AGENT_DIR="$tmp/broken/pi" \
  CLAUDE_HOME="$tmp/broken/claude" "$broken_root/install.sh" 2>&1) \
  && fail "install succeeded despite unknown tool"
[[ $out == *"broken.md"* && $out == *"Teleport"* ]] || fail "error does not name file and tool: $out"
echo "ok: unknown tool fails naming file and tool"

sums() {
  find "$1" -type f -print0 | sort -z | xargs -0 python3 -c '
import hashlib, sys
for p in sys.argv[1:]:
    print(hashlib.sha256(open(p, "rb").read()).hexdigest(), p)
'
}
sums "$pi_home" > "$tmp/first.sums"
PATH="$tmp/bin:$PATH" PI_CODING_AGENT_DIR="$pi_home" CLAUDE_HOME="$claude_home" \
  "$source_root/install.sh" > /dev/null
sums "$pi_home" > "$tmp/second.sums"
diff "$tmp/first.sums" "$tmp/second.sums" || fail "second install changed the Pi tree"
echo "ok: install is idempotent"

echo "ALL TESTS PASSED"
