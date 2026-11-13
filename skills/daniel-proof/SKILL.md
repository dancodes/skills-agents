---
name: daniel-proof
description: Prove each claim of a feature on a local app session with one explained video and sharp cropped screenshots taken during the recording, by chaining /daniel-verify, /daniel-video-record and /daniel-video-annotate.
disable-model-invocation: true
---

# /daniel-proof

Input: the claims to prove (pasted text, a Linear ticket, or a feature description), and optionally the workspace root and the source session. Output, all in the `<dir>` that /daniel-video-record sets:
- `<slug>-explained.mp4`, the video that /daniel-video-annotate writes
- `<slug>-shots/<id>.png`, one sharp crop per shot, taken during the recording
- `<slug>-shots/shots.md`, the manifest

Each step below runs one of the three skills. Read that skill and follow it, with the changes listed here.

## 1. Start everything in one turn

In one message:
- Settle the reading speed: step 0 of /daniel-video-annotate, the speed the user gave, else 350 wpm.
- Start the dev server: /daniel-verify Setup step 1, `"$verify" start <workspace-root>`.
- Read the SKILL.md of /daniel-verify, /daniel-video-record and /daniel-video-annotate, and the profile's `verify.md` and `video.md`, all with parallel Read calls.

Done when you have a reading speed or a fixed hold, and the server is up.

## 2. Write the shot list

Turn every claim into one or more shots. A shot names:
- an id (`1a`, `1b`, `2a`: the number is the claim, the letter the shot)
- a title: one sentence stating what the shot proves, with the exact values it shows
- where it lives: the page, the panel and the region
- the labels and numbers that must be visible for the shot to count as proof
- the context each must-see value needs to read correctly, such as its row label, column header or field name

Each shot proves one point, so it shows only its must-see values and their context. Split a claim into more shots before you widen one.

Cover both sides of each claim. For a claim "X is not adjusted but Y is", show X at 0 or missing and Y priced, and show the table as well as the detail panel.

Done when every claim has at least one shot and every shot names its must-see values.

## 3. Check in the browser

Run /daniel-verify: the rest of its Setup, then its "Checking a change" on the screens of every shot. Look at each shot in your own tab, read only: never edit values, delete records, or trigger dialogs on the source session.

If the UI contradicts a claim, keep the shot, rename its id to `<id>-contradicts`, and note exactly what the UI shows.

Done when every shot is confirmed or marked as a contradiction.

## 4. Record, with the shots

Run /daniel-video-record for one flow that passes every shot in id order. The dev server from step 3 is running: skip its step 1.1 and do not run `set-target`.

- Make the clones in step 2 of /daniel-video-record in one call: three when the flow changes data (the probe, the shot take and the clean take), else one for all.
- In the probe, find the targets of each shot: the must-see values and their labels, as inline elements. Find the request that proves each shot, when one exists.
- In the steps file, at each shot, rest the cursor on the must-see value and add a `shot <id> <targets>` line after the value settles.
- Record the shot take with `$video record`. Chrome flashes each crop on the screen while it draws it, so this take gives the crops and is the rehearsal, but it is not the video. Check its frames and crops in one batch of Reads. Fix the steps file when a click missed, or when a crop is cut off, misses a must-see value or its label, or holds UI the shot does not need. When the targets are far apart, such as a row label and a value ten columns away, split the shot in two.
- Record the clean take on the next clone, with the same steps file minus the `shot` lines. The pauses then match the shot take, second for second.
- When the flow passes the 280 s limit, record one video per claim.

Done when the frames of the clean take show every shot, and every crop from the shot take is legible.

## 5. Write the manifest

Use the crops you read in step 4; do not open them again. Every must-see label and number has to be legible and match the claim. Then write `shots.md` in that folder, one section per shot in id order:

```markdown
## 1a. <title>
![1a](1a.png)
Shows: <the exact values visible>
```

A contradicting shot gets the title "Contradicts claim <n>" and states what the UI shows.

Done when every shot has a legible PNG and a `shots.md` entry.

## 6. Annotate

Run /daniel-video-annotate on each recording, with the reading speed or hold from step 1 and the shot list as the source. Skip its step 0.

- Pause at least once per shot, on its must-see value, and box that value.
- Start each caption with the shot id, and name the exact values the frame shows. A contradicting shot's caption states what the UI shows and never calls it proof.

Done when its step 6 check passes for every pause.

## 7. Report

Per video: the explained MP4 path, its size and duration. The shots folder and `shots.md`. Per shot: the values the crop shows, and the request that proves it. Then the contradictions, the inferred captions, and the console errors and failed requests from the events log. Write "None" when a list is empty.

Stop the dev server as the Stop section of /daniel-verify says.
