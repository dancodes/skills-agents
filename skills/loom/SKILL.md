---
name: loom
description: Turn a Loom recording into a Markdown file with metadata, the timed transcript, a frame and an on-screen description per section, comments and reactions. Use when the user shares a loom.com link, asks for a Loom transcript, notes or summary, or invokes /loom.
---

# /loom

`loom.py` sits next to this file: `"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/loom/loom.py"`.
It takes any Loom link (share, embed, with or without a query string).

## Steps

1. **Fetch.** Run `loom.py "<url>"`. Add `--out <dir>` when the user names a
   place; otherwise it writes to `~/Documents/loom/<slug>-<id>/`. It prints
   the Markdown path and the frame count. When it exits with `PRIVATE:`, run
   the Chrome fallback below instead, then continue at step 2.
2. **Describe every frame.** Read each image the Markdown embeds. Under the
   image, add one `**On screen:**` paragraph: the app and page, the field
   names and values shown, any error or flag, and what the speaker points at.
   Keep the transcript verbatim: the captions are machine-made, so put each
   correction the frame proves in the On screen paragraph (`"five eight
   eighty" is the 5,880 Sq. Ft. Total Site Size`). Done when every section
   with a frame has its On screen paragraph.
3. **Write the overview.** Insert `## Overview` after the metadata list: two
   or three sentences on what the recording shows, then `Key points`, then
   `Problems shown` and `Action items` when the recording has any. Start
   every item with its timestamp.
4. **Reply** with the Markdown's absolute path and the overview.

## Chrome fallback

For a video that needs a Loom login. The user's Chrome is signed in to Loom.

1. Load the claude-in-chrome tools, open `https://www.loom.com/share/<id>` in
   a new tab and take a screenshot. A sign-in or request-access page means
   the user has no access: stop and say so.
2. Run the output of `loom.py "<url>" --browser-js` with `javascript_tool`. It
   replaces the page with the video's JSON. Read it with `get_page_text` and
   write the JSON after the `---` line to the scratchpad as `loom-<id>.json`.
3. Run `loom.py "<url>" --from-json <file>`. This Markdown has no frames.
4. Reload the share page. For each `###` section, seek a few seconds past its
   timestamp with `document.querySelector('video').currentTime = <seconds>`
   and take a screenshot. Step 2 then describes these screenshots in place of
   frames.
