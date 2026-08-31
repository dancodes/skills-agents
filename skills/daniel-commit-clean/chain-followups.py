#!/usr/bin/env python3
"""List every file on the branch that a commit other than its owner modified.

A branch reads best when each commit owns its files outright. The exceptions are
real: a registry every section appends to is modified by every section's commit
and belongs to none of them. Everything between those two shapes is a follow-up
that was never squashed back, and only a reader can tell which is which, so this
prints the evidence and makes no decision.

Every jj call is read-only and passes --ignore-working-copy: the /daniel agents
share one repository, and a snapshot here would rewrite a commit another agent
is sitting on.
"""
import re
import subprocess
import sys
from collections import Counter, defaultdict

DIFF_LINES = 60
AGGREGATOR_THRESHOLD = 5

USAGE = """Usage: chain-followups.py [--root <revset>] [--aggregator-threshold <n>]

--root defaults to trunk(); the branch is <root>..@.
--aggregator-threshold defaults to 5; files touched more often collapse to one line."""

LEGEND = """How to read this
  A file's owner is the branch commit that added it. A commit that modifies a
  file it does not own made a follow-up: a change that, at the time, was easier
  to append than to squash back.

  AGGREGATORS   files touched more times than the threshold. A registry, a
                barrel file, a fixture every section extends. Every commit
                touching one is a legitimate follow-up, so their cases are
                counted rather than listed. Read the list: a file that is not
                an aggregator has no business being on it.

  Each case below prints the owner, the follow-up commit, and the follow-up's
  own diff of the file. Hunks that remove or rewrite lines carry a
  "lines last written by" label read from `jj file annotate` on the follow-up's
  parent: that names who wrote what this hunk is changing, which is the whole
  question. Hunks that only add lines carry no label, because there is nothing
  to attribute and `jj absorb` will leave them alone for the same reason.

  Three commands are printed per case and none of them is a recommendation:
    leave    the change belongs where it is. Most cases.
    squash   the whole touch belongs to the owner.
    absorb   part of the touch belongs to the owner. Hunks jj cannot attribute
             stay in the follow-up commit, which is the safe failure.

  Cases run deepest-owner-first, so the rewrite nearest the branch root goes
  first. Files with no owner on the branch are not cases: they existed before
  it, and there is nowhere to put them back."""


