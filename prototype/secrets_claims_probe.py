#!/usr/bin/env python3
"""PROTOTYPE — THROWAWAY. Do not import, do not ship, do not add tests.

Run:  uv run --project python python prototype/secrets_claims_probe.py [claim]
      (claim = 4 | 1 | 2 | 3 | all;  default: 4)

## The question

`docs/research/kb/decisions/secrets-cli-grilling-2026-08-04b.md` § 4 lists four claims that
were read from --help or source and never executed. Each would change the spec if wrong.
Claim 4 is decisive: it settles D5 ("fnox stays" is provisional), and D6 (language) follows.

## Why this is not the skill's LOGIC or UI shape

Neither branch fits, and the SKILL says to state the assumption rather than force one. There
is no state model to drive and no UI to look at — these are empirical capability and timing
probes against real installed tools. What is kept from the skill: throwaway and marked as
such, one command to run, no persistence, no abstractions, full state surfaced after every
probe, and capture to a throwaway branch when done.

## Hard safety rules this file obeys

- **No secret VALUE is ever printed.** Commands that emit values run with stdout -> DEVNULL,
  and are measured by wall time and byte COUNT only.
- **Every subprocess has a hard timeout.** `timeout`/`gtimeout` are not installed on this
  host, and a keychain read from a non-GUI process can block forever (190 stuck processes,
  2026-08-02). Python's subprocess timeout is the only reliable kill available here.
- **The live fnox config is never modified.** A prior session's mutation test wiped it. Every
  write-touching probe runs under an isolated FNOX_CONFIG_DIR in the scratchpad.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

FNOX = "/Users/rmanaloto/.local/share/mise/installs/fnox/latest/fnox"
DOPPLER = "/Users/rmanaloto/.local/share/mise/installs/github-doppler-hq-cli/3.76.1/doppler"
MISE = shutil.which("mise") or "mise"
LIVE_CFG = Path.home() / ".config" / "fnox" / "config.toml"
KEYCHAIN_SERVICE = "mde-fnox"

BOLD, DIM, RST = "\x1b[1m", "\x1b[2m", "\x1b[0m"


def hdr(text: str) -> None:
    print(f"\n{BOLD}{'=' * 78}\n{text}\n{'=' * 78}{RST}")


def row(label: str, *, rc: object, secs: object = None, out_bytes: object = None, note: str = "") -> None:
    t = f"{secs:7.3f}s" if isinstance(secs, float) else f"{str(secs or ''):>8}"
    b = f"{out_bytes:>7}" if isinstance(out_bytes, int) else f"{'':>7}"
    print(f"  {label:<46} rc={str(rc):<8} {t}  bytes={b}  {DIM}{note}{RST}")


class Result(NamedTuple):
    """rc is an int, or the string 'TIMEOUT'. `out` is EMPTY unless keep_stdout was asked for."""

    rc: object
    secs: float
    nbytes: int
    out: str
    err: str


def probe(
    argv: list[str],
    *,
    timeout: float = 25.0,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    keep_stdout: bool = False,
) -> Result:
    """Run argv under a hard timeout.

    stdout is captured but only returned as TEXT when keep_stdout is set — callers that touch
    value-emitting commands get the byte count and nothing else.
    """
    full_env = {**os.environ, **(env or {})}
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            env=full_env,
            cwd=cwd,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Result("TIMEOUT", time.perf_counter() - t0, -1, "", "")
    dt = time.perf_counter() - t0
    err = p.stderr.decode(errors="replace")[:400]
    return Result(p.returncode, dt, len(p.stdout), p.stdout.decode(errors="replace") if keep_stdout else "", err)


# --------------------------------------------------------------------------------------
# CLAIM 4 — fnox-full vs fnox-less. Settles D5.
# --------------------------------------------------------------------------------------
def claim4() -> None:
    hdr("CLAIM 4 — fnox-full vs fnox-less  (decides D5; D6 follows)")

    print(f"{BOLD}4a. Shell-population cost: fnox vs doppler{RST}")
    print(f"{DIM}   All stdout is value-bearing -> counted, never printed.{RST}")

    r = probe([FNOX, "export", "-f", "shell"])
    row("fnox export -f shell (daemon allowed)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes)
    r = probe([FNOX, "export", "-f", "shell", "--no-daemon"], timeout=90)
    row("fnox export -f shell --no-daemon", rc=r.rc, secs=r.secs, out_bytes=r.nbytes, note="cold-ish")

    fb = Path(tempfile.mkdtemp(prefix="proto-fallback-")) / "fallback.enc"
    # NOTE: ~/.doppler/.doppler.yaml scopes only `/` and carries NO project/config, so a bare
    # `doppler secrets download` cannot know what to fetch. The project/config live in the FNOX
    # provider block instead. Passing them explicitly is itself part of the finding.
    scope = ["--project", "dotfiles", "--config", "dev_personal"]

    r = probe([DOPPLER, "secrets", "download", "--no-file", "--format", "env"], timeout=60)
    row("doppler download env (NO explicit scope)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
        note="expected to fail: no project/config configured")
    if r.rc != 0:
        print(f"    {DIM}stderr: {r.err.strip().splitlines()[0][:160] if r.err.strip() else '(empty)'}{RST}")

    r = probe(
        [DOPPLER, "secrets", "download", "--no-file", "--format", "env", *scope, "--fallback", str(fb)],
        timeout=60,
    )
    row("doppler download env + scope (network, writes fallback)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes)
    if r.rc != 0:
        print(f"    {DIM}stderr: {r.err.strip().splitlines()[0][:160] if r.err.strip() else '(empty)'}{RST}")
    print(f"  {DIM}fallback written: {fb.exists()}  size={fb.stat().st_size if fb.exists() else 0}{RST}")

    r = probe(
        [DOPPLER, "secrets", "download", "--no-file", "--format", "env", *scope,
         "--fallback", str(fb), "--offline"],
        timeout=60,
    )
    row("doppler download env --offline (fallback only)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes, note="warm")
    if r.rc != 0:
        print(f"    {DIM}stderr: {r.err.strip().splitlines()[0][:160] if r.err.strip() else '(empty)'}{RST}")

    print(f"\n{BOLD}4b. The DOPPLER_TOKEN keychain-ACL story without fnox{RST}")
    print(f"{DIM}   service={KEYCHAIN_SERVICE!r} account='DOPPLER_TOKEN'. `-w` triggers the ACL;{RST}")
    print(f"{DIM}   metadata reads do not. Both stdout streams go nowhere near the terminal.{RST}")

    # CONTROL ARM 1 — metadata read (no ACL needed). Proves the item exists and the probe works.
    r = probe(
        ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", "DOPPLER_TOKEN"],
        timeout=8,
    )
    row("security find-generic-password (NO -w, metadata)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
        note="control: item exists?")

    # CONTROL ARM 2 — a service that cannot exist. Proves a failure returns fast, not by hanging.
    r = probe(
        ["/usr/bin/security", "find-generic-password", "-s", f"nope-{os.getpid()}-zqf", "-a", "x"],
        timeout=8,
    )
    row("security find-generic-password (bogus service)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
        note="control: fails FAST?")

    # THE REAL ARM — `-w` requires ACL authorisation.
    #
    # ⚠️ ANSWERED AND NOW DISABLED BY DEFAULT. Ran twice on 2026-08-04, both TIMEOUT at 8.005s,
    # and both times it popped a GUI dialog ("security wants to use your confidential information
    # stored in 'mde-fnox'"). That dialog IS the finding: /usr/bin/security is not on the item's
    # ACL, so a non-GUI process blocks forever waiting for a password nobody can type.
    #
    # Re-enable only deliberately, and NEVER answer the dialog with "Always Allow" — that would
    # add /usr/bin/security to the ACL permanently and destroy the very condition being measured.
    if os.environ.get("PROTO_RUN_ACL_ARM") == "1":
        r = probe(
            ["/usr/bin/security", "find-generic-password", "-w", "-s", KEYCHAIN_SERVICE,
             "-a", "DOPPLER_TOKEN"],
            timeout=8,
        )
        row("security find-generic-password -w (ACL read)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
            note="TIMEOUT == /usr/bin/security is NOT on the ACL")
    else:
        row("security find-generic-password -w (ACL read)", rc="TIMEOUT", secs=8.005, out_bytes=-1,
            note="RECORDED 2026-08-04 x2; arm disabled (set PROTO_RUN_ACL_ARM=1 to re-run)")

    # And the incumbent, for comparison: fnox reading the same item.
    r = probe([FNOX, "list", "--no-daemon"], timeout=30)
    row("fnox list --no-daemon (fnox reads the same item)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
        note="names only, no values")


# --------------------------------------------------------------------------------------
# CLAIM 1 — mise bootstrap dotfiles
# --------------------------------------------------------------------------------------
def claim1() -> None:
    hdr("CLAIM 1 — `mise bootstrap dotfiles`: symlink-each + status --json --missing")

    root = Path(tempfile.mkdtemp(prefix="proto-dotfiles-"))
    src, tgt = root / "src", root / "home"
    src.mkdir()
    tgt.mkdir()
    (src / "alpha.conf").write_text("alpha original\n")
    (src / "beta.conf").write_text("beta original\n")
    # SCHEMA, from the LIVE schema (raw.githubusercontent.com/jdx/mise/main/schema/mise.json,
    # http 200) — the docs cache is stale and misses [dotfiles] entirely:
    #   "dotfiles applied with `mise dotfiles apply` or `mise bootstrap`, KEYED BY TARGET PATH"
    # value = a source string, or { source, mode, exclude, block, template, ... }.
    # TWO fixture defects, both caught by control arms rather than by reading:
    #  1. first fixture wrote {source=,target=,mode=} as TOP-LEVEL keys. mise read the config
    #     fine and rejected all three as dotfile ENTRIES whose targets were not absolute,
    #     leaving "no dotfiles configured" — every arm returned rc=0, a probe that could
    #     only pass.
    #  2. second fixture keyed per-FILE. mise: "mode symlink-each requires the source to be
    #     a directory". symlink-each is a DIRECTORY->DIRECTORY mode that links each child.
    (root / "mise.toml").write_text(
        "[dotfiles]\n"
        f'"{tgt}" = {{ source = "{src}", mode = "symlink-each" }}\n'
    )
    env = {"MISE_TRUSTED_CONFIG_PATHS": str(root)}

    def status(label: str, note: str = "") -> None:
        r = probe([MISE, "bootstrap", "dotfiles", "status", "--json", "--missing", "-C", str(root)],
                  env=env, timeout=30, keep_stdout=True)
        row(f"status --json --missing [{label}]", rc=r.rc, secs=r.secs, out_bytes=r.nbytes, note=note)
        if r.rc not in (0, 1):
            print(f"    {DIM}stderr: {r.err.strip()[:220]}{RST}")

    r = probe([MISE, "bootstrap", "dotfiles", "apply", "-C", str(root)], env=env, timeout=40)
    row("dotfiles apply (mode=symlink-each)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes)
    if r.rc != 0:
        print(f"    {DIM}stderr: {r.err.strip()[:300]}{RST}")

    made = sorted(p.name + ("->symlink" if p.is_symlink() else "->REGULAR") for p in tgt.iterdir())
    print(f"  {DIM}target now holds: {made}{RST}")

    status("all applied", "control: expect rc=0")

    (tgt / "alpha.conf").unlink()
    status("target MISSING", "expect rc=1")

    (tgt / "alpha.conf").write_text("alpha LOCALLY EDITED\n")   # regular file, not the symlink
    status("target DIFFERS", "expect rc=1")

    # "SOURCE gone" is ambiguous for a directory-mode entry, so arm BOTH readings rather than
    # publishing a defect against whichever one I happened to pick first.
    (tgt / "alpha.conf").unlink(missing_ok=True)
    r = probe([MISE, "bootstrap", "dotfiles", "apply", "-C", str(root)], env=env, timeout=40)
    row("re-apply (restore clean state)", rc=r.rc, secs=r.secs, out_bytes=r.nbytes)

    (src / "alpha.conf").unlink()          # source file gone, target symlink LEFT DANGLING
    dangling = (tgt / "alpha.conf").is_symlink() and not (tgt / "alpha.conf").exists()
    status("source FILE gone, target symlink DANGLING", f"dangling={dangling}; expect rc=1")

    shutil.rmtree(src)                      # the whole source DIRECTORY gone
    status("source DIRECTORY gone", "expect rc=1")


# --------------------------------------------------------------------------------------
# CLAIM 2 — fnox export honours a REAL declared profile
# --------------------------------------------------------------------------------------
def claim2() -> None:
    hdr("CLAIM 2 — `fnox export -f shell -P <p> --no-defaults` against a REALISTIC config")
    print(f"{DIM}   Fixture MIRRORS the live config's shape (arm the fixture, do not isolate the{RST}")
    print(f"{DIM}   variable). The live config is COPIED, never modified.{RST}")

    d = Path(tempfile.mkdtemp(prefix="proto-fnox-cfg-"))
    shutil.copy2(LIVE_CFG, d / "config.toml")
    text = (d / "config.toml").read_text()
    # Append a REAL profile declaring a small subset, using the plain provider so nothing resolves
    # against a live backend.
    # SCHEMA: a profile is NOT a flat map of secrets. fnox: "unknown field `PROTO_ONLY_A`,
    # expected one of `leases`, `providers`, `default_provider`, `secrets`" — so secrets nest
    # under [profiles.<name>.secrets]. Caught by the parse error, not by reading docs.
    text += (
        "\n[providers.proto_plain]\ntype = 'plain'\n"
        "\n[profiles.shell.secrets]\n"
        "PROTO_ONLY_A = { provider = 'proto_plain', value = 'PROTO_ONLY_A' }\n"
        "PROTO_ONLY_B = { provider = 'proto_plain', value = 'PROTO_ONLY_B' }\n"
    )
    (d / "config.toml").write_text(text)
    env = {"FNOX_CONFIG_DIR": str(d)}

    for label, args in [
        ("control: no profile", []),
        ("-P shell (profile only)", ["-P", "shell"]),
        ("-P shell --no-defaults", ["-P", "shell", "--no-defaults"]),
        ("-P bogus --no-defaults", ["-P", "bogus", "--no-defaults"]),
    ]:
        r = probe([FNOX, "list", "--no-daemon", *args], env=env, timeout=30, keep_stdout=True)
        names = [ln.split()[0] for ln in r.out.splitlines()[1:] if ln.strip()]
        proto = sum(1 for x in names if x.startswith("PROTO_ONLY_"))
        row(f"fnox list {label}", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
            note=f"total={len(names)} proto={proto}")
        if r.rc != 0:
            print(f"    {DIM}stderr: {' '.join(r.err.split())[:200]}{RST}")


# --------------------------------------------------------------------------------------
# CLAIM 3 — the cleartext-write defect
# --------------------------------------------------------------------------------------
def claim3() -> None:
    hdr("CLAIM 3 — does `fnox set --provider <non-writer>` write CLEARTEXT into the config?")
    print(f"{DIM}   Both arms, isolated FNOX_CONFIG_DIR, FAKE values. We assert by checking whether{RST}")
    print(f"{DIM}   the literal fake string lands in the file -- we never print the file.{RST}")

    # CONTROL ARM CHOICE MATTERS. My first run used `plain` as the "writer" control -- but plain
    # IS a cleartext store, so BOTH arms showed cleartext and the probe discriminated nothing.
    # `age` is the correct positive control: it must emit CIPHERTEXT for the same input.
    # The recipient below is the PUBLIC example key from fnox's own docs -- encryption needs only
    # a recipient, so no real key material is involved and nothing here can be decrypted.
    AGE_DOC_RECIPIENT = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
    marker = "PROTOTYPE-FAKE-VALUE-NOT-A-SECRET"

    arms = [
        ("age  (encrypting writer)", f'type = "age"\nrecipients = ["{AGE_DOC_RECIPIENT}"]'),
        ("plain (cleartext store)", 'type = "plain"'),
        ("doppler (CANNOT write: no put_secret)", 'type = "doppler"\nproject = "x"\nconfig = "y"'),
    ]
    for arm, provider_body in arms:
        d = Path(tempfile.mkdtemp(prefix="proto-set-"))
        cfg = d / "config.toml"
        cfg.write_text(f"[providers.p]\n{provider_body}\n\n[secrets]\n")
        r = probe(
            [FNOX, "set", "PROTO_KEY", marker, "--provider", "p", "-c", str(cfg)],
            env={"FNOX_CONFIG_DIR": str(d)},
            timeout=30,
        )
        body = cfg.read_text() if cfg.exists() else ""
        leaked = marker in body
        wrote_entry = "PROTO_KEY" in body
        row(f"fnox set [{arm}]", rc=r.rc, secs=r.secs, out_bytes=r.nbytes,
            note=f"entry_written={wrote_entry} CLEARTEXT_IN_CONFIG={leaked}")
        if r.rc != 0:
            print(f"    {DIM}stderr: {' '.join(r.err.split())[:200]}{RST}")


def main() -> None:
    which = (sys.argv[1] if len(sys.argv) > 1 else "4").lower()
    print(f"{BOLD}PROTOTYPE — secrets CLI claims{RST}  {DIM}throwaway; branch prototype/secrets-cli-claims{RST}")
    print(f"{DIM}No secret value is printed. Every subprocess is timeout-bounded.{RST}")
    table = {"4": [claim4], "1": [claim1], "2": [claim2], "3": [claim3],
             "all": [claim4, claim1, claim2, claim3]}
    for fn in table.get(which, [claim4]):
        try:
            fn()
        except Exception as exc:  # prototype: surface and continue, do not handle
            print(f"  {BOLD}probe raised:{RST} {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
