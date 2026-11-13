---
name: daniel-video-record
description: Record an MP4 in which a real mouse cursor clicks through the app on the shared /daniel-verify screen and shows a bug or a feature. Use when the user invokes /daniel-video-record, or asks for a video, a screen recording or a repro video of a bug, a ticket or a flow.
---

# /daniel-video-record

Input: what to record (a bug, a feature, a ticket, or a short flow), and
optionally the workspace root, the source session and the template. The
workspace defaults to `jj workspace root`. Use a workspace whose code has the
behavior: a bug that is on `main` needs a workspace on `main`.

Output: `<dir>/<slug>.mp4` with `<dir>` = `${TMPDIR:-/tmp}/video-record/<slug>/`,
so deleting a workspace cannot delete it. `<slug>` is the ticket id or a short
kebab-case name. H.264, `yuv420p`, `+faststart`, 1280 wide.

The scripts are in `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-video-record/`.
Below, `$video` is `video.sh` there and `$tab` is `node <that directory>/tab.mjs`.
Run either with no arguments for its usage.

## The rules of the shared screen

- **Your tab.** Every agent shares one Chrome. Drive your tab with `$tab` and
  its target id. The `chrome-devtools` MCP has one "selected page" for all
  agents, so a click through it can land in another agent's tab.
- **The lock.** The screen and the mouse are shared too. `$video try` and
  `$video record` hold `~/.cache/daniel-verify/screen.lock` and bring your tab
  to the front, its window sized to fill the screen. They are the only commands that move the real mouse or change
  the front tab. A call can wait up to 300 s for another agent's recording:
  set the Bash tool `timeout` to 600000.
- **Steps live in a file.** A hook blocks any Bash command whose text has
  `sleep <n>`, also as an xdotool argument or in a heredoc. Write each steps
  file with the Write tool. Shell `sleep`, `wait`, `timeout` and polling loops
  are blocked as well: `$tab wait`, `$tab waitjs`, `$tab pause` and xdotool
  `sleep` replace them.
- **Waits end early.** `$tab goto`, `wait` and `waitjs` give up after 15 s,
  and at once when the tab is on a login page. Pass a longer limit only for a
  load that `video.md` lists as slower. Never wait for text that you know will
  not show, to pass time: use `$tab pause`.
- **A new clone for each attempt that changes data.** An edit stays on the
  server, so a second take on the same clone starts from the wrong state.
  Change data only in a clone, never in the source session.

## 1. Set up

1. Run `/daniel-verify <workspace-root>` through its Setup steps 1 and 2. It
   starts or reuses the dev server, the display and Chrome, and prints the
   port and the path of the profile's `verify.md`. If another agent set the
   server up, do not run `verify.sh set-target`.
2. Run `$video setup`. It installs ffmpeg from apt, in noninteractive mode,
   when ffmpeg is missing or has no `x11grab` or `libx264`.
3. Read `video.md` beside the profile's `verify.md`, when it exists. It has
   the repo's clone commands, load times, cache windows and fixed screen
   coordinates.
4. `mkdir -p <dir>`.

Done when `$video setup` prints `Ready` and you know the port.

## 2. Open your tab on a clone

1. `$tab open <app-url>` prints your target id. The tab opens in the
   background, so it does not disturb a recording.
2. If the tab lands on a login page, log in as `verify.md` says.
3. Make every clone the run needs now, in one call: one for the probe, and
   one more for the take when the flow changes data. `$tab popup <id> <count>
   <target> ...` clicks the clone controls that `video.md` names and prints
   each clone's URL as soon as the app opens it, without a new tab. Without a
   `video.md`, follow the `verify.md` steps with `$tab goto`, `$tab wait` and
   `$tab click`.
4. `$tab goto` your tab to the probe clone. Open one more tab for each other
   clone, or keep its URL for later. Close the source session's tab with
   `$tab close`.

Done when `$tab list <clone-id>` prints one tab, and it is yours.

## 3. Probe

Do the flow once on the probe clone with `$tab` commands, without the real
mouse. Chain the commands of each page state in one Bash call with `&&`, so
a page costs one turn. Collect four things:

- **Proof.** Start `$tab listen <id> <dir>/probe.jsonl <seconds> [url-regex]`
  with `run_in_background`, with `<seconds>` about 60 s past what you expect
  the probe to take. It also stops when its tab closes. Then do the flow. The
  log has each XHR and fetch request with its body, each failed request and
  each console error, with `t` in seconds. Find the requests that prove the
  behavior, for example the write that carries the wrong value. A video of a
  behavior you cannot prove in the log is a guess.
- **Targets.** For each click, a target that `$tab click` accepts: a CSS
  selector, or `text=<exact text or aria-label>`.
- **Screen coordinates.** `$tab point <id> <target> [target ...]` prints the
  screen `x,y` of each target for xdotool: the CSS rect plus the viewport
  offset, times the device pixel ratio. Measure all targets of one page state
  in one call, in the state in which the video clicks them: coordinates
  change after a navigation and after a scroll. Do not use a point with
  `inViewport: false` or `covered: true`. `point` refuses a tab that was
  never in front, because its offset reads 0: run `$video front <id>` once.
- **Timings.** `$tab goto <id> <url> <target>` and `$tab wait <id> <target>`
  print how long the target took to show. Wait for the marker that shows the
  page is ready, and take it from `video.md` when it lists one. Time every
  page load and every calculation that the video waits for. If the behavior
  depends on a time window, write down which request starts it and how long
  it lasts.

