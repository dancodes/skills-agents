---
name: daniel-proof
description: Take sharp screenshots that prove each claim of a feature on a local TrueTracts session, saved as PNG files in the repo's tmp/ folder with a manifest. Uploading them anywhere is out of scope.
disable-model-invocation: true
---

# /daniel-proof

Input: the claims to prove (pasted text, a Linear ticket, or a feature description) and a session URL on the local dev server, on whatever port it runs (`http://localhost:<port>/...`). Output: one PNG per shot plus `shots.md` in `<dir>` = `${TMPDIR:-/tmp}/proof-shots/<slug>/`, the OS temp folder, so parking or deleting a workspace cannot delete them. Create it and `<root>/tmp/proof-capture/` with `mkdir -p` first. `<root>` is the root of the repo or jj workspace you run in (`jj root`, else `git rev-parse --show-toplevel`). `<slug>` is the ticket id, or a short kebab-case name for the feature.

## 1. Write the shot list

Turn every claim into one or more shots. A shot names:
- an id (`1a`, `1b`, `2a`: the number is the claim, the letter the shot)
- a title: one sentence stating what the shot proves, with the exact values it shows
- where it lives: the step, the panel and the region
- the labels and numbers that must be visible for the shot to count as proof
- the context each must-see value needs to read correctly, such as its row label, column header or field name

Each shot proves one point, so it shows only its must-see values and their context. Split a claim into more shots before you widen one.

Cover both sides of each claim. For a claim "X is not adjusted but Y is", show X at 0 or missing and Y priced, and show the grid as well as the drawer. Done when every claim has at least one shot and every shot names its must-see values.

## 2. Check the browser

Captures go through the `chrome-devtools` MCP. It connects to a Chrome listening on `127.0.0.1:9222`, not the Claude in Chrome browser.
- Call `list_pages`. If it can't connect, start the shared display and Chrome with `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-verify/verify.sh start <root>`, as /daniel-verify does. It also starts or reuses the dev server and prints its URL. Use that port when the input gave none.
- If `list_pages` connects but reports no page, open the session with `new_page`.
- If the page lands on an `auth.` login URL, stop. Ask the user to log into TrueTracts in that window, and wait for their reply. The profile keeps the login for next time.

## 3. Capture, in one subagent

Hand the shot list to one general-purpose subagent. It is the only one, because there is one browser. Its brief:

- Read only: never edit values, delete comps, or trigger dialogs. Opening the Adjustments drawer and pressing "Finish and View Grid" are fine.
- Run `emulate` with viewport `1600x1000x2` once per page. A capture is then 3200 x 2000 with sharp text.
- After each navigate, wait until more than the app shell renders. The dev server can take 20 to 40 s.
- Crop each shot to the smallest box that holds its must-see values and their context. Never capture a whole panel, drawer or page when a part of it proves the point. Never cut a must-see value, its label or its header.
- For each shot, scroll the region into view. Then capture it one of two ways:
  - Element capture: `take_screenshot` with a `uid` from `take_snapshot` and `filePath` set to `<root>/tmp/proof-capture/<id>.png`, then move it to `<dir>/<id>.png`. Use it only when the smallest node that holds everything adds no other UI.
  - Crop: otherwise, take the viewport to `<root>/tmp/proof-capture/<id>-full.png`. With `evaluate_script`, read the `getBoundingClientRect` of each must-see element and its label, and take the union box. Add about 8 px of margin, multiply by 2 for device pixels, and crop with `python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-proof/crop.py <root>/tmp/proof-capture/<id>-full.png <dir>/<id>.png <x*2> <y*2> <w*2> <h*2>`. It uses only the Python standard library, so it runs on Linux and macOS. Delete the `-full` file.
  - When the must-see parts are far apart, such as a row label and a value ten columns away, hide the rows or columns between them with `display:none` so the box stays small, as long as what remains still reads honestly. Remove those styles afterwards.
- Open each PNG with the Read tool. Every must-see label and number has to be legible and match the claim.
- If the UI contradicts a claim, still save the shot as `<dir>/<id>-contradicts.png`. Report exactly what the UI says, and never title it as proof.
- Report per shot: the file, the values it visibly shows, and any contradiction.

`take_screenshot` only writes inside the workspace root, so it refuses `<dir>`. That is why each capture lands in `<root>/tmp/proof-capture/` first and moves to `<dir>` at once. Keep `tmp/` out of commits with `.git/info/exclude`. If `take_screenshot` refuses `<root>/tmp/`, capture under the root it accepts, and say so in the report. Never leave a shot only in `<root>`.

## 4. Check and record

Open every PNG yourself with the Read tool. Retake any shot that is blurry, cut off, missing a must-see value, or shows UI that the shot does not need. Then write `shots.md` in the same folder, one section per shot in id order:

```markdown
## 1a. <title>
![1a](1a.png)
Shows: <the exact values visible>
```

Done when every shot in the list has a legible PNG and a `shots.md` entry, and every contradiction is reported. Report the folder path and the contradictions to the user.
