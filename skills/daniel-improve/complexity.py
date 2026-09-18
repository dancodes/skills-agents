#!/usr/bin/env python3
"""Rank every function in the given Python files by size, worst first.

Runs ruff with each limit set to 0 so it reports the true score for every
function instead of only the ones over a threshold, then maps each diagnostic
back to its enclosing function with `ast`.

    complexity.py src/a.py src/b.py
    complexity.py --json src/a.py          # machine-readable, for before/after diffing
    RUFF="uv run ruff" complexity.py src/a.py

Reads nothing but the files named. Writes nothing. `--isolated` keeps the
repository's own ruff config out of it, so the numbers do not move when someone
edits pyproject.toml.
"""

import argparse
import ast
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

RULES = {
    "PLR0915": "stmt",
    "C901": "c901",
    "PLR0914": "locals",
    "PLR0912": "branches",
    "PLR0911": "returns",
    "PLR0913": "args",
}

COLUMNS = ["stmt", "c901", "locals", "branches", "returns", "args"]

# PLR0915 says "(33 > 0)", PLR0914 says "(14/0)".
SCORE = re.compile(r"\((\d+)\s*(?:>|/)\s*\d+\)")

DEFAULT_RUFF = "uvx ruff@0.12.4"


def run_ruff(ruff: str, paths: list[str]) -> list[dict]:
    command = [
        *shlex.split(ruff),
        "check",
        "--isolated",
        "--preview",
        "--no-cache",
        "--output-format",
        "json",
        "--select",
        ",".join(RULES),
        "--config",
        "lint.mccabe.max-complexity = 0",
        "--config",
        "lint.pylint.max-branches = 0",
        "--config",
        "lint.pylint.max-locals = 0",
        "--config",
        "lint.pylint.max-statements = 0",
        "--config",
        "lint.pylint.max-returns = 0",
        "--config",
        "lint.pylint.max-args = 0",
        *paths,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if not result.stdout.strip():
        sys.exit(f"ruff produced no output.\n{result.stderr.strip()}")
    return json.loads(result.stdout)


def functions_in(path: Path) -> list[tuple[int, int, str]]:
    tree = ast.parse(path.read_text())
    found: list[tuple[int, int, str]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                name = f"{prefix}{child.name}"
                found.append((child.lineno, child.end_lineno or child.lineno, name))
                walk(child, f"{name}.")
            elif isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            else:
                walk(child, prefix)

    walk(tree, "")
    return found


def enclosing(spans: list[tuple[int, int, str]], row: int) -> str | None:
    inside = [span for span in spans if span[0] <= row <= span[1]]
    if not inside:
        return None
    return max(inside, key=lambda span: span[0])[2]


def collect(ruff: str, paths: list[str]) -> dict[tuple[str, str], dict[str, int]]:
    # ruff reports absolute filenames, so both sides are resolved before matching.
    spans = {str(Path(path).resolve()): functions_in(Path(path)) for path in paths}
    shown = {str(Path(path).resolve()): path for path in paths}
    scores: dict[tuple[str, str], dict[str, int]] = {}
    for item in run_ruff(ruff, paths):
        column = RULES.get(item["code"])
        match = SCORE.search(item["message"])
        if column is None or match is None:
            continue
        key = str(Path(item["filename"]).resolve())
        name = enclosing(spans.get(key, []), item["location"]["row"])
        if name is None:
            continue
        scores.setdefault((shown.get(key, key), name), {})[column] = int(match.group(1))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    parser.add_argument("--top", type=int, default=0, help="show only the N worst functions")
    args = parser.parse_args()

    scores = collect(os.environ.get("RUFF", DEFAULT_RUFF), args.paths)
    rows = sorted(scores.items(), key=lambda item: item[1].get("stmt", 0), reverse=True)
    if args.top:
        rows = rows[: args.top]

    if args.json:
        print(
            json.dumps(
                [{"file": file, "function": name, **values} for (file, name), values in rows],
                indent=2,
            )
        )
        return

    if not rows:
        print("No functions scored. Check the paths.")
        return

    width = max(len(name) for (_, name), _ in rows)
    header = f"{'function':<{width}}  " + "  ".join(f"{column:>8}" for column in COLUMNS) + "  file"
    print(header)
    print("-" * len(header))
    for (file, name), values in rows:
        cells = "  ".join(f"{values.get(column, 0):>8}" for column in COLUMNS)
        print(f"{name:<{width}}  {cells}  {file}")


if __name__ == "__main__":
    main()
