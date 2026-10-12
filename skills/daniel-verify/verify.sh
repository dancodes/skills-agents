#!/usr/bin/env bash
# Run a workspace's dev server from its repo profile, plus a shared display and Chrome.

set -Eeuo pipefail

home=$HOME/.cache/daniel-verify
state=$home/state
display=:50
socket=$home/vnc.sock
cdp_port=9222
script=$(realpath "$0")
repo_profile=$(dirname -- "$script")/../daniel/repo-profile.sh

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
alive() { [[ -n ${1:-} ]] && kill -0 "$1" 2>/dev/null; }
field() { jq -r ".$2 // empty" "$1"; }
listening() { ss -Htln "sport = :$1" | grep -q .; }

usage() {
  cat >&2 <<EOF
Usage:
  verify.sh templates [path]
  verify.sh start <path>
  verify.sh set-target <path> <template> <url>
  verify.sh list
  verify.sh stop <path|port>
  verify.sh stop --all
EOF
  exit 2
}

main() {
  mkdir -p "$state"
  chmod 700 "$home"
  case ${1:-} in
    templates) [[ $# -le 2 ]] || usage; templates "${2:-$PWD}" ;;
    start) [[ $# -eq 2 ]] || usage; start "$("$repo_profile" root "$2")" ;;
    set-target) [[ $# -eq 4 ]] || usage; set_target "$("$repo_profile" root "$2")" "$3" "$4" ;;
    list) list ;;
    stop) [[ $# -eq 2 ]] || usage; stop "$2" ;;
    *) usage ;;
  esac
}

load_profile() {
  PROFILE_DIR=$("$repo_profile" dir "$1")
  [[ -n $PROFILE_DIR && -f $PROFILE_DIR/verify.sh ]] || return 1
  source "$PROFILE_DIR/verify.sh"
}

templates() {
  load_profile "$1" || return 0
  (( ${#TEMPLATES[@]} )) || return 0
  printf '%s (default)' "${TEMPLATES[0]}"
  printf ' | %s' "${TEMPLATES[@]:1}"
  printf '\n'
}

start() {
  local root=$1 entry
  load_profile "$root" || die "No verify profile matches $root"
  check_env
  exec 9>"$home/alloc.lock"
  flock 9
  reap
  ensure_display
  ensure_chrome
  entry=$(entry_for "$root")
  if [[ -n $entry ]]; then
    printf 'Reusing the dev server for %s.\n' "$root"
  else
    prestart "$(app_dir "$root")" >"$home/prestart.log" 2>&1 || die "prestart failed. See $home/prestart.log"
    launch "$root"
  fi
  exec 9>&-
  wait_ready "$(field "$entry" port)"
  summary "$entry"
}

check_env() {
  [[ -f $ENV_FILE ]] || die "$ENV_FILE is missing"
  ! grep -q REPLACE_ME "$ENV_FILE" || die "$ENV_FILE still has REPLACE_ME values."
}

reap() {
  local f started age
  for f in "$state"/*.json; do
    [[ -e $f ]] || continue
    if ! alive "$(field "$f" pid)"; then
      printf 'Removed a dead entry: %s (port %s).\n' "$(field "$f" workspace)" "$(field "$f" port)"
      rm -f "$f"
      continue
    fi
    started=$(field "$f" started_at)
    age=$(( $(date +%s) - $(date -d "$started" +%s) ))
    (( age < 86400 )) || printf 'Running for more than 24h: %s on port %s. Stop: %s stop %s\n' \
      "$(field "$f" workspace)" "$(field "$f" port)" "$script" "$(field "$f" port)"
  done
}

entry_for() {
  local f
  for f in "$state"/*.json; do
    [[ -e $f && $(field "$f" workspace) == "$1" ]] && { printf '%s\n' "$f"; return; }
  done
  return 0
}

ensure_display() {
  pgrep -u "$USER" -f "^Xvnc $display( |$)" >/dev/null && return
  [[ -f $home/Xauthority ]] || xauth -f "$home/Xauthority" add "$display" . "$(mcookie)"
  rm -f "$socket"
  setsid Xvnc "$display" -geometry 1920x1080 -depth 24 -auth "$home/Xauthority" -nolisten tcp \
    -rfbport -1 -rfbunixpath "$socket" -rfbunixmode 0600 -SecurityTypes None \
    </dev/null >"$home/xvnc.log" 2>&1 9>&- &
  for _ in $(seq 50); do [[ -S $socket ]] && return; sleep 0.2; done
  die "Xvnc did not start. See $home/xvnc.log"
}

ensure_chrome() {
  listening "$cdp_port" && return
  [[ -x $home/chrome-bin ]] || die "$home/chrome-bin is missing. See the skills-agents README."
  DISPLAY=$display XAUTHORITY=$home/Xauthority setsid "$home/chrome-bin" \
    --remote-debugging-port="$cdp_port" --remote-debugging-address=127.0.0.1 \
    --user-data-dir="$home/chrome-profile" --no-first-run --no-default-browser-check --disable-popup-blocking \
    --window-position=0,0 --window-size=1920,1080 about:blank \
    </dev/null >"$home/chrome.log" 2>&1 9>&- &
  for _ in $(seq 50); do listening "$cdp_port" && return; sleep 0.2; done
  die "Chrome did not open port $cdp_port. See $home/chrome.log"
}

launch() {
  local root=$1 port pid log cmd
  port=$(free_port) || die "All ports (${PORTS[*]}) are in use. $(list)"
  log=$home/dev-$port.log
  dev_command "$port"
  (
    set -a; source "$ENV_FILE"; set +a
    dev_env "$port"
    cd "$(app_dir "$root")"
    exec setsid "${cmd[@]}" </dev/null >"$log" 2>&1 9>&-
  ) &
  pid=$!
  jq -n --arg ws "$root" --arg profile "$PROFILE_DIR" --argjson port "$port" --argjson pid "$pid" \
    --arg log "$log" --arg started "$(date -Iseconds)" \
    '{workspace: $ws, profile: $profile, port: $port, pid: $pid, started_at: $started, log: $log, template: null, target_url: null}' \
    >"$state/$port.json"
  entry=$state/$port.json
}

free_port() {
  local p
  for p in "${PORTS[@]}"; do
    [[ -e $state/$p.json ]] || listening "$p" || { printf '%s\n' "$p"; return; }
  done
  return 1
}

wait_ready() {
  local code
  for _ in $(seq 120); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$1$HEALTH_PATH" || true)
    [[ $code == 2* ]] && return
    [[ $code == 000 ]] || die "The dev server answered $code on $HEALTH_PATH. See $home/dev-$1.log"
    alive "$(field "$state/$1.json" pid)" || die "The dev server exited. See $home/dev-$1.log"
    sleep 1
  done
  die "The dev server did not answer on port $1 in 120s. See $home/dev-$1.log"
}

summary() {
  local port
  port=$(field "$1" port)
  jq . "$1"
  printf 'App: http://localhost:%s\nProfile steps: %s/verify.md\nStop when done: %s stop %s\n' \
    "$port" "$PROFILE_DIR" "$script" "$port"
}

set_target() {
  local f
  f=$(entry_for "$1")
  [[ -n $f ]] || die "No dev server runs for $1"
  jq --arg t "$2" --arg u "$3" '.template = $t | .target_url = $u' "$f" >"$f.tmp" && mv "$f.tmp" "$f"
  jq . "$f"
}

list() {
  local f
  for f in "$state"/*.json; do
    [[ -e $f ]] || continue
    printf '%s  port %s  pid %s %s  since %s  target %s\n' "$(field "$f" workspace)" \
      "$(field "$f" port)" "$(field "$f" pid)" "$(alive "$(field "$f" pid)" && echo up || echo dead)" \
      "$(field "$f" started_at)" "$(field "$f" target_url)"
  done
}

stop() {
  local f
  if [[ $1 == --all ]]; then
    for f in "$state"/*.json; do [[ -e $f ]] && stop_entry "$f"; done
    pkill -u "$USER" -f -- "--user-data-dir=$home/chrome-profile" || true
    pkill -u "$USER" -f "^Xvnc $display( |$)" || true
    printf 'Stopped all dev servers, Chrome and Xvnc.\n'
    return
  fi
  if [[ $1 =~ ^[0-9]+$ ]]; then f=$state/$1.json; else f=$(entry_for "$("$repo_profile" root "$1")"); fi
  [[ -n $f && -e $f ]] || die "No dev server found for $1"
  stop_entry "$f"
}

stop_entry() {
  local pid
  pid=$(field "$1" pid)
  alive "$pid" && kill -- "-$pid" 2>/dev/null || true
  printf 'Stopped port %s (%s).\n' "$(field "$1" port)" "$(field "$1" workspace)"
  rm -f "$1"
}

main "$@"
