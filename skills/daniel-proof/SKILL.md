---
name: daniel-proof
description: Take sharp screenshots that prove each claim of a feature on a local TrueTracts session, saved as PNG files in the repo's tmp/ folder with a manifest. Uploading them anywhere is out of scope.
disable-model-invocation: true
---

# /daniel-proof

Input: the claims to prove (pasted text, a Linear ticket, or a feature description) and a session URL on `http://localhost:8888`. Output: one PNG per shot plus `shots.md` in `/Users/dan/code/tf/neighbourhoods/tmp/proof-shots/<slug>/`. `<slug>` is the ticket id, or a short kebab-case name for the feature.

## 1. Write the shot list

Turn every claim into one or more shots. A shot names:
- an id (`1a`, `1b`, `2a`: the number is the claim, the letter the shot)
- a title: one sentence stating what the shot proves, with the exact values it shows
- where it lives: the step, the panel and the region
- the labels and numbers that must be visible for the shot to count as proof

Cover both sides of each claim. For a claim "X is not adjusted but Y is", show X at 0 or missing and Y priced, and show the grid as well as the drawer. Done when every claim has at least one shot and every shot names its must-see values.

## 2. Check the browser

Captures go through the `chrome-devtools` MCP. It connects to a Chrome listening on `127.0.0.1:9222`, not the Claude in Chrome browser.
- Call `list_pages`. If it can't connect, run `open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir=$HOME/.chrome-debug-profile` and wait until `lsof -nP -iTCP:9222 -sTCP:LISTEN` shows Chrome.
- If `list_pages` connects but reports no page, open the session with `new_page`.
- If the page lands on an `auth.` login URL, stop. Ask the user to log into TrueTracts in that window, and wait for their reply. The profile keeps the login for next time.

## 3. Capture, in one subagent

Hand the shot list to one general-purpose subagent. It is the only one, because there is one browser. Its brief:

- Read only: never edit values, delete comps, or trigger dialogs. Opening the Adjustments drawer and pressing "Finish and View Grid" are fine.
- Run `emulate` with viewport `1600x1000x2` once per page. A capture is then 3200 x 2000 with sharp text.
- After each navigate, wait until more than the app shell renders. The dev server can take 20 to 40 s.
- For each shot, scroll the region into view. Then capture it one of two ways:
  - Element capture: `take_screenshot` with the region's `uid` from `take_snapshot` and `filePath` set to `<dir>/<id>.png`.
  - Crop: when the region has no single node, take the viewport to `<dir>/<id>-full.png` and read its box with `evaluate_script` (`getBoundingClientRect`). Then crop with `sips -c <h*2> <w*2> --cropOffset <y*2> <x*2> <id>-full.png --out <id>.png`, adding about 16 px of margin, and delete the `-full` file.
  - To fit a tall region, hide unrelated parts (photos, other panels) with `display:none`, as long as what remains still reads honestly. Remove those styles afterwards.
- Open each PNG with the Read tool. Every must-see label and number has to be legible and match the claim.
- If the UI contradicts a claim, still save the shot as `<id>-contradicts.png`. Report exactly what the UI says, and never title it as proof.
- Report per shot: the file, the values it visibly shows, and any contradiction.

`take_screenshot` only writes inside the workspace root, so `/tmp` is refused. That is why shots go to the repo's `tmp/`, which `.git/info/exclude` keeps out of commits.

## 4. Check and record

Open every PNG yourself with the Read tool. Retake any shot that is blurry, cut off, or missing a must-see value. Then write `shots.md` in the same folder, one section per shot in id order:

```markdown
## 1a. <title>
![1a](1a.png)
Shows: <the exact values visible>
```

Done when every shot in the list has a legible PNG and a `shots.md` entry, and every contradiction is reported. Report the folder path and the contradictions to the user.
