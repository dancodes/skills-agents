#!/usr/bin/env python3
"""Run `yarn typecheck` in the current directory, one agent at a time.

Serializes machine-wide: a cold tsgo run peaks around 2GB, and several
workspaces typechecking at once exhaust RAM until the OOM killer fires.

fcntl.flock rather than a lock binary, because macOS ships no flock(1) and
Linux ships no shlock(1). The kernel drops the lock when the holder dies, which
is the state an OOM-killed run leaves behind.

ponytail: one machine-wide pool; per-repo pools only if this machine ever
typechecks two unrelated repos at once.
"""
import fcntl
import os
import subprocess
import sys
import time

LOCK_PATH = "/tmp/yarn-typecheck.{}.lock"
POLL_SECONDS = 3


def acquire(slots, deadline):
    """A held lock file, or None once deadline passes with every slot busy."""
    handles = [open(LOCK_PATH.format(slot), "a+") for slot in range(slots)]
    while True:
        for handle in handles:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                continue
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()}\n")
            handle.flush()
            return handle
        if time.monotonic() >= deadline:
            for handle in handles:
                handle.close()
            return None
        time.sleep(POLL_SECONDS)


def holders(slots):
    pids = []
    for slot in range(slots):
        try:
            with open(LOCK_PATH.format(slot)) as handle:
                pids.append(handle.read().strip())
        except OSError:
            pass
    return " ".join(pids)


def main(argv):
    slots = int(os.environ.get("TYPECHECK_SLOTS", "1"))
    wait_seconds = float(os.environ.get("TYPECHECK_WAIT", "570"))
    lock = acquire(slots, time.monotonic() + wait_seconds)
    if lock is None:
        print(f"typecheck.py: no free slot after {wait_seconds:.0f}s. "
              f"Held by pid(s): {holders(slots)}", file=sys.stderr)
        return 1
    # One checker beats the default four on a 2-core box: ~40% faster and ~53%
    # less memory. A caller's own --checkers wins, argv coming last.
    return subprocess.run(["yarn", "typecheck", "--checkers", "1", *argv]).returncode


def test():
    # flock conflicts across open file descriptions, so one process can fill
    # every slot and prove the next caller waits.
    held = [acquire(2, time.monotonic()), acquire(2, time.monotonic())]
    assert all(held), "two slots, two holds"
    start = time.monotonic()
    assert acquire(2, time.monotonic() + 4) is None, "third caller gives up"
    assert time.monotonic() - start >= 4, "and waits for the deadline first"
    assert holders(2).split() == [str(os.getpid())] * 2, holders(2)
    for handle in held:
        handle.close()
    assert acquire(1, time.monotonic()), "closing a holder frees its slot"
    print("ok")


if __name__ == "__main__":
    sys.exit(test() if "--test" in sys.argv else main(sys.argv[1:]))
