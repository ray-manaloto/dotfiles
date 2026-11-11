#!/usr/bin/env python3
"""Rolling restart: restart Claude tabs one at a time, in place, so each loads the current Claude Code
binary and plugins, without ever stopping a tab that is working or has background jobs.

Order: for each space given (in the order given), its children first, its lead last. The coordinator's own
tab is never touched (the owner resumes it by hand: /exit, then claude --permission-mode auto --resume
chief-of-staff).

Per tab:
  1. busy gate   checks.py busy: status must be done/idle and no background jobs. Otherwise SKIP it (listed
                 in the report, to retry later). Never interrupt.
  2. handshake   hc send a stop-point request: finish nothing new, write the resume block on your lane page,
                 then end your turn with the line READY-TO-RESTART (or BUSY-KEEP-ME <reason>).
  3. wait        up to --wait seconds for that line and an idle status; re-run the busy gate (a job may have
                 started meanwhile). BUSY-KEEP-ME or a timeout = SKIP.
  4. exit        hc send /exit; wait for the terminal to drop back to its shell.
  5. resume      restore.py --apply --only <terminal> --rolling: types the claude --resume command into the
                 same terminal (same tab, same id), with the rolling resume prompt.
  6. verify      checks.py versions --tabs <terminal>: version_ok and plugins_ok.

Dry run by default (prints the order and each tab's busy state). --apply does it.
Usage: python3 -I roll.py --spaces free-models,dotfiles [--tabs t2c8,t2c9] [--apply] [--wait 900]
"""
import argparse, json, os, re, subprocess, sys, time

RAW_ENV = {k: v for k, v in os.environ.items() if k not in ("HC_TERMINAL_ID", "HC_SCOPE")}
HERE = os.path.dirname(os.path.abspath(__file__))
HANDSHAKE = ("From chief-of-staff, rolling restart to load the new Claude Code plugins. Start nothing new. "
             "Bring your current step to a safe stopping point, write or update the Resume block at the top "
             "of your lane page (what you were doing, next step, any job to restart, every session-only cron, loop or "
             "monitor you run, since they end with this session, and your worktree path with any staged or "
             "uncommitted work and the commit or review step it waits on), then end your turn with "
             "the single line READY-TO-RESTART. If a background job or an owner question must not be "
             "interrupted, end with BUSY-KEEP-ME and the reason instead. Your session resumes in this same tab "
             "within a minute.")


def j(cmd, timeout=120):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {"raw": r.stdout[-400:], "err": r.stderr[-400:]}


IGNORE_FOOTER = set()  # tabs whose "N in background" footer the lead verified as finished (e.g. crons)


def busy(term):
    d = j([sys.executable, "-I", os.path.join(HERE, "checks.py"), "busy", "--tabs", term], timeout=300)
    b = (d.get("tabs") or [{}])[0]
    if term in IGNORE_FOOTER and b:
        b["background_jobs"] = [x for x in b.get("background_jobs", []) if "(footer)" not in x]
        b["safe_to_restart"] = b.get("status") in ("done", "idle") and not b["background_jobs"]
    return b


def state(term):
    d = j(["hc", "get", term, "--json"])
    return (d.get("status") or {}).get("state"), (d.get("foreground") or {}).get("argv") or []


def tail(term, n=40):
    return subprocess.run(["hc", "read", term], capture_output=True, text=True).stdout.splitlines()[-n:]


def wait_for(pred, secs, step=10):
    end = time.time() + secs
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return None


def order(spaces, tabs):
    live = j(["hc", "ls", "--json"]).get("terminals", [])
    out = []
    for sp in spaces:
        mine = [t for t in live if t.get("state") == "live" and t.get("agent") == "claude-code"
                and (t.get("where") or "").startswith(sp + " / ") and (not tabs or t["address"] in tabs)]
        lead = [t for t in mine if t["where"].split(" / ", 1)[1].endswith(("-lead", "-coord", "-v2"))]
        out += [t for t in mine if t not in lead] + lead
    return [t for t in out if t["address"] != os.environ.get("HC_TERMINAL_ID")]


def worktree_state(term):
    """git status of the tab's cwd, so the report proves the restart left staged and uncommitted work alone."""
    cwd = (j(["hc", "get", term, "--json"]).get("foreground") or {}).get("cwd")
    if not cwd:
        return None
    r = subprocess.run(["git", "-C", cwd, "status", "--porcelain=v1", "--branch"], capture_output=True, text=True)
    return {"cwd": cwd, "status": r.stdout if r.returncode == 0 else "(not a git repo)"}


