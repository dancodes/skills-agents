#!/usr/bin/env bash
# Record the shared daniel-verify screen while xdotool drives a real mouse through one Chrome tab.

set -Eeuo pipefail

home=$HOME/.cache/daniel-verify
export DISPLAY=:50 XAUTHORITY=$home/Xauthority
cdp=http://127.0.0.1:9222
lock=$home/screen.lock
here=$(dirname -- "$(realpath "$0")")
lead=1.5
rest=5
max_length=280
lock_wait=300

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  cat >&2 <<USAGE
Usage:
  video.sh setup                               check ffmpeg, xdotool, node and Chrome; install ffmpeg if missing
  video.sh timeline <steps>                    mm:ss of each "# label" line, and the video length
  video.sh front <target-id>                   bring the tab to the front once, so tab.mjs point can measure it
  video.sh try <target-id> <steps> <out.png>   run the steps with the real mouse, then save one screen frame
  video.sh record <target-id> <steps> <out.mp4>
  video.sh frames <video.mp4> [second ...]     save frames as PNG, default every 10 s and the last second

<steps> is an xdotool script file. Lines that start with # are timeline labels.
A line "shot <name> <target> [| <target> ...]" saves a sharp 2x crop of the box around
the targets to <out>-shots/<name>.png at that moment, without pausing the steps.
try and record also write <out>.events.jsonl and hold $lock.
USAGE
  exit 2
}

