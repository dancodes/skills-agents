"""Programmatic checks for writing-tics eval outputs.

Usage: python check_output.py evals.json <eval_id> <output_file>

Runs the machine-checkable parts of each eval: required strings (numbers,
names, code spans), forbidden patterns (the tics themselves), header level,
no em dashes, no "It is not X. It is Y." reveal, and the unchanged check for
the clean passage. Short or verbless sentences are printed as warnings for a
human to judge, because fragment detection without a parser is approximate.
"""
import json
import re
import sys

DASHES = re.compile(r"\u2014|\u2013| -- |\s--\s")
NEG_FIRST_STRICT = re.compile(
    r"\b(?:It|This|That)\s+(?:is|was)\s+not\b[^.]*\.\s+(?:It|This|That)\s+(?:is|was)\b"
    r"|\b(?:It|This|That)\s+(?:isn't|wasn't)\b[^.]*\.\s+(?:It|This|That)(?:'s|\s+is|\s+was)\b"
)
VERBS = set(
    "is are was were be been being has have had do does did can could will would shall should may might must "
    "runs run takes take scores score falls fall spikes spike jumps jump starts start changes change sits sit "
    "convert converts happens happen leave leaves caps cap means mean uses use comes come shows show treated treat "
    "affected hit makes make grows grow explain explains stayed reached ran tested caused cause understates "
    "belong belongs split showed".split()
)


def sentences(text):
    out = []
    in_code = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s or s.startswith(("#", "-", "*", "|", ">")) or re.match(r"^\d+\.", s) or s.endswith(":"):
            continue
        out.extend(x for x in re.split(r"(?<=[.!?])\s+", s) if x)
    return out


def looks_fragment(sent):
    words = re.findall(r"[A-Za-z']+", re.sub(r"`[^`]*`", "X", sent))
    lower = [w.lower() for w in words]
    has_verb = any(w in VERBS or w.endswith(("ed", "n't")) for w in lower)
    return len(words) <= 3 or not has_verb


def main():
    evals = {e["id"]: e for e in json.load(open(sys.argv[1]))["evals"]}
    ev = evals[int(sys.argv[2])]
    out = open(sys.argv[3]).read()
    checks = ev.get("checks", {})
    results = []

    def rec(name, ok, evidence=""):
        results.append({"text": name, "passed": bool(ok), "evidence": evidence})

    if checks.get("unchanged"):
        rec("output identical to input (whitespace-trimmed)", out.strip() == ev["input"].strip(),
            "identical" if out.strip() == ev["input"].strip() else "differs")
    for r in checks.get("required", []):
        rec(f"contains {r!r}", r in out)
    for f in checks.get("forbidden", []):
        m = re.search(f, out)
        rec(f"does not match /{f}/", not m, m.group(0) if m else "")
    if "header_level" in checks:
        first = next((l for l in out.splitlines() if l.startswith("#")), "")
        rec(f"header level {checks['header_level'].strip()}", first.startswith(checks["header_level"]), first)
    m = DASHES.search(out)
    rec("no em/en dash or spaced double hyphen", not m, repr(m.group(0)) if m else "")
    m = NEG_FIRST_STRICT.search(out)
    rec("no 'It is not X. It is Y.' reveal", not m, m.group(0) if m else "")

    frags = [s for s in sentences(out) if looks_fragment(s)]
    passed = sum(r["passed"] for r in results)
    print(json.dumps({"eval": ev["eval_name"], "passed": passed, "total": len(results),
                      "failures": [r for r in results if not r["passed"]],
                      "fragment_warnings": frags}, indent=2))


if __name__ == "__main__":
    main()
