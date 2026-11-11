#!/usr/bin/env python3
"""Snapshot the herdr session graph before a reboot.

Writes graph.json and ledger.md: every space, tab and terminal, with the agent
running in it (claude / codex / shell), its exact session id, cwd and argv, plus
the parent -> children edges read from the wiki lane pages' "## Children" lists.

Session ids:
  - Claude Code writes ~/.claude/sessions/<pid>.json ({"sessionId", "cwd"}) for each
    interactive process; we match it against every process under the terminal.
  - Codex keeps its rollout file open (~/.codex/sessions/.../rollout-...-<uuid>.jsonl);
    we find it with lsof on the terminal's process tree.

Read-only. Usage: python3 -I snapshot.py [--out DIR] [--wiki DIR]
"""
import argparse, datetime, glob, json, os, re, subprocess, sys

HOME = os.path.expanduser("~")


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def descendants(pid, children):
    out, stack = [], [pid]
    while stack:
        p = stack.pop()
        out.append(p)
        stack.extend(children.get(p, []))
    return out


def process_children():
    kids = {}
    for line in run(["ps", "-axo", "pid=,ppid="]).splitlines():
        parts = line.split()
        if len(parts) == 2:
            kids.setdefault(int(parts[1]), []).append(int(parts[0]))
    return kids


def claude_session(pids):
    for p in pids:
        f = os.path.join(HOME, ".claude", "sessions", f"{p}.json")
        if os.path.exists(f):
            try:
                # The record can carry trailing data after the first JSON object; read only that object.
                d, _ = json.JSONDecoder().raw_decode(open(f).read())
                return d.get("sessionId"), p
            except Exception:
                pass
    return None, None


def codex_session(pids):
    if not pids:
        return None
    out = run(["lsof", "-p", ",".join(map(str, pids))], timeout=60)
    m = re.search(r"(/\S*rollout-\S*?-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl)", out)
    if not m:
        return None
    # A multi-agent v2 sub-agent's rollout can be the open file; it cannot be resumed on its own
    # ("resume the parent first"). Its session_meta.session_id names the root thread to resume.
    try:
        with open(m.group(1)) as f:
            meta = json.loads(f.readline()).get("payload", {})
        return meta.get("session_id") or m.group(2)
    except Exception:
        return m.group(2)


