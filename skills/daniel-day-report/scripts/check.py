import argparse
import json
import os
import re
import subprocess
import sys

from common import day_dir, load_profile, resolve_day

VIEWS = ["day", "waste", "tasks", "open", "fixes"]
MUST_FILL = {"day": ["kpis", "tl", "ws", "cols"], "waste": ["bTheme", "fBody"], "tasks": ["psBody"], "open": ["openBody"], "fixes": ["fxBody"]}

PRE = """<script>
window.__errs = [];
window.addEventListener("error", e => __errs.push(String(e.message)));
const __ce = console.error; console.error = (...a) => { __errs.push(a.join(" ")); __ce(...a); };
</script>
"""

POST = """<script>
setTimeout(() => {
  const out = { mode: "%MODE%", width: innerWidth, views: {} };
  if ("%MODE%" === "dark") document.querySelector('[data-mode="dark"]').click();
  for (const v of %VIEWS%) {
    document.querySelector(`[data-view="${v}"]`).click();
    window.dispatchEvent(new Event("resize"));
    const sec = document.getElementById("v-" + v);
    const empty = (%FILL%[v] || []).filter(id => !document.getElementById(id) || !document.getElementById(id).innerHTML.trim());
    const wide = [...sec.querySelectorAll(".card")].filter(c => c.scrollWidth > c.clientWidth + 2 && !c.querySelector("table")).map(c => (c.querySelector(".pane-h") || c).textContent.trim().slice(0, 40));
    out.views[v] = { empty, wide, pageOverflow: document.documentElement.scrollWidth > innerWidth + 1 };
  }
  out.errors = window.__errs;
  const pre = document.createElement("pre"); pre.id = "__check"; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
}, 600);
</script>
"""

DARK = """<script>document.querySelector('[data-mode="dark"]').click();</script>
"""


def chrome_path(profile):
    path = os.path.expanduser(profile.get("chrome", ""))
    if path and os.path.exists(path):
        return path
    sys.exit(f"No headless Chrome at '{path}'. Set 'chrome' in the day-report profile.")


def run_chrome(chrome, args):
    base = [chrome, "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", nargs="?", default="today")
    args = ap.parse_args()
    profile = load_profile()
    day = resolve_day(args.day, profile["tz"])
    page_dir = os.path.join(day_dir(profile, day), "page")
    chrome = chrome_path(profile)
    page = open(os.path.join(page_dir, "index.html")).read()
    shots = os.path.join(page_dir, "shots")
    os.makedirs(shots, exist_ok=True)
    problems = []
    for mode in ("light", "dark"):
        post = POST.replace("%MODE%", mode).replace("%VIEWS%", json.dumps(VIEWS)).replace("%FILL%", json.dumps(MUST_FILL))
        probe = os.path.join(page_dir, f"check-{mode}.html")
        open(probe, "w").write(PRE + page + post)
        for width in (1280, 390):
            dom = run_chrome(chrome, [f"--window-size={width},900", "--dump-dom", "file://" + probe]).stdout
            m = re.search(r'<pre id="__check">(.*?)</pre>', dom, re.S)
            if not m:
                problems.append(f"{mode} {width}px: the check did not run")
                continue
            res = json.loads(m.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))
            for e in res["errors"]:
                problems.append(f"{mode} {width}px: JS error: {e}")
            for v, r in res["views"].items():
                if r["empty"]:
                    problems.append(f"{mode} {width}px {v}: empty {', '.join(r['empty'])}")
                if r["wide"]:
                    problems.append(f"{mode} {width}px {v}: content wider than its card: {r['wide']}")
                if r["pageOverflow"]:
                    problems.append(f"{mode} {width}px {v}: page scrolls sideways")
        shot = os.path.join(page_dir, f"shot-{mode}.html")
        open(shot, "w").write(page + (DARK if mode == "dark" else ""))
        for v in VIEWS if mode == "light" else ["day", "waste"]:
            run_chrome(chrome, ["--window-size=1280,900", f"--screenshot={shots}/{mode}-{v}.png", f"file://{shot}#{v}"])
        if mode == "light":
            run_chrome(chrome, ["--window-size=390,900", f"--screenshot={shots}/phone-day.png", f"file://{shot}#day"])
        os.remove(probe)
        os.remove(shot)
    print(f"screenshots: {shots}")
    for p in sorted(set(problems)):
        print("PROBLEM", p)
    print("PASS" if not problems else f"FAIL: {len(set(problems))} problems")


if __name__ == "__main__":
    main()
