"""Run `agent-desktop permissions` and report which app macOS checked for each grant.

macOS (TCC) judges a CLI by its *responsible* app, the one that launched it, not by
the binary. This runs the real agent-desktop binary once, then reads tccd's own log
lines for that pid, so the answer comes from macOS rather than from a guess.

Usage: python3 -I tcc_who.py [--reveal] [--binary PATH]
Prints one JSON object: {"result": "granted"|"needs_grant"|"unknown", "message": ...,
"services": [{"service", "app", "path", "auth"}]}. --reveal opens the app to drag in
Finder when a grant is missing. Exit code 0 when everything checked is granted.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time

AUTH = {"0": "denied", "1": "unknown", "2": "allowed", "3": "limited"}
SERVICE = {
    "kTCCServiceAccessibility": "Accessibility (Device Control and Data Access)",
    "kTCCServiceScreenCapture": "Screen Recording",
    "kTCCServiceAppleEvents": "Automation",
}


def real_binary(given: str | None) -> str:
    if given:
        return given
    # The mise shim is a link to mise itself; run the installed file so the pid is agent-desktop's.
    mise = shutil.which("mise")
    if mise:
        done = subprocess.run(
            [mise, "which", "agent-desktop"],
            check=False,
            capture_output=True,
            text=True,
        )
        if done.returncode == 0 and done.stdout.strip():
            return done.stdout.strip()
    found = shutil.which("agent-desktop")
    if not found:
        sys.exit(
            json.dumps({"result": "unknown", "message": "agent-desktop is not on PATH"})
        )
    return found


def tcc_lines(pid: int) -> tuple[list[str], str | None]:
    """tccd's lines for this pid, and why `log show` failed (None when it ran)."""
    done = subprocess.run(
        [
            "/usr/bin/log",
            "show",
            "--last",
            "30s",
            "--style",
            "compact",
            "--predicate",
            f'process == "tccd" AND eventMessage CONTAINS "msgID={pid}."',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        return [], f"/usr/bin/log exited {done.returncode}: {done.stderr.strip()}"
    return done.stdout.splitlines(), None


def parse(lines: list[str]) -> list[dict]:
    by_msg: dict[str, dict] = {}
    for line in lines:
        m = re.search(r"(AUTHREQ_\w+): msgID=([\d.]+), (.*)", line)
        if not m:
            continue
        kind, msg, rest = m.groups()
        row = by_msg.setdefault(msg, {})
        if kind == "AUTHREQ_CTX":
            s = re.search(r"service=(\w+)", rest)
            row["service"] = s.group(1) if s else "?"
        elif kind == "AUTHREQ_ATTRIBUTION":
            # No responsible key means the process answers for itself.
            p = re.search(r"responsible_path=([^,}]+)", rest) or re.search(
                r"binary_path=([^,}]+)", rest
            )
            row["path"] = p.group(1) if p else "?"
        elif kind == "AUTHREQ_SUBJECT":
            s = re.search(r"subject=([^,]+)", rest)
            row["app"] = s.group(1) if s else "?"
        elif kind == "AUTHREQ_RESULT":
            a = re.search(r"authValue=(\d+)", rest)
            row["auth"] = AUTH.get(a.group(1), a.group(1)) if a else "?"
    services = {}
    for row in by_msg.values():
        if "service" in row:
            services[row["service"]] = {
                "service": SERVICE.get(row["service"], row["service"]),
                "app": row.get("app", "?"),
                "path": row.get("path", "?"),
                "auth": row.get("auth", "?"),
            }
    return list(services.values())


def complete(row: dict) -> bool:
    return "?" not in (row["app"], row["path"], row["auth"])


def bundle_of(path: str) -> str:
    m = re.match(r"(.*?\.app)/Contents/", path)
    return m.group(1) if m else path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reveal", action="store_true")
    ap.add_argument("--binary")
    args = ap.parse_args()
    proc = subprocess.Popen(
        [real_binary(args.binary), "permissions"], stdout=subprocess.PIPE, text=True
    )
    out, _ = proc.communicate()
    report = json.loads(out).get("data", {})
    time.sleep(1.5)  # tccd's log lines land a moment after the call returns.
    lines, failed = tcc_lines(proc.pid)
    services = parse(lines)
    missing = [s for s in services if complete(s) and s["auth"] != "allowed"]
    partial = [s["service"] for s in services if not complete(s)]
    states = {k: v.get("state") for k, v in report.items()}
    # Automation stays "unknown" until an Apple Event is sent, so only a denial counts there.
    refused = sorted(k for k, v in states.items() if v not in ("granted", "unknown"))
    refused += sorted(
        k for k, v in states.items() if v == "unknown" and k != "automation"
    )
    if failed:
        result, message = "unknown", f"{failed}; agent-desktop says {states}"
    elif not services:
        result, message = (
            "unknown",
            f"no tccd lines for pid {proc.pid}; agent-desktop says {states}",
        )
    elif missing:
        apps = sorted({bundle_of(s["path"]) for s in missing})
        result = "needs_grant"
        message = "Drag into System Settings and turn on: " + "; ".join(
            f"{bundle_of(s['path'])} -> {s['service']}" for s in missing
        )
        if args.reveal:
            for app in apps:
                subprocess.run(["open", "-R", app], check=False)
    elif partial or refused:
        # The log and the CLI disagree or the log is cut short: say so rather than guess.
        result = "unknown"
        why = [f"incomplete tccd lines for {partial}"] if partial else []
        if refused:
            why.append(f"tccd showed no denial, but agent-desktop says {refused}")
        message = (
            "; ".join(why) + f" ({states}); re-run, or read the log as SKILL.md shows"
        )
    else:
        result, message = "granted", f"agent-desktop says {states}"
    print(
        json.dumps(
            {"result": result, "message": message, "services": services}, indent=1
        )
    )
    return 0 if result == "granted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
