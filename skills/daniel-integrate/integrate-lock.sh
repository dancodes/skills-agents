#!/usr/bin/env bash

# Serialize integration: two squashes landing into the same commits concurrently
# leave the change divergent and every other workspace stale. The lock sits next
# to the shared repository so every attached workspace contends for the same one.
# mkdir is the atomic primitive; macOS has no flock.

set -Eeuo pipefail

action=${1:-}
if [[ $action != acquire && $action != release && $action != status ]]; then
  printf 'Usage: integrate-lock.sh acquire|release|status\n' >&2
  exit 2
fi

root=$(jj workspace root)
repo=$root/.jj/repo
# In a secondary workspace .jj/repo is a file holding the path to the real one.
[[ -f $repo ]] && repo=$(cat -- "$repo")
lock=$(dirname -- "$repo")/daniel-integrate.lock

case $action in
  acquire)
    if ! mkdir -- "$lock" 2>/dev/null; then
      printf 'Integration is already in progress. Holder:\n' >&2
      cat -- "$lock/holder" >&2 2>/dev/null || printf '  (none recorded)\n' >&2
      printf '\nWait for it to finish. If that run is dead, release it with:\n  rm -rf %s\n' \
        "$lock" >&2
      exit 1
    fi
    printf '%s  %s  pid %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$root" "$PPID" \
      > "$lock/holder"
    printf 'Lock acquired.\n'
    ;;
  release)
    rm -rf -- "$lock"
    printf 'Lock released.\n'
    ;;
  status)
    if [[ -d $lock ]]; then
      printf 'held: '
      cat -- "$lock/holder" 2>/dev/null || printf '(none recorded)\n'
    else
      printf 'free\n'
    fi
    ;;
esac