def lane_children(wiki):
    """Map child terminal address -> (lane file, line) from '## Children' sections."""
    edges = {}
    for f in sorted(glob.glob(os.path.join(wiki, "lanes", "*.md"))):
        inside = False
        for line in open(f, encoding="utf-8", errors="replace"):
            if line.startswith("## "):
                inside = line.strip().lower().startswith("## children")
                continue
            if inside:
                for addr in re.findall(r"\((t[0-9a-z]+)\)", line):
                    edges.setdefault(addr, []).append({"lane": os.path.basename(f), "line": line.strip()[:200]})
    return edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default=os.path.join(HOME, "dev/tmp/fix-herdr/wiki"))
    ap.add_argument("--out", default=None, help="default: <wiki>/sessions")
    a = ap.parse_args()
    out = a.out or os.path.join(a.wiki, "sessions")
    os.makedirs(out, exist_ok=True)

    layout = json.loads(run(["herdr-app", "ls"]) or "{}")
    kids = process_children()
    edges = lane_children(a.wiki)
    me = os.environ.get("HC_TERMINAL_ID")
    graph = {"taken_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
             "coordinator": me, "spaces": []}

    for s in layout.get("spaces", []):
        space = {"id": s["id"], "name": s["name"], "folder": s.get("folder"), "tabs": []}
        for t in s.get("tabs", []):
            tab = {"id": t["id"], "name": t["name"], "terminals": []}
            for term in t.get("terminals", []):
                addr = term["terminal"]
                info = json.loads(run(["hc", "get", addr, "--json"]) or "{}")
                fg = info.get("foreground") or {}
                root = info.get("pid")
                fgpid = fg.get("pid")
                tree = descendants(root, kids) if root else []
                if fgpid:
                    tree = [fgpid] + descendants(fgpid, kids) + tree
                sid, _ = claude_session(tree)
                kind, session = ("claude", sid) if sid else (None, None)
                if not kind:
                    cx = codex_session(tree)
                    if cx:
                        kind, session = "codex", cx
                kind = kind or "shell"
                tab["terminals"].append({
                    "address": addr, "kind": kind, "session": session,
                    "cwd": fg.get("cwd") or info.get("cwd"),
                    "argv": fg.get("argv"), "status": (info.get("status") or {}).get("msg"),
                    "lane_parents": edges.get(addr, []),
                    "is_coordinator": addr == me,
                })
            space["tabs"].append(tab)
        graph["spaces"].append(space)

    gpath = os.path.join(out, "graph.json")
    # Projects that are closed right now (restored only partly with restore.py --spaces) are not in the live
    # layout; keep their entries from the previous graph so a later restore still knows them.
    if os.path.exists(gpath):
        live = {s["name"]: s for s in graph["spaces"]}
        for s in json.load(open(gpath)).get("spaces", []):
            if s["name"] not in live:
                s["kept_from_previous_graph"] = True
                graph["spaces"].append(s)
                continue
            # A live space can still miss tabs that are closed now (e.g. a reviewer pane): keep those
            # whose agent session is not running in this layout.
            have = {x.get("session") for t in live[s["name"]]["tabs"] for x in t["terminals"]} - {None}
            names = {t["name"] for t in live[s["name"]]["tabs"]}
            for t in s["tabs"]:
                sess = {x.get("session") for x in t["terminals"]} - {None}
                if sess and not (sess & have) and t["name"] not in names:
                    t["kept_from_previous_graph"] = True
                    live[s["name"]]["tabs"].append(t)
    with open(gpath, "w") as fh:
        json.dump(graph, fh, indent=2)

    lines = [f"# Session graph ({graph['taken_at']})", "",
             "Generated by herdr-reboot/scripts/snapshot.py. One row per terminal; restore.py reopens the claude/codex ones.", "",
             "| space | tab | terminal | kind | session | cwd | listed under |", "|---|---|---|---|---|---|---|"]
    for s in graph["spaces"]:
        for t in s["tabs"]:
            for x in t["terminals"]:
                under = ", ".join(e["lane"] for e in x["lane_parents"]) or "-"
                lines.append(f"| {s['name']} | {t['name']} | {x['address']}{' (me)' if x['is_coordinator'] else ''} | {x['kind']} | {x['session'] or '-'} | {x['cwd'] or '-'} | {under} |")
    with open(os.path.join(out, "ledger.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    n = sum(len(t["terminals"]) for s in graph["spaces"] for t in s["tabs"])
    agents = sum(1 for s in graph["spaces"] for t in s["tabs"] for x in t["terminals"] if x["kind"] != "shell")
    missing = [x["address"] for s in graph["spaces"] for t in s["tabs"] for x in t["terminals"]
               if x["kind"] != "shell" and not x["session"]]
    elsewhere = work_elsewhere(graph, a.wiki)
    print(json.dumps({"wrote": gpath, "terminals": n, "agents": agents, "agents_without_session": missing,
                      "work_elsewhere": elsewhere}))


def git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=30)
    return r.stdout if r.returncode == 0 else ""


def work_elsewhere(graph, wiki):
    """Live agent sessions whose own checkout is clean while another worktree of the same repo has changes and
    a lane-page bullet names both the tab and that worktree. Heuristic (owner 2026-11-10): fix before closing."""
    blocks = []
    for f in glob.glob(os.path.join(wiki, "lanes", "*.md")):
        blocks += re.split(r"\n(?=\s*- )", open(f).read())
    found = []
    for s in graph["spaces"]:
        if s.get("kept_from_previous_graph"):
            continue
        for t in s["tabs"]:
            if t.get("kept_from_previous_graph"):
                continue
            for x in t["terminals"]:
                cwd = x.get("cwd")
                if x["kind"] == "shell" or not cwd or not os.path.isdir(cwd) or not git(cwd, "rev-parse", "--git-dir"):
                    continue
                if git(cwd, "status", "--porcelain", "--untracked-files=no").strip():
                    continue
                for line in git(cwd, "worktree", "list", "--porcelain").splitlines():
                    if not line.startswith("worktree "):
                        continue
                    other = line[len("worktree "):]
                    if os.path.realpath(other) == os.path.realpath(cwd) or not os.path.isdir(other):
                        continue
                    if not git(other, "status", "--porcelain", "--untracked-files=no").strip():
                        continue
                    base = os.path.basename(other)
                    # Only a bullet ABOUT this tab counts: the tab name in its first 80 characters (a lead's
                    # children list names many worktrees). Leads and coordinators belong in the main checkout.
                    if t["name"].endswith(("-lead", "-coord")):
                        continue
                    if any(t["name"] in b.lstrip()[:80] and base in b for b in blocks):
                        found.append({"tab": f"{s['name']} / {t['name']}", "session": x["session"],
                                      "cwd": cwd, "work_in": other})
    return found


if __name__ == "__main__":
    sys.exit(main())
