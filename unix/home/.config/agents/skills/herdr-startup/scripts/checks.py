#!/usr/bin/env python3
"""Read-only checks for a rolling herdr restart.

  checks.py graph     every live agent tab is in graph.json, every non-lead child names a parent lane, no
                      graph tab points at a terminal that is gone
  checks.py versions  every running claude process runs the installed Claude Code version and started after
                      the last plugin install/update (so it has loaded current plugins)
  checks.py busy      per agent tab: safe to restart now? (idle status AND no background child processes
                      besides MCP servers / LSPs)

Each prints JSON and exits 1 when something fails, so mise/hk can call it as a doctor check.
Usage: python3 -I checks.py {graph|versions|busy} [--graph PATH] [--tabs t2c5,t2cq]
"""
import argparse, datetime, glob, json, os, re, subprocess, sys

HOME = os.path.expanduser("~")
GRAPH = os.path.join(HOME, "dev/tmp/fix-herdr/wiki/sessions/graph.json")
WIKI = os.path.join(HOME, "dev/tmp/fix-herdr/wiki")
# Long-lived children a Claude session keeps for itself; anything else under it counts as a background job.
SERVICE = re.compile(r"(mcp|lsp|language-server|clangd|pyright|gopls|rust-analyzer|typescript-language-server|"
                     r"jdtls|sourcekit|caffeinate|codebase-memory|openwiki|context7|exa|firecrawl|playwright|"
                     r"node .*server|uv tool run|uv tool uvx|npx -y|npm exec|bun x|modelcontextprotocol|node_repl|cua_node|codex-code-mode-host|"
                     r"^codex |hc (watch|tail)|fnox (daemon|mcp)| server(\s|$))", re.I)


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def live_terminals():
    out = []
    for t in json.loads(run(["hc", "ls", "--json"]) or "{}").get("terminals", []):
        if t.get("state") == "live":
            out.append(t)
    return out


def proc_table():
    rows = {}
    for line in run(["ps", "-axo", "pid=,ppid=,lstart=,args="]).splitlines():
        m = re.match(r"\s*(\d+)\s+(\d+)\s+(\w{3}\s+\w{3}\s+\d+\s+[\d:]+\s+\d{4})\s+(.*)", line)
        if m:
            rows[int(m.group(1))] = {"ppid": int(m.group(2)), "start": m.group(3), "args": m.group(4)}
    return rows


def kids_of(pid, rows):
    out, stack = [], [pid]
    while stack:
        p = stack.pop()
        for c, r in rows.items():
            if r["ppid"] == p:
                out.append(c)
                stack.append(c)
    return out


def fg(addr):
    return json.loads(run(["hc", "get", addr, "--json"]) or "{}")


def claude_pid(info, rows):
    """The claude process in a terminal: its foreground pid if that is claude, else a descendant named claude."""
    f = (info.get("foreground") or {})
    cands = [f.get("pid")] + kids_of(info.get("pid") or -1, rows)
    for p in cands:
        if p and p in rows and re.search(r"(^|/)claude(\s|$)", rows[p]["args"]):
            return p
    return None


def cmd_graph(a):
    """Terminal ids change on every restore, so tabs are matched by "space / tab" name, not by address."""
    g = json.load(open(a.graph))
    live = {t.get("where"): t for t in live_terminals() if t.get("where")}
    in_graph = {}
    for s in g.get("spaces", []):
        if s.get("kept_from_previous_graph"):
            continue
        for t in s["tabs"]:
            if t.get("kept_from_previous_graph"):
                continue
            for i, x in enumerate(t["terminals"]):
                in_graph[f"{s['name']} / {t['name']}" + (f"-{i + 1}" if i else "")] = x
    problems = []
    for where, t in live.items():
        if t.get("agent") in ("claude-code", "codex", "opencode") and where not in in_graph:
            problems.append({"kind": "live_agent_not_in_graph", "terminal": t["address"], "where": where})
    for where, x in in_graph.items():
        if x["kind"] != "shell" and where not in live:
            problems.append({"kind": "graph_tab_not_live", "where": where, "old_terminal": x["address"]})
        sp, tab = where.split(" / ", 1)
        lead = tab.endswith(("-lead", "-coord", "-v2")) or sp == "chief-of-staff"
        if x["kind"] == "claude" and not lead and not x.get("lane_parents"):
            problems.append({"kind": "child_without_parent_lane", "where": where})
    print(json.dumps({"check": "graph", "graph_taken_at": g.get("taken_at"), "problems": problems}, indent=1))
    return 1 if problems else 0


