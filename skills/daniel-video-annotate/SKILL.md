---
name: daniel-video-annotate
description: Turn a screen recording into an explained version by cutting the still waits, pausing at each key action, boxing the control and captioning what is done and why. Use when the user invokes /daniel-video-annotate, or asks to annotate or explain a video.
---

# /daniel-video-annotate

Input: a video file, plus whatever says why each step is taken (a ticket, a merge request, the user's message). Output, beside the input: `<name>-trimmed.mp4` and `<name>-explained.mp4`. The input file is never changed.

The explained video plays the recording, and at each pause it holds one frame for the hold time, dims the screen around one boxed control, and shows a one-sentence caption in a black strip below or above the recording. The strip makes the video taller, so the recording is never covered.

`annotate.py` sits next to this file. In the commands below, `A` stands for `python3 "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-video-annotate/annotate.py"`. It needs only `ffmpeg`, `ffprobe` and the Python standard library. `<work>` is a scratch folder: the session scratchpad when there is one, else `${TMPDIR:-/tmp}/video-annotate/<name>/`.

If the video is on the dev VM, copy it down first with `dvm get <remote path> <local dir>`.

## 0. Choose the reading speed

The hold is how long each caption stays readable on screen. Each pause holds 1.5 s plus the time to read its caption at the reading speed, and at least 2.5 s. Use the speed in words per minute that the user gave, else 350 wpm. Do not ask. When the user gave a fixed hold in seconds, use it for every pause instead.

Done when you have a reading speed or a fixed hold.

## 1. Cut the waits

```
A trim <video> <name>-trimmed.mp4
```

It finds every stretch where the picture stays still for 1.5 s or more, keeps the first second of each, and cuts the rest. It prints the number of stretches and the duration before and after. Skip this step when the user wants the waits kept, and use the original as `<trimmed>` below.

Every time in the later steps is a time in `<trimmed>`. Trimming again moves every time, so redo steps 2 to 6 after any new trim.

## 2. Learn the story

```
A sheets <trimmed> <work>/sheets
```

It writes contact sheets of six frames each, one frame per second, with the exact time burned into each frame. Read every sheet. Read the ticket or other source for the reason behind each step.

Done when you can say, in order, what the person does on screen, which value each action sets, and what result proves the point of the recording.

## 3. Choose the pauses

Pause once for each choice (a value picked, a button pressed, a page opened on purpose) and once for each result that proves the point. Skip navigation that carries no decision.

For each pause, find the frame and the box:

```
A frames <trimmed> <work>/frames 23.0 23.2 23.4 23.6
```

It writes one full-size PNG per time, named by its exact time, with a red grid every 100 px and the pixel coordinates labelled along the top and left edges.

- Pick a settled frame. Recordings contain half-rendered frames, such as a panel that is blank for a few frames after a click. Step through at 0.2 s until the control and its surroundings are fully drawn.
- For a choice from a list, prefer the frame where the list is open and the cursor is on the option. If that frame is half-rendered, use the frame just after, where the field shows the new value.
- Read the box as `[x, y, width, height]` from the grid labels, in source pixels. The Read tool shrinks large images, so positions measured on the displayed image are wrong; the labels stay right.
- Box the single control that the caption talks about, with a few pixels of margin. A pause may leave `box` out, and then nothing is dimmed.

Done when every pause has a time whose frame you have looked at, and a box read from that same frame.

## 4. Write the captions

One sentence per pause. It says what we do and why, or what the screen now shows and why. Name the concrete thing: the row, the field, the old value and the new value.

Take the "why" from the source. When the source does not give the reason for a step, write what is visible, and list that caption as inferred in the report. Apply the `writing-tics` skill to the captions. Keep each under about 180 characters, because the strip is as tall as the longest caption.

## 5. Render

Write `<work>/spec.json`, a list in time order:

```json
[
  {"at": 12.0, "box": [399, 569, 180, 29], "caption": "We change Item 1's Size from M to L in the table, which saves L to the server."},
  {"at": 23.6, "box": [659, 500, 192, 24], "caption": "..."}
]
```

`at` is seconds in `<trimmed>`. Then set `hold` on every pause:

```
A holds <work>/spec.json [--wpm <speed>]
```

It writes the hold of each pause into the spec and prints it beside the word count. With a fixed hold, set `hold` on every pause yourself. A pause without `hold` holds 6 seconds.

```
A annotate <trimmed> <work>/spec.json <name>-explained.mp4 [--position top|bottom] [--clearance <lines>]
```

The caption strip goes where the user asked. With no request, it goes at the bottom.

- `--position bottom` is the default. Video players draw their controls over the bottom edge, so the strip gets empty space under the caption: `--clearance` lines of it, 3 by default, which clears the controls of a small embedded player.
- `--position top` puts the strip above the recording, where no player draws controls. It takes no clearance.

Boxes stay in the coordinates of `<trimmed>` for both positions.

## 6. Check every pause

```
A check <name>-explained.mp4 <work>/spec.json <work>/check
```

It writes one frame from the middle of each pause. Read every one. The box must sit on the control, the caption must be whole and not cut at the right edge, and the frame must be the settled one you chose. Fix the spec and render again until every pause passes.

## 7. Report

Give the path, the size and the duration of the explained video, then the captions in order, each with the control it boxes. Say which captions are inferred. Say that you checked one frame per pause and did not watch the playback.

## Limits

- The output has no audio. Tell the user when the input had a voice track.
- The frame rate is the input's average rate, rounded and held between 5 and 30 frames per second.
- `trim` only cuts a picture that is fully still. A spinner, a progress bar, a blinking cursor or a clock keeps the picture moving, so those waits stay. A wait broken by one small change is kept as several one-second pieces.
- `trim` only cuts frames inside a still stretch, and it keeps the first frame of every change. A change smaller than the `--noise` tolerance (default 0.003), such as one small character, counts as still and can be cut. Step 2 is the check: every action must appear in the sheets. Lower `--noise` to 0.001 when one is missing.

## Errors

| What you see | Cause | Fix |
|---|---|---|
| `this ffmpeg build has no drawtext filter` | ffmpeg was built without libfreetype | Install a full build, such as `brew install ffmpeg` |
| `no font file found` | None of the known macOS or Linux font paths exist | Pass `--font /path/to/font.ttf` to `sheets`, `frames` and `annotate` |
| `Unrecognized option 'fps_mode'` | ffmpeg is older than 5.1 | Upgrade ffmpeg |
| `no still stretches found, nothing written` | The picture never stays still for 1.5 s | Use the original as `<trimmed>`, or lower `--min-freeze` |
| The trimmed video still feels slow | Animated waits were kept, or one second per still stretch adds up | Lower `--keep` to 0.5 |
| The trimmed video jumps too fast to follow | One second per screen is too short for this recording | Raise `--keep` to 2 and `--min-freeze` to 3 |
| `pause N at Ts is past the end of the video` | The times came from the original and not from `<trimmed>` | Read the times again from `sheets` and `frames` of `<trimmed>` |
| `pause N box ... is outside the frame`, or the box misses the control in `check` | The box was measured on a shrunken image | Read it from the grid labels of the `frames` PNG |
| The caption is cut at the right edge | The font is wider than the script assumes | Pass `--wrap 80`, or a lower number, to `annotate` |
| The player's controls cover the caption | The space under the caption is shorter than the controls | Raise `--clearance` to 5, or pass `--position top` |
| `pause N would sit at ..., past the end` | `check` was given the trimmed video | Give it the explained video |
| Any other `ffmpeg failed` | Unknown | Run `A selftest`. It trims and annotates a generated clip, so a pass means ffmpeg works and the input or the spec is at fault |
| `dvm get --help` fails with an scp error | `dvm get` passes every argument to scp | Run `dvm help` |

macOS has no `timeout` command. A one-minute 720p video renders in a few seconds, so run the commands plainly.