`$tab click` scrolls its target into view, which a viewer's mouse does not
do. Find the real wheel count with one `$video try` on a steps file that
holds only the scroll: `mousemove X Y click --repeat <n> --delay 100 5`. The
page stays scrolled, so `$tab point` then gives the coordinates for that
state.

Do not run a `$video try` per coordinate or per shot, and do not walk the
flow again with the real mouse before the take. The take is the rehearsal:
step 6 checks its frames, and a miss costs one retake on the spare clone.

Done when the log proves the behavior, and you have a coordinate and a
timing for every step. If the behavior did not happen, stop and report what
the log shows instead.

## 4. Write the steps file

An xdotool script, written with the Write tool to `<dir>/<slug>.steps`. Each
`# label` line becomes a timeline entry.

```
# Open Settings from the sidebar
mousemove 24 576 sleep 1 click 1 sleep 7
# Scroll down to the Billing section
mousemove 1000 650 sleep 0.3 click --repeat 13 --delay 100 5 sleep 1
# Change the plan to Pro
mousemove 680 875 sleep 1 click 1 sleep 1
mousemove 727 946 sleep 1 click 1 sleep 2
# Reload: the plan is still Free
mousemove 95 62 sleep 1 click 1 sleep 26
# The plan after the reload
mousemove 690 875
```

- Move like a person: `mousemove X Y sleep 1 click 1`. The viewer follows
  the cursor to the target before the click.
- After each click, `sleep` for the measured time plus a margin of about
  20%. Inside a time window, keep the margins small and check the total with
  `$video timeline`.
- Scroll with the wheel: button 5 is down, 4 is up. Point the mouse at the
  area that scrolls first.
- `shot <name> <target> [| <target> ...]` saves a sharp 2x crop of the
  smallest box around the targets, plus 8 px, to `<dir>/<slug>-shots/<name>.png`.
  It runs beside the steps and does not pause them. Chrome draws the crop, so
  the screen, the video and the real cursor stay out of it. Put it after the
  `sleep` that lets the value settle. Each target must be fully in the
  viewport. Name inline targets: a block element spans the full width.
  Step 6 checks them.
- Start with a step that closes any browser bubble or infobar over the
  page, such as the one `video.md` lists, when it can show.
- `type --delay 80 '<text>'` types text. Add a `sleep` for its length after
  it: the timeline does not count typing.
- End with a `mousemove` onto the value that shows the result. The recording
  runs 5 s past the last step, so the last frames rest on it.
- End with a full reload when it proves that the server kept the value. The
  reload button is browser UI, at about `95,62` in the shared Chrome.
- Start the flow from the state that keeps it short and inside any time
  window, for example a page that has already loaded.

`$video timeline <steps>` prints the mm:ss of each label and the length. The
limit is 280 s: record a longer flow in parts.

## 5. Record

Each take needs the starting state again: use the spare clone from step 2
when the probe changed data, and bring its tab to the page where the steps
start. Then, with the Bash `timeout` at 600000:

```
"$video" record <target-id> <dir>/<slug>.steps <dir>/<slug>.mp4
```

It takes the lock, activates your tab, runs the steps as one xdotool chain in
the background, and runs ffmpeg in the foreground for the timeline length. It
writes `<dir>/<slug>.events.jsonl` and prints the timeline.

## 6. Check

1. `$video frames <dir>/<slug>.mp4 [second ...]` saves PNG frames. Take one
   frame 1 to 2 s after each timeline label, and the last second.
2. Open every frame, every PNG in `<dir>/<slug>-shots/` and
   `<dir>/<slug>.events.jsonl` with the Read tool, all in one message. Each
   click landed, each page had loaded, and the last frames show the result.
   `record` prints one line per shot, or the reason it failed. The proof
   requests from the probe are in the events log, with the same values. `t`
   is the video time, within about 1 s.

If a click missed or a page was still loading, fix the coordinates or the
pauses and go back to step 5 with a new clone. Make it with `$tab popup`
while you fix the steps file.

Report only what the frames show. If the behavior happened in the log but
not on screen, or did not happen at all, say that in the first line of the
report, with what the screen shows instead, and name what you would need to
record a real symptom. Never title such a video as a repro.

Done when every frame matches its timeline label, or you reported the
difference.

## 7. Stop and report

Close your tabs with `$tab close` first: that also ends any `$tab listen`
still running in the background. Leave Chrome and the display running. For
the dev server, follow the Stop section of `/daniel-verify`: stop it only if
you started it.

Then report:

- The MP4 path, its length, the shots folder, and the timeline (mm:ss → what the user does or
  sees).
- The clone ids: which one the probe used and which one the video used.
- Whether the behavior showed on screen and in the log.
- Console errors and failed requests from the events log. Mark the ones that
  `verify.md` lists as known. Write "None" when a list is empty.

## Several recordings

Run the setup once yourself (step 1). Write one shared context file in your
scratchpad: the goal, the root cause and the requests that prove each
behavior, the workspace, the port, the source session, and `<dir>`. Then
start one agent per recording. Each brief names its one recording, the
context file and this skill, and says: the dev server is running, do not
stop it, do not run `set-target`.

The agents share the dev server. Each has its own tab and its own clones.
The lock makes them record one after the other. Stop the dev server yourself
after the last agent reports.
