#!/usr/bin/env python3
"""Resolve the squash target of every file in a handoff, in one command.

Which commit owns a file is not answerable from a per-revision file list: it
cannot tell a rename from a new file, and in a file a dozen commits touch it
names the last toucher rather than the commit whose feature the edited lines
belong to. Squashing on that guess lands content in a commit that never owned
the file, which conflicts through every descendant.

Every jj call is read-only and passes --ignore-working-copy: /daniel agents share
one repository, and a snapshot here would rewrite a commit another agent is in.
"""
import re
import subprocess
import sys
from collections import Counter

CANDIDATE_DIFF_LINES = 60

USAGE = """Usage: handoff-owners.py [handoff-bookmark ...] [--root <revset>]

Resolves the squash target of every file in each handoff. With no bookmark named,
resolves every parked handoff/* bookmark.
--root defaults to trunk(); the branch is <root>..@."""

LEGEND = """How to read this
  A file's target is the branch commit that owns it. Ownership is decided per
  file, so one handoff routinely splits across several targets.

  R / C  rename or copy, printed as "source => target". Both paths go in one
         squash, and the source path's history is what names the owner.
  A M D  added, modified, deleted path.

  touched by <id>   a branch commit whose own diff includes this path. These are
                    the only candidates: squashing into a commit that never
                    touched the path conflicts through every descendant.
  -> <id>           the resolved target. The reason follows in parentheses:
     only commit    the single candidate, so no line-level check was needed.
     removes        that commit wrote the lines this handoff deletes, read from
                    `jj file annotate` on the handoff's parent. Decisive.
     lineage of     the commit that owns the path this file was renamed from.
     split out of   this new file's content was cut out of another file in this
                    handoff, so it belongs where that file's removed lines do.
  -> AMBIGUOUS      several candidates and no decisive signal, usually because
                    the handoff only adds lines. A "context last written by"
                    note is a hint, not an answer: the last commit to touch a
                    neighbouring line is often a later rename rather than the
                    commit whose feature these lines belong to. Each candidate's
                    own diff of the path is printed below the table: decide from
                    those, then squash by hand.
  -> RESURRECTED    a branch commit deleted this path and the handoff adds it
                    back. No recommendation: reviving a file the branch removed
                    is a decision, not a placement.
  -> NEW COMMIT     no branch commit touches this path and it is not a split.

  Draft commands are a starting point, not a plan, and run deepest first: the
  target nearest the branch root comes before the targets above it. They exclude
  every AMBIGUOUS, RESURRECTED and NEW COMMIT file. SCAFFOLDING lists workspace symlinks and generated files
  the park snapshotted, which never belong in a commit. Blast radius lists the
  bookmarks needing a re-push and the workspaces going stale once the targets are
  rewritten."""
SCAFFOLDING = re.compile(r"node_modules/|src/modules/api/generated")