def roll_one(t, a):
    term, where = t["address"], t["where"]
    v0 = j([sys.executable, "-I", os.path.join(HERE, "checks.py"), "versions", "--tabs", term], timeout=300)
    if (v0.get("sessions") or [{}])[0].get("plugins_ok"):
        return {"where": where, "terminal": term, "result": "skipped-already-current"}
    b = busy(term)
    if not b.get("safe_to_restart"):
        return {"where": where, "terminal": term, "result": "skipped-busy", "status": b.get("status"),
                "jobs": b.get("background_jobs")}
    st, argv = state(term)
    if "claude" not in " ".join(argv):
        return {"where": where, "terminal": term, "result": "skipped-foreground-not-claude", "argv": argv}
    subprocess.run(["hc", "send", term, HANDSHAKE], capture_output=True)
    time.sleep(15)

    def answered():
        # Match only a line that is exactly the marker; the request text itself mentions both markers.
        lines = [l.strip() for l in tail(term, 60)]
        s, _ = state(term)
        if s not in ("done", "idle"):
            return None
        for l in reversed(lines):
            if l == "READY-TO-RESTART":
                return "ready"
            if l.startswith("BUSY-KEEP-ME"):
                return "busy"
        return None
    ans = wait_for(answered, a.wait)
    if ans != "ready":
        return {"where": where, "terminal": term, "result": "skipped-" + (ans or "no-answer")}
    b = busy(term)
    if b.get("background_jobs"):
        return {"where": where, "terminal": term, "result": "skipped-job-started", "jobs": b["background_jobs"]}
    st, argv = state(term)  # re-check the foreground right before the send
    if "claude" not in " ".join(argv):
        return {"where": where, "terminal": term, "result": "skipped-foreground-changed", "argv": argv}
    # A send from an agent tab arrives wrapped as <hc from=...> chat; commands must go untagged.
    before = worktree_state(term)
    subprocess.run(["hc", "send", term, "/exit"], env=RAW_ENV, capture_output=True)
    time.sleep(4)
    # /exit opens "Background work is running ... will stop when you exit" when the session has background work.
    # Scheduled tasks (crons) are restored on resume (seen 2026-11-11 on ysk-mod-v2), so exit if that is all;
    # anything else (agents, shells) means Stay: press Esc and skip the tab.
    screen = "\n".join(tail(term, 40))
    if "Background work is running" in screen:
        block = screen.split("will stop when you exit:", 1)[-1].split("Exit and stop tasks", 1)[0]
        items = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith(("❯", "1."))]
        if items and all(i.startswith("scheduled task") for i in items):
            subprocess.run(["hc", "keys", term, "enter"], capture_output=True)
        else:
            subprocess.run(["hc", "keys", term, "esc"], capture_output=True)
            return {"where": where, "terminal": term, "result": "skipped-background-work-at-exit", "items": items[:6]}
    if not wait_for(lambda: "claude" not in " ".join(state(term)[1]), 90, 5):
        return {"where": where, "terminal": term, "result": "FAILED-exit-timeout"}
    time.sleep(3)
    res = j([sys.executable, "-I", os.path.join(HERE, "restore.py"), "--apply", "--rolling", "--only", term],
            timeout=300)
    time.sleep(20)
    v = j([sys.executable, "-I", os.path.join(HERE, "checks.py"), "versions", "--tabs", term], timeout=300)
    s = (v.get("sessions") or [{}])[0]
    after = worktree_state(term)
    same = before is None or after is None or before["status"] == after["status"]
    return {"where": where, "terminal": term, "at": time.strftime("%H:%M:%S"),
            "result": ("restarted" if s.get("plugins_ok") else "CHECK") + ("" if same else "-WORKTREE-CHANGED"),
            "worktree": (before or {}).get("cwd"), "worktree_unchanged": same,
            "restore": res, "version": s.get("version"), "plugins_ok": s.get("plugins_ok")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spaces", required=True)
    ap.add_argument("--tabs", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--wait", type=int, default=900, help="seconds to wait for READY-TO-RESTART per tab")
    ap.add_argument("--ignore-footer", default="", help="tabs whose footer background count the lead verified as finished")
    a = ap.parse_args()
    tabs = set(filter(None, a.tabs.split(",")))
    IGNORE_FOOTER.update(filter(None, a.ignore_footer.split(",")))
    plan = order([s.strip() for s in a.spaces.split(",") if s.strip()], tabs)
    if not a.apply:
        for t in plan:
            b = busy(t["address"])
            print(json.dumps({"where": t["where"], "terminal": t["address"], "status": b.get("status"),
                              "safe_now": b.get("safe_to_restart"), "jobs": b.get("background_jobs")}))
        return 0
    # Refresh the graph first so restore.py knows every tab's current session id.
    j([sys.executable, "-I", os.path.join(HERE, "..", "..", "herdr-shutdown", "scripts", "snapshot.py")], timeout=300)
    for t in plan:
        print(json.dumps(roll_one(t, a)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