def jj(args):
    result = subprocess.run(
        ["jj", "--ignore-working-copy", "--color=never"] + args,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"jj {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def branch_commits(root):
    """The branch oldest first, so the first commit to add a path comes first."""
    template = (
        '"C\\t" ++ change_id.shortest(8) ++ "\\t" ++ description.first_line() ++ "\\n"'
        ' ++ diff.files().map(|f| "F\\t" ++ f.status_char() ++ "\\t" ++ f.target().path()'
        ' ++ "\\n").join("")'
    )
    commits = []
    for line in jj(["log", "-r", f"{root}..@", "--no-graph", "-T", template]).splitlines():
        kind, _, rest = line.partition("\t")
        if kind == "C":
            cid, _, description = rest.partition("\t")
            commits.append((cid, description, []))
        elif kind == "F" and commits:
            status, _, path = rest.partition("\t")
            commits[-1][2].append((status, path))
    commits.reverse()
    return commits


def resolve_owners(commits):
    """A path's owner is the first commit to add it. A path only ever modified
    predates the branch, so it has no owner here."""
    owners = {}
    for cid, _, files in commits:
        for status, path in files:
            if status == "A":
                owners.setdefault(path, cid)
    return owners


def find_followups(commits, owners):
    """(follow-up commit, path) for every touch by a commit that is not the owner."""
    return [(cid, path) for cid, _, files in commits for _, path in files
            if path in owners and owners[path] != cid]


def hunks(rev, path):
    """Hunk headers with the pre-image line numbers each one removes. Those
    numbers index the parent revision, which is what annotate is read against."""
    found, header, removed = [], None, []
    line_number = 0
    for line in jj(["diff", "--git", "-r", rev, path]).splitlines():
        start = re.match(r"@@ -(\d+)", line)
        if start:
            if header:
                found.append((header, removed))
            header, removed = line, []
            line_number = int(start.group(1))
        elif not header or line.startswith(("---", "+++")):
            continue
        elif line[:1] == "-":
            removed.append(line_number)
            line_number += 1
        elif line[:1] == "+":
            continue
        else:
            line_number += 1
    if header:
        found.append((header, removed))
    return found


def authorship(rev, path, lines):
    out = jj(["file", "annotate", "-r", rev, "-T",
              'commit.change_id().shortest(8) ++ "\\n"', path])
    by_line = out.splitlines()
    return Counter(by_line[n - 1] for n in lines if 0 < n <= len(by_line))


def labels(cid, path, known):
    """header -> who last wrote the lines it changes. Pure additions get nothing."""
    out = {}
    for header, removed in hunks(cid, path):
        if not removed:
            continue
        wrote = authorship(f"{cid}-", path, removed)
        shown = ", ".join(f"{owner} x{n}" for owner, n in wrote.most_common(3)
                          if owner in known)
        if shown:
            out[header] = shown
    return out


def case(cid, path, owner, by_cid):
    print(f"{path}")
    print(f"     owner      {owner}  {by_cid[owner]}")
    print(f"     follow-up  {cid}  {by_cid[cid]}")
    labelled = labels(cid, path, set(by_cid))
    diff = jj(["diff", "--git", "-r", cid, path]).splitlines()
    for line in diff[:DIFF_LINES]:
        note = labelled.get(line)
        print(f"     {line}" + (f"     lines last written by {note}" if note else ""))
    if len(diff) > DIFF_LINES:
        print(f"     ... {len(diff) - DIFF_LINES} more lines,"
              f" see jj diff --git -r {cid} {path}")
    print(f"\n     leave\n"
          f"     squash   jj squash --from {cid} --into {owner} -u -- {path}\n"
          f"     absorb   jj absorb --from {cid} --into {owner} -- {path}\n")


def report(root, threshold):
    commits = branch_commits(root)
    if not commits:
        sys.exit(f"No commits in {root}..@; pass the branch root with --root.")
    by_cid = {cid: description for cid, description, _ in commits}
    depth = {cid: n for n, (cid, _, _) in enumerate(commits)}
    owners = resolve_owners(commits)
    touches = Counter(path for _, _, files in commits for _, path in files)
    followups = find_followups(commits, owners)

    aggregators = sorted({p for _, p in followups if touches[p] > threshold},
                         key=lambda p: -touches[p])
    cases = sorted((c for c in followups if touches[c[1]] <= threshold),
                   key=lambda c: depth[owners[c[1]]])

    print(f"{LEGEND}\n")
    print(f"Branch {root}..@: {len(commits)} commits, {len(owners)} files owned,"
          f" {len(followups)} follow-up touches.\n")

    if aggregators:
        collapsed = sum(1 for _, p in followups if touches[p] > threshold)
        print(f"AGGREGATORS, {collapsed} follow-ups in {len(aggregators)} files"
              f" touched more than {threshold} times:")
        for path in aggregators:
            print(f"  {touches[path]:3}x  {path}")
            print(f"        owned by {owners[path]}  {by_cid[owners[path]]}")
        print()

    print(f"{len(cases)} case(s), deepest owner first:\n")
    for cid, path in cases:
        case(cid, path, owners[path], by_cid)


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(f"{USAGE}\n\n{LEGEND}")
        return 0
    root, threshold = "trunk()", AGGREGATOR_THRESHOLD
    if "--root" in argv:
        index = argv.index("--root")
        root = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    if "--aggregator-threshold" in argv:
        index = argv.index("--aggregator-threshold")
        threshold = int(argv[index + 1])
        argv = argv[:index] + argv[index + 2:]
    if argv:
        sys.exit(USAGE)
    report(root, threshold)
    return 0


def test():
    commits = [
        ("aaaaaaaa", "spec parser", [("A", "gen.py"), ("A", "schema.json")]),
        ("bbbbbbbb", "panel map", [("A", "map.md"), ("M", "gen.py")]),
        ("cccccccc", "supplemental", [("M", "map.md"), ("M", "gen.py"),
                                      ("M", "trunkfile.ts"), ("A", "new.ts")]),
    ]
    owners = resolve_owners(commits)
    assert owners == {"gen.py": "aaaaaaaa", "schema.json": "aaaaaaaa",
                      "map.md": "bbbbbbbb", "new.ts": "cccccccc"}, owners
    assert "trunkfile.ts" not in owners

    found = find_followups(commits, owners)
    assert found == [("bbbbbbbb", "gen.py"), ("cccccccc", "map.md"),
                     ("cccccccc", "gen.py")], found

    global jj
    jj = lambda args: (
        "diff --git a/map.md b/map.md\n"
        "--- a/map.md\n"
        "+++ b/map.md\n"
        "@@ -3,4 +3,4 @@ header\n"
        " context\n"
        "-was\n"
        "+is\n"
        " tail\n"
        "@@ -20,0 +21,2 @@ other\n"
        "+added\n"
        "+added\n"
    )
    assert hunks("c", "map.md") == [("@@ -3,4 +3,4 @@ header", [4]),
                                    ("@@ -20,0 +21,2 @@ other", [])], hunks("c", "map.md")
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main(sys.argv[1:]))