def cmd_versions(a):
    vdir = os.path.join(HOME, ".local/share/claude/versions")
    installed = sorted(os.listdir(vdir), key=lambda v: [int(x) for x in re.findall(r"\d+", v)])[-1] if os.path.isdir(vdir) else None
    pj = os.path.join(HOME, ".claude/plugins/installed_plugins.json")
    # Marketplace plugins (installed_plugins.json) and inline mods loaded from CLAUDE_CODE_PLUGIN_DIRS
    # (side-notes, you-should-know-forward): their .claude-plugin/plugin.json changes on every install.
    # What a session loads at start: user-scope plugin code (version + commit), enabledPlugins and pluginConfigs
    # in ~/.claude/settings.json, and the inline mods' plugin.json. installed_plugins.json timestamps are not usable:
    # Claude rewrites records (and lastUpdated) without any code change whenever a session starts somewhere. So
    # hash the code set and remember when each hash was first seen; the mark is that time.
    import hashlib
    parts = []
    try:
        for k, entries in sorted(json.load(open(pj)).get("plugins", {}).items()):
            for e in entries:
                if e.get("scope") == "user":
                    parts.append(f"{k}|{e.get('version')}|{e.get('gitCommitSha')}")
    except Exception:
        pass
    st = os.path.join(HOME, ".claude/settings.json")
    mods = []
    try:
        cfg = json.load(open(st))
        parts.append(json.dumps(cfg.get("enabledPlugins", {}), sort_keys=True))
        parts.append(json.dumps(cfg.get("pluginConfigs", {}), sort_keys=True))
        for d in filter(None, cfg.get("env", {}).get("CLAUDE_CODE_PLUGIN_DIRS", "").split(":")):
            f = os.path.join(d, ".claude-plugin", "plugin.json")
            if os.path.exists(f):
                mods.append(f)
                parts.append(hashlib.sha256(open(f, "rb").read()).hexdigest())
    except Exception:
        pass
    h = hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
    sfile = os.path.join(HOME, ".local/state/herdr-checks/codeset.json")
    os.makedirs(os.path.dirname(sfile), exist_ok=True)
    seen = json.load(open(sfile)) if os.path.exists(sfile) else {}
    if h not in seen:
        # First run ever: seed with the newest settings/mod file time; later new hashes get "now".
        first = max(os.path.getmtime(f) for f in [st] + mods) if not seen else datetime.datetime.now().timestamp()
        seen[h] = datetime.datetime.fromtimestamp(first).isoformat(timespec="seconds")
        json.dump(seen, open(sfile, "w"), indent=1)
    plug_mtime = datetime.datetime.fromisoformat(seen[h])
    rows = proc_table()
    out, bad = [], 0
    for t in live_terminals():
        if t.get("agent") != "claude-code" or (a.tabs and t["address"] not in a.tabs):
            continue
        info = fg(t["address"])
        pid = claude_pid(info, rows)
        if not pid:
            continue
        txt = run(["lsof", "-a", "-p", str(pid), "-d", "txt", "-Fn"])
        m = re.search(r"/claude/versions/([\d.]+)", txt)
        ver = m.group(1) if m else None
        started = datetime.datetime.strptime(rows[pid]["start"], "%a %b %d %H:%M:%S %Y")
        ok_ver = ver == installed
        ok_plug = plug_mtime is None or started > plug_mtime
        bad += (not ok_ver) or (not ok_plug)
        out.append({"terminal": t["address"], "where": t.get("where"), "pid": pid, "version": ver,
                    "version_ok": ok_ver, "started": started.isoformat(timespec="minutes"), "plugins_ok": ok_plug})
    print(json.dumps({"check": "versions", "installed": installed,
                      "plugins_changed": plug_mtime.isoformat(timespec="minutes") if plug_mtime else None,
                      "sessions": out, "stale": bad}, indent=1))
    return 1 if bad else 0


def cmd_busy(a):
    rows = proc_table()
    out = []
    live = live_terminals()
    # hc run children that die with their parent (the default; only --outlive-parent survives) are herdr-core
    # terminals, not child processes, so the process scan misses them. Map parent -> such children.
    hc_kids = {}
    for t in live:
        info = fg(t["address"])
        if info.get("parent") and info.get("die_with_parent", True):
            hc_kids.setdefault(str(info["parent"]), []).append(t["address"])
    for t in live:
        if t.get("agent") not in ("claude-code", "codex", "opencode") or (a.tabs and t["address"] not in a.tabs):
            continue
        info = fg(t["address"])
        status = (info.get("status") or {}).get("state") or t.get("status")
        pid = claude_pid(info, rows) or (info.get("foreground") or {}).get("pid")
        jobs = []
        for c in kids_of(pid, rows) if pid else []:
            args = rows[c]["args"]
            if SERVICE.search(args) or re.match(r"^(-?zsh|bash|sh)$", args.split()[0] if args else ""):
                continue
            jobs.append(args.split(" && ", 1)[-1][:120] if "shell-snapshots" in args else args[:120])
        # In-process background agents and tasks (Agent tool, /code-review in background, Monitor) are not child
        # processes; Claude's footer shows them as "N in background".
        screen = run(["hc", "read", t["address"]])[-3000:]
        m = re.search(r"(\d+) in background", screen)
        if m and int(m.group(1)) > 0:
            # The footer also counts scheduled tasks (crons), which survive a restart. roll.py makes the final
            # call from the /exit dialog, which lists each item; here it is only reported.
            footer = f"{m.group(1)} background item(s) in footer (crons or agents)"
        else:
            footer = None
        for parent_key in (t["address"], str(pid)):
            for kid in hc_kids.get(parent_key, []):
                jobs.append(f"hc run child {kid} dies with this session")
        safe = status in ("done", "idle") and not jobs
        out.append({"terminal": t["address"], "where": t.get("where"), "status": status,
                    "background_jobs": jobs[:6], "footer": footer, "safe_to_restart": safe})
    print(json.dumps({"check": "busy", "tabs": out}, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("check", choices=["graph", "versions", "busy"])
    ap.add_argument("--graph", default=GRAPH)
    ap.add_argument("--tabs", default="")
    a = ap.parse_args()
    a.tabs = set(filter(None, a.tabs.split(",")))
    return {"graph": cmd_graph, "versions": cmd_versions, "busy": cmd_busy}[a.check](a)


if __name__ == "__main__":
    sys.exit(main())
