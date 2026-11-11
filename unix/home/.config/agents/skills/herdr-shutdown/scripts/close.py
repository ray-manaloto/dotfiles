#!/usr/bin/env python3
"""Close herdr tabs in a safe order before a reboot: children first, then leads.

Reads graph.json (from snapshot.py). Dry run by default; --apply closes. The
coordinator's own tab is never closed here: it is closed last, by hand (/exit),
after this script reports. A tab counts as a lead when its name ends in "-lead".
Every close passes --id (a bare tab.close acts on the active tab).

Usage: python3 -I close.py [--graph FILE] [--apply]
"""
import argparse, json, os, subprocess, sys, time

HOME = os.path.expanduser("~")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default=os.path.join(HOME, "dev/tmp/fix-herdr/wiki/sessions/graph.json"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    g = json.load(open(a.graph))
    children, leads, kept = [], [], []
    for s in g["spaces"]:
        for t in s["tabs"]:
            label = f"{s['name']} / {t['name']}"
            if any(x["is_coordinator"] for x in t["terminals"]):
                kept.append(label + " (coordinator: close last, by hand)")
                continue
            (leads if t["name"].endswith("-lead") else children).append((t["id"], label))
    done = []
    # Owner ruling: check every id against `herdr-app ls` right before any close.
    live = {}
    if a.apply:
        cur = json.loads(subprocess.run(["herdr-app", "ls"], capture_output=True, text=True, timeout=60).stdout or "{}")
        live = {t["id"]: f"{s['name']} / {t['name']}" for s in cur.get("spaces", []) for t in s.get("tabs", [])}
    for tid, label in children + leads:
        if a.apply and live.get(tid) != label:
            done.append({"tab": label, "ok": False, "out": f"skipped: herdr-app ls shows {live.get(tid)!r} for {tid}"})
            continue
        cmd = ["herdr-app", "do", "tab.close", "--id", tid, "--confirmed", "true"]
        if not a.apply:
            print("DRY", " ".join(cmd), "#", label)
            continue
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        done.append({"tab": label, "ok": r.returncode == 0, "out": (r.stdout or r.stderr).strip()[:200]})
        time.sleep(1)
    print(json.dumps({"closed": done, "order": [l for _, l in children + leads], "kept": kept}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
