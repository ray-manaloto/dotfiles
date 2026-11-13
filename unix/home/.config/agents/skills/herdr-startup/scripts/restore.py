#!/usr/bin/env python3
"""Reopen the herdr workspace from graph.json after a reboot.

Dry run by default: prints what it would do. --apply does it.
For every tab in the graph (except the coordinator's, which the owner resumes by hand):
  - agent terminals resume their exact session:
      claude --permission-mode auto --resume <id> "<resume prompt>"
      codex-hc resume <id>
  - shell terminals reopen as plain shells in the same folder, unless the folder
    no longer exists (e.g. a /private/tmp scratchpad cleared by the reboot).
If herdr already restored a tab of that name in that space with an idle shell,
the resume command is typed into it instead of opening a duplicate.
The space is created (space.new) when missing. One terminal per tab is reopened
per agent; extra panes in a multi-pane tab come back as separate tabs named
"<tab>-<n>".

Usage: python3 -I restore.py [--graph FILE] [--apply] [--only t26j,t27h] [--rolling]
"""
import argparse, json, os, shlex, subprocess, sys, time

RAW_ENV = {k: v for k, v in os.environ.items() if k not in ("HC_TERMINAL_ID", "HC_SCOPE")}
HOME = os.path.expanduser("~")
PROMPT = ("Resumed after a Mac reboot by the chief of staff (herdr-startup). Your shells and background jobs "
          "ended with the reboot, and /private/tmp scratchpads were cleared (saved copies are under "
          "~/.local/state/scratch-keep/). Read the 'Resume after reboot' block at the top of your lane page, "
          "check your worktree (git status), restart only the jobs listed there, then continue. If you had a "
          "pending owner question, ask it again interactively.")
ROLLING = ("Resumed by the chief of staff's rolling restart (roll.py) to load the current Claude Code and "
           "plugins. Nothing else was stopped: your worktree and other tabs are as you left them. Read the "
           "Resume block at the top of your lane page. Run CronList first: session-only crons usually survive a resume. "
           "Re-create only the crons, loops and monitors the Resume block lists that are missing, delete duplicates, "
           "and continue from its next step.")


def sh(cmd, env=None):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {"raw": r.stdout.strip()[:300], "err": r.stderr.strip()[:300]}