main() {
  case ${1:-} in
    setup) [[ $# -eq 1 ]] || usage; setup ;;
    timeline) [[ $# -eq 2 ]] || usage; timeline "$2" ;;
    front) [[ $# -eq 2 ]] || usage; front "$2" ;;
    try) [[ $# -eq 4 ]] || usage; try "$2" "$3" "$4" ;;
    record) [[ $# -eq 4 ]] || usage; record "$2" "$3" "$4" ;;
    frames) [[ $# -ge 2 ]] || usage; frames "${@:2}" ;;
    *) usage ;;
  esac
}

setup() {
  local tool
  has_ffmpeg || install_ffmpeg
  has_ffmpeg || die "ffmpeg has no x11grab or no libx264 after the install."
  for tool in xdotool flock curl node; do
    command -v "$tool" >/dev/null || die "$tool is missing."
  done
  node -e 'process.exit(typeof WebSocket === "function" ? 0 : 1)' || die "tab.mjs needs node 22 or later."
  curl -sf "$cdp/json/version" >/dev/null || die "No Chrome on $cdp. Start it with /daniel-verify."
  printf 'Ready. Screen %s on display %s. Lock: %s\n' "$(geometry)" "$DISPLAY" "$lock"
}

has_ffmpeg() {
  command -v ffmpeg >/dev/null || return 1
  [[ $(ffmpeg -hide_banner -devices 2>&1) == *x11grab* && $(ffmpeg -hide_banner -encoders 2>&1) == *libx264* ]]
}

install_ffmpeg() {
  printf 'Installing ffmpeg from apt.\n'
  sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold ffmpeg </dev/null \
    || die "The ffmpeg install failed. sudo must work without a password."
}

geometry() { xdotool getdisplaygeometry | tr ' ' x; }

fit() { node "$here/tab.mjs" fit "$1" $(xdotool getdisplaygeometry) </dev/null >/dev/null 9>&- || die "Could not size the window of tab $1 to the screen."; }

chain() { grep -Ev '^[[:space:]]*(#|$)' "$1"; }

timeline() {
  [[ -f $1 ]] || die "No steps file at $1"
  awk -v lead="$lead" -v rest="$rest" '
    function stamp(s) { return sprintf("%02d:%02d", int(s / 60), int(s) % 60) }
    /^[[:space:]]*shot[[:space:]]/ { next }
    /^[[:space:]]*#/ { sub(/^[[:space:]]*#[[:space:]]*/, ""); printf "%s  %s\n", stamp(lead + total), $0; next }
    {
      for (i = 1; i <= NF; i++) {
        if ($i == "click" || $i == "type" || $i == "key") { repeat = 0; delay = 0 }
        if ($i == "sleep") total += $(i + 1)
        if ($i == "--repeat") repeat = $(i + 1)
        if ($i == "--delay") delay = $(i + 1)
        if (repeat && delay) { total += repeat * delay / 1000; repeat = 0; delay = 0 }
      }
    }
    END { printf "length %d\n", lead + total + rest + 0.999 }
  ' "$1"
}

length_of() { timeline "$1" | awk '$1 == "length" { print $2 }'; }

hold_screen() {
  local target=$1 events=$2
  exec 9>"$lock"
  flock -w "$lock_wait" 9 || die "Another recording held the screen for $lock_wait s. Run the command again."
  curl -sf "$cdp/json/activate/$target" >/dev/null || die "No tab $target. List the tabs: node $here/tab.mjs list"
  fit "$target"
  trap 'kill ${listener:-} ${mouse:-} 2>/dev/null || true' EXIT
  node "$here/tab.mjs" listen "$target" "$events" 900 </dev/null >/dev/null 2>&1 9>&- &
  listener=$!
}

front() {
  exec 9>"$lock"
  flock -w "$lock_wait" 9 || die "Another recording held the screen for $lock_wait s. Run the command again."
  curl -sf "$cdp/json/activate/$1" >/dev/null || die "No tab $1. List the tabs: node $here/tab.mjs list"
  fit "$1"
  printf 'Tab %s is in front.\n' "$1"
}

try() {
  local target=$1 steps=$2 out=$3
  [[ -f $steps ]] || die "No steps file at $steps"
  hold_screen "$target" "${out%.*}.events.jsonl"
  chain "$steps" | run_steps "$target" "${out%.*}" 9>&-
  capture -frames:v 1 "$out"
  printf 'Frame: %s\nEvents: %s\n' "$out" "${out%.*}.events.jsonl"
}

record() {
  local target=$1 steps=$2 out=$3 length
  [[ -f $steps ]] || die "No steps file at $steps"
  length=$(length_of "$steps")
  (( length <= max_length )) || die "The steps take $length s. The limit is $max_length s: record it in parts."
  hold_screen "$target" "${out%.*}.events.jsonl"
  { printf 'sleep %s\n' "$lead"; chain "$steps"; } | run_steps "$target" "${out%.*}" >"${out%.*}.steps.log" 2>&1 9>&- &
  mouse=$!
  capture -t "$length" -vf scale=1280:-2 -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$out"
  printf 'Video: %s (%s s)\nEvents: %s\n' "$out" "$(duration "$out")" "${out%.*}.events.jsonl"
  cat "${out%.*}.steps.log"
  timeline "$steps"
}

run_steps() {
  local target=$1 base=$2 part=0 line
  local script=$base.xdotool.$part
  : >"$script"
  while IFS= read -r line; do
    if [[ $line =~ ^[[:space:]]*shot[[:space:]]+([^[:space:]]+)[[:space:]]+(.+)$ ]]; then
      [[ -s $script ]] && xdotool "$script" </dev/null
      mkdir -p "$base-shots"
      node "$here/tab.mjs" crop "$target" "$base-shots/${BASH_REMATCH[1]}.png" "${BASH_REMATCH[2]}" </dev/null &
      script=$base.xdotool.$((++part))
      : >"$script"
    else
      printf '%s\n' "$line" >>"$script"
    fi
  done
  [[ -s $script ]] && xdotool "$script" </dev/null
  wait
}

capture() {
  ffmpeg -loglevel error -y -f x11grab -framerate 15 -video_size "$(geometry)" -draw_mouse 1 -i "$DISPLAY" "$@" </dev/null
}

duration() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1" | cut -d. -f1; }

frames() {
  local video=$1 dir=${1%.*}-frames total second
  shift
  [[ -f $video ]] || die "No video at $video"
  total=$(duration "$video")
  mkdir -p "$dir"
  (( $# )) || set -- $(seq 5 10 "$((total - 1))") "$((total - 1))"
  for second in "$@"; do
    ffmpeg -v error -y -ss "$second" -i "$video" -frames:v 1 "$dir/f$second.png" </dev/null
    printf '%s\n' "$dir/f$second.png"
  done
}

main "$@"