def jj(args):
    result = subprocess.run(
        ["jj", "--ignore-working-copy", "--color=never"] + args,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"jj {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def parked():
    out = jj(["bookmark", "list", "-r", 'bookmarks(glob:"handoff/*")', "-T", 'name ++ "\n"'])
    return out.split()


def branch_commits(root, handoffs):
    """Branch commits, newest first. The handoffs are excluded: a parked snapshot
    touches every path in play, so leaving it in makes every file look owned."""
    template = (
        '"C\\t" ++ change_id.shortest(8) ++ "\\t" ++ description.first_line() ++ "\\n"'
        ' ++ diff.files().map(|f| "F\\t" ++ f.status_char() ++ "\\t" ++ f.source().path()'
        ' ++ "\\t" ++ f.target().path() ++ "\\n").join("")'
    )
    parked = " | ".join(f"({h})" for h in handoffs)
    commits, deleted = [], {}
    revset = f"({root}..@) ~ ({parked})" if parked else f"{root}..@"
    for line in jj(["log", "-r", revset, "--no-graph", "-T", template]).splitlines():
        kind, _, rest = line.partition("\t")
        if kind == "C":
            cid, _, description = rest.partition("\t")
            commits.append((cid, description, set()))
        elif kind == "F" and commits:
            status, source, target = rest.split("\t")
            commits[-1][2].update({source, target})
            if status == "D":
                deleted.setdefault(target, commits[-1][0])
    return commits, deleted


def handoff_files(rev):
    template = (
        'diff.files().map(|f| f.status_char() ++ "\\t" ++ f.source().path()'
        ' ++ "\\t" ++ f.target().path() ++ "\\n").join("")'
    )
    rows = []
    for line in jj(["log", "-r", rev, "--no-graph", "-T", template]).splitlines():
        status, source, target = line.split("\t")
        rows.append((status, source, target))
    return rows


def hunks(rev, path):
    """Line numbers are the diff's pre-image, so they index the parent revision."""
    removed_lines, context_lines, removed_text, line_number = [], [], [], 0
    for line in jj(["diff", "--git", "-r", rev, path]).splitlines():
        header = re.match(r"@@ -(\d+)", line)
        if header:
            line_number = int(header.group(1))
        elif not line_number:
            continue
        elif line.startswith("---") or line.startswith("+++"):
            continue
        elif line[:1] == "-":
            removed_lines.append(line_number)
            removed_text.append(line[1:])
            line_number += 1
        elif line[:1] == "+":
            continue
        else:
            context_lines.append(line_number)
            line_number += 1
    return removed_lines, context_lines, removed_text


def authorship(rev, path, lines):
    out = jj(["file", "annotate", "-r", rev, "-T",
              'commit.change_id().shortest(8) ++ "\\n"', path])
    by_line = out.splitlines()
    return Counter(by_line[n - 1] for n in lines if 0 < n <= len(by_line))


def line_owners(rev, path):
    """(decisive, hint). A deleted line names its owner; context around an
    insertion only hints, since the last commit to touch a neighbouring line is
    often a later rename rather than the one whose feature the lines belong to."""
    removed_lines, context_lines, _ = hunks(rev, path)
    parent = f"{rev}-"
    return (authorship(parent, path, removed_lines) if removed_lines else Counter(),
            authorship(parent, path, context_lines) if context_lines else Counter())


def significant(line):
    stripped = line.strip()
    return len(stripped) > 3 and stripped not in ("});", "};", "}", ");")


def resolve(cid_counter, candidates):
    known = {cid: n for cid, n in cid_counter.items() if cid in candidates}
    if not known:
        return None
    top, count = max(known.items(), key=lambda kv: kv[1])
    if any(cid != top and n >= count for cid, n in known.items()):
        return None
    return top


def resurrected(status, target, deleted):
    """A path a branch commit deleted, that this handoff adds back."""
    return deleted.get(target) if status == "A" else None


def split_owner(rev, target, cut, by_cid):
    """The owner of a file whose content was cut out of a file this handoff edits."""
    content = {l.strip() for l in jj(["file", "show", "-r", rev, target]).splitlines()
               if significant(l)}
    for origin, lines in cut.items():
        shared = content & lines
        if len(shared) >= 3 and len(shared) >= len(content) / 2:
            owner = resolve(line_owners(rev, origin)[0], set(by_cid))
            if owner:
                return owner, f"split out of {origin}, whose removed lines are {owner}'s"
    return None, ""


def report(rev, root, commits, deleted):
    by_cid = {cid: description for cid, description, _ in commits}
    touches = {cid: paths for cid, _, paths in commits}
    depth = {cid: n for n, (cid, _, _) in enumerate(commits)}
    rows = handoff_files(rev)

    # An added file holding these lines is a split, not new work.
    cut = {}
    for status, source, target in rows:
        if status == "M":
            cut[target] = {l.strip() for l in hunks(rev, target)[2] if significant(l)}

    print(f"\n## {rev}  ({len(rows)} files)\n")
    groups, unresolved, new_commit = {}, [], []
    for status, source, target in rows:
        paths = [target] if source == target else [source, target]
        label = target if source == target else f"{source} => {target}"
        candidates = [cid for cid in by_cid if any(p in touches[cid] for p in paths)]
        print(f"{status}  {label}")
        for cid in candidates:
            print(f"     touched by {cid}  {by_cid[cid]}")

        owner, why = None, ""
        grave = resurrected(status, target, deleted)
        if not candidates or grave:
            owner, why = split_owner(rev, target, cut, by_cid)
            if not owner and grave:
                print(f"     -> RESURRECTED   ({grave} deleted this path; re-adding it"
                      " is yours to place)\n")
                continue
            if not owner:
                print("     -> NEW COMMIT   (new to the branch, and not cut out of a"
                      " file this handoff edits)\n")
                new_commit.append(target)
                continue
        elif len(candidates) == 1:
            owner, why = candidates[0], "only commit touching this path"
        elif status in ("R", "C"):
            owner = resolve(Counter({cid: 1 for cid in by_cid if source in touches[cid]}), set(by_cid))
            why = f"lineage of {source}"
        else:
            decisive, hint = line_owners(rev, target)
            owner = resolve(decisive, set(candidates))
            if owner:
                why = f"wrote {decisive[owner]} of the {sum(decisive.values())} lines this handoff removes"
            elif hint:
                shown = ", ".join(f"{cid} x{n}" for cid, n in hint.most_common(3))
                why = f"adds only; context last written by {shown}"

        if owner:
            print(f"     -> {owner}  {by_cid[owner]}   ({why})")
            groups.setdefault(owner, []).extend(paths)
        else:
            print(f"     -> AMBIGUOUS   ({why or 'no signal'})")
            unresolved.append((label, target, candidates))
        print()

    for label, target, candidates in unresolved:
        for cid in candidates:
            print(f"--- {cid} {by_cid[cid]}: its own diff of {target} ---")
            diff = jj(["diff", "--git", "-r", cid, target]).splitlines()
            print("\n".join(diff[:CANDIDATE_DIFF_LINES]))
            if len(diff) > CANDIDATE_DIFF_LINES:
                print(f"... {len(diff) - CANDIDATE_DIFF_LINES} more lines,"
                      f" see jj diff --git -r {cid} {target}")
            print()

    scaffolding = [t for _, _, t in rows if SCAFFOLDING.search(t)]
    if scaffolding:
        print(f"SCAFFOLDING, never squash these {len(scaffolding)} paths:")
        for path in scaffolding[:10]:
            print(f"  {path}")

    print("Draft commands, verify each target before running:\n")
    for cid in sorted(groups, key=lambda c: -depth[c]):
        paths = groups[cid]
        joined = " \\\n    ".join(sorted(set(paths)))
        print(f"jj squash --from {rev} --into {cid} -u -- \\\n    {joined}\n")
    if unresolved:
        print(f"{len(unresolved)} file(s) AMBIGUOUS above: decide from the diffs, then squash.\n")
    if new_commit:
        print(f"{len(new_commit)} file(s) have no owner on this branch; they need a new"
              " commit unless they belong with an AMBIGUOUS file above:")
        for path in new_commit:
            print(f"  {path}")
        print()

    if groups:
        radius = " | ".join(f"({cid})" for cid in groups)
        print("Blast radius:\n")
        print(jj(["log", "-r", f"({radius}):: & (working_copies() | bookmarks())", "--no-graph",
                  "-T", 'change_id.shortest(8) ++ "  " ++ bookmarks ++ " " ++ '
                        'working_copies ++ "  " ++ description.first_line() ++ "\\n"']))


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(f"{USAGE}\n\n{LEGEND}")
        return 0
    root = "trunk()"
    if "--root" in argv:
        index = argv.index("--root")
        root = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    if not argv:
        argv = parked()
        if not argv:
            print("Nothing parked: no handoff/* bookmark exists.")
            return 0
    commits, deleted = branch_commits(root, argv)
    if not commits:
        sys.exit(f"No commits in {root}..@; pass the branch root with --root.")
    print(f"{LEGEND}\n")
    print(f"Branch {root}..@, newest first, with how many paths each commit touches:\n")
    for cid, description, paths in commits:
        print(f"  {cid}  {description}   ({len(paths)} paths)")
    for rev in argv:
        report(rev, root, commits, deleted)
    return 0


def test():
    global jj
    diff = """diff --git a/src/unitInterior.ts b/src/unitInterior.ts
--- a/src/unitInterior.ts
+++ b/src/unitInterior.ts
@@ -10,5 +10,4 @@ export const group = {
   quality: "Q",
-  reconciliation: "R",
+  reconciliation: "moved",
   condition: "C1",
 };
"""
    jj = lambda args: diff
    removed, context, text = hunks("h", "src/unitInterior.ts")
    assert removed == [11], removed
    assert context == [10, 12, 13], context
    assert text == ['  reconciliation: "R",'], text

    assert resolve(Counter({"aaa": 4, "bbb": 1}), {"aaa", "bbb"}) == "aaa"
    assert resolve(Counter({"aaa": 2, "bbb": 2}), {"aaa", "bbb"}) is None
    assert resolve(Counter({"ccc": 9}), {"aaa"}) is None
    assert resolve(Counter({"ccc": 9, "aaa": 1}), {"aaa"}) == "aaa"
    assert significant('  reconciliation: "R",') and not significant("});")

    graves = {"src/old.ts": "wnmwlkzk"}
    assert resurrected("A", "src/old.ts", graves) == "wnmwlkzk"
    assert resurrected("M", "src/old.ts", graves) is None
    assert resurrected("A", "src/new.ts", graves) is None
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main(sys.argv[1:]))