def layout():
    cur = sh(["herdr-app", "ls"])
    spaces = {}
    for s in cur.get("spaces", []):
        spaces[s["name"]] = {"id": s["id"], "tabs": {t["name"]: t for t in s.get("tabs", [])}}
    return spaces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default=os.path.join(HOME, "dev/tmp/fix-herdr/wiki/sessions/graph.json"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", default="", help="old terminal addresses, e.g. t26j,t27h")
    ap.add_argument("--spaces", default="", help="space (project) names, e.g. dotfiles,glaze-fix")
    ap.add_argument("--list", action="store_true", help="print the spaces in the graph and exit")
    ap.add_argument("--rolling", action="store_true", help="rolling-restart resume prompt, not the reboot one")
    a = ap.parse_args()
    g = json.load(open(a.graph))
    if a.list:
        for s in g["spaces"]:
            n = sum(1 for t in s["tabs"] for x in t["terminals"] if x.get("session") and not x["is_coordinator"])
            print(f"{s['name']}: {len(s['tabs'])} tabs, {n} agent sessions")
        return 0
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    want = {x.strip() for x in a.spaces.split(",") if x.strip()}
    unknown = want - {s["name"] for s in g["spaces"]}
    if unknown:
        print(f"unknown space(s): {sorted(unknown)}; use --list", file=sys.stderr)
        return 2
    g["spaces"] = [s for s in g["spaces"] if not want or s["name"] in want]
    live = layout() if a.apply else {}
    report = {"opened": [], "typed_into_existing": [], "skipped": []}

    for s in g["spaces"]:
        for t in s["tabs"]:
            used = 0
            for x in t["terminals"]:
                tag = f"{s['name']} / {t['name']} (was {x['address']})"
                if only and x["address"] not in only:
                    continue
                if x["is_coordinator"]:
                    report["skipped"].append(f"{tag}: coordinator, resumed by hand")
                    continue
                folder = x["cwd"] if x["cwd"] and os.path.isdir(x["cwd"]) else None
                if x["kind"] == "claude" and x["session"]:
                    keep = []  # carry the model and effort the session was started with
                    old = x.get("argv") or []
                    for i, v in enumerate(old[:-1]):
                        if v in ("--model", "--effort"):
                            keep += [v, old[i + 1]]
                    argv = ["claude", "--permission-mode", "auto"] + keep + ["--resume", x["session"],
                                                                             ROLLING if a.rolling else PROMPT]
                elif x["kind"] == "codex" and x["session"]:
                    argv = ["codex-hc", "resume", x["session"]]
                else:
                    argv = None
                    if not folder:
                        report["skipped"].append(f"{tag}: shell in a folder that is gone ({x['cwd']})")
                        continue
                folder = folder or s.get("folder") or HOME
                name = t["name"] if used == 0 else f"{t['name']}-{used + 1}"
                used += 1

                if not a.apply:
                    print("DRY", s["name"], "/", name, "@", folder, "->", " ".join(argv[:5]) if argv else "(shell)")
                    report["opened"].append(tag)
                    continue

                sp = live.get(s["name"])
                existing = sp["tabs"].get(name) if sp else None
                if existing and argv and existing.get("terminals"):
                    term = existing["terminals"][0]["terminal"]
                    info = sh(["hc", "get", term, "--json"])
                    fg = ((info.get("foreground") or {}).get("argv") or ["?"])[0]
                    # Type only into a bare shell: no agent app and the foreground process is the shell itself.
                    if (info.get("status") or {}).get("app") is None and os.path.basename(fg).lstrip("-") in ("zsh", "bash", "sh", "fish"):
                        cmd = "cd " + shlex.quote(folder) + " && " + " ".join(shlex.quote(p) for p in argv)
                        sh(["hc", "send", term, cmd], env=RAW_ENV)  # untagged: typed into a shell
                        report["typed_into_existing"].append({"where": tag, "terminal": term})
                        continue
                if existing and not argv:
                    report["skipped"].append(f"{tag}: shell tab already restored by herdr")
                    continue
                args = ["--name", name, "--folder", folder] + (["--argv", json.dumps(argv)] if argv else [])
                if sp:
                    res = sh(["herdr-app", "do", "tab.new", "--space", sp["id"]] + args)
                else:
                    res = sh(["herdr-app", "do", "space.new", "--name", s["name"], "--folder", folder,
                              "--tab", name] + (["--argv", json.dumps(argv)] if argv else []))
                    live = layout()
                report["opened"].append({"where": tag, "result": res})
                time.sleep(2)
    if a.apply:
        # herdr has opened a new space's first tab in another space's folder (2026-11-10: dotfiles-lead
        # came back in another project's folder). Check each resumed agent's real cwd against the graph.
        time.sleep(5)
        wrong = []
        for s in g["spaces"]:
            for t in s["tabs"]:
                for x in t["terminals"]:
                    if not x.get("session") or x["is_coordinator"]:
                        continue
                    pids = subprocess.run(["pgrep", "-f", f"resume {x['session']}"], capture_output=True,
                                          text=True).stdout.split()
                    for pid in pids[:1]:
                        out = subprocess.run(["lsof", "-a", "-d", "cwd", "-p", pid, "-Fn"], capture_output=True,
                                             text=True).stdout
                        cwd = next((l[1:] for l in out.splitlines() if l.startswith("n")), "")
                        if x["cwd"] and cwd and os.path.realpath(cwd) != os.path.realpath(x["cwd"]):
                            wrong.append({"tab": t["name"], "session": x["session"], "now": cwd, "want": x["cwd"]})
        report["wrong_folder"] = wrong
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    sys.exit(main())
