---
name: daniel-verify
description: Run a jj workspace's dev server from its private repo profile, open it in a shared Chrome, prepare a test target, and check frontend changes in the browser. Use when the user invokes /daniel-verify, or when the /daniel orchestrator hands you a verify port and target URL.
---

# /daniel-verify

Input: `/daniel-verify [workspace-root] [template]`. The workspace root
defaults to `jj workspace root`. The template defaults to the first one that
`verify.sh templates` prints.

The script is `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/daniel-verify/verify.sh`.
Below it is `$verify`.

## What runs where

- Repo profile: `${SKILLS_AGENTS_PRIVATE:-$HOME/.config/skills-agents}/repos/<name>/`,
  matched to the workspace by `repo-profile.sh`. `verify.sh` there gives the
  ports, env file, health path and dev server command. `verify.md` there gives
  the login, the templates, how to prepare a target, and the routes. Without a
  profile, this skill cannot run: say so and stop.
- Dev server: one per workspace, on the first free port of the profile's pool.
- Display: Xvnc `:50`, shared. VNC is a unix socket only, mode 600.
- Browser: one Chrome with `--remote-debugging-port=9222`, shared. The
  `chrome-devtools` MCP connects to it. The profile keeps logins.
- Secrets: the profile's env file. The script exports it into the dev
  server's environment. Never copy it into a workspace or print it.
- State: `~/.cache/daniel-verify/state/<port>.json` has the workspace,
  profile, port, PID, `started_at`, log, template and target URL.

## Setup

1. Start, or reuse, the dev server, display and Chrome:
   ```
   "$verify" start <workspace-root>
   ```
   It prints the state entry, the app URL and the path of the profile's
   `verify.md`. It stops with an error if the env file still has
   `REPLACE_ME`, or if all ports are in use. Relay either error to Daniel and
   stop. Do not wait for a port.

   If the entry already has a `target_url`, setup is done. Use that target.
2. Read the profile's `verify.md`.
3. Open a new tab with `new_page` at the app URL. Always work in your own tab.
   Other agents share this browser.
4. Log in as `verify.md` says.
5. Prepare the target from the template as `verify.md` says, then record it:
   ```
   "$verify" set-target <workspace-root> <template> <target-url>
   ```

## Checking a change

Edits reload through HMR. You do not restart the server.

For each changed screen:
1. Take a screenshot with `take_screenshot` and `filePath` set to your
   scratchpad.
2. Read errors with `list_console_messages`.
3. Read failed requests with `list_network_requests`. Check `verify.md` for
   known causes before you report them.

Report the port, the target URL, the screenshot paths, console errors and
failed requests. Write "None" when a list is empty.

## Stop

You stop what you started. Never give Daniel a `verify.sh stop` command.

- Called by /daniel: end with `Dev server on :<port>, target <url>.` The
  park script stops it when it deletes the workspace.
- Called by Daniel directly: run `"$verify" stop <port>` when you finish,
  unless he says to keep it.
- `"$verify" stop --gone` stops every server whose workspace folder is gone.

Other commands:
- `"$verify" list` shows every entry, alive or dead, with its start time.
- `"$verify" stop --all` also stops Chrome and Xvnc.

`start` deletes entries whose PID is dead and stops servers whose workspace
folder is gone. It lists entries that are older than 24h but does not stop
them.

## Watching from another machine

```
gcloud compute ssh <vm> --zone <zone> -- -N -L 5901:<home>/.cache/daniel-verify/vnc.sock
```

Use plain `ssh -N -L 5901:<socket> <host>` off GCP. Then open
`vnc://localhost:5901`. The VNC server asks for no password, because only the
owning user can open the socket. If macOS Screen Sharing refuses that, use
TigerVNC Viewer (`brew install --cask tigervnc-viewer`).
