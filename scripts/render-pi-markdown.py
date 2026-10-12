#!/usr/bin/env python3
"""Render Claude Code agent and skill markdown files into Pi equivalents.

Canonical agents stay the single capability source: agent frontmatter carries
the tools and skills, and one TOOL_MAP maps the Claude tool vocabulary to Pi's.
Hooks never survive rendering; Pi installs must not reference Claude hooks.

Usage:
  render-pi-markdown.py agent <path>
  render-pi-markdown.py skill <path>
"""

import sys
from pathlib import Path

CLAUDE_CONFIG_EXPR = "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PI_CONFIG_EXPR = "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"

TOOL_MAP = {
    "Bash": ["bash"],
    "Read": ["read"],
    "Grep": ["grep"],
    "Glob": ["find"],
    "Edit": ["edit"],
    "Write": ["write"],
    "Agent": ["subagent", "subagent_wait"],
}


def die(path, message):
    sys.exit(f"{path}: {message}")


def parse_frontmatter(text, path):
    """Split a markdown file into an ordered frontmatter mapping and the body.

    Supports the `key: value` and `key:` block-list forms this repo uses.
    Scalar values keep any commas; use scalar_list() to split them.
    """
    if not text.startswith("---\n"):
        die(path, "no frontmatter block")
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        die(path, "frontmatter block not terminated")
    body = text[end + 5:]
    fields = {}
    current = None
    for line in text[4:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line[:1] in (" ", "\t") or line.startswith("- "):
            if current is None:
                die(path, f"list item outside a field: {line!r}")
            fields[current].append(line.strip().removeprefix("-").strip())
        elif ":" in line:
            key, _, value = line.partition(":")
            current = key.strip()
            value = value.strip()
            fields[current] = [] if value == "" else [value]
        else:
            die(path, f"unparsable frontmatter line: {line!r}")
    return fields, body


def scalar_list(fields, key):
    """Split a comma-separated frontmatter list into one flat list."""
    return [
        part.strip()
        for value in fields.get(key, [])
        for part in value.split(",")
        if part.strip()
    ]


def emit_fields(fields):
    lines = ["---"]
    for key, values in fields.items():
        if len(values) == 1:
            lines.append(f"{key}: {values[0]}")
        else:
            lines.append(f"{key}:")
            lines.extend(f"  - {value}" for value in values)
    lines.append("---")
    return "\n".join(lines)


def rewrite_paths(text):
    return text.replace(CLAUDE_CONFIG_EXPR, PI_CONFIG_EXPR)


def render_agent(path):
    fields, body = parse_frontmatter(Path(path).read_text(encoding="utf-8"), path)
    fields.pop("hooks", None)

    pi_tools = []
    for tool in scalar_list(fields, "tools"):
        if tool not in TOOL_MAP:
            die(path, f"unknown tool: {tool}")
        for mapped in TOOL_MAP[tool]:
            if mapped not in pi_tools:
                pi_tools.append(mapped)
    if pi_tools:
        fields["tools"] = [", ".join(pi_tools)]
    else:
        fields.pop("tools", None)

    skills = scalar_list(fields, "skills")
    if skills:
        fields["skills"] = skills

    fields["systemPromptMode"] = ["replace"]
    fields["inheritProjectContext"] = ["true"]
    return emit_fields(fields) + "\n" + rewrite_paths(body)


def render_skill(path):
    fields, body = parse_frontmatter(Path(path).read_text(encoding="utf-8"), path)
    fields.pop("hooks", None)
    return emit_fields(fields) + "\n" + rewrite_paths(body)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("agent", "skill"):
        die("render-pi-markdown.py", "usage: render-pi-markdown.py agent|skill <path>")
    mode, path = sys.argv[1], sys.argv[2]
    render = render_agent if mode == "agent" else render_skill
    sys.stdout.write(render(path))


if __name__ == "__main__":
    main()
