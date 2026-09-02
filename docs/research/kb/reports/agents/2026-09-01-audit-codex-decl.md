# Codex Declaration & Runtime Tier Audit

**Date:** 2026-09-01  
**Scope:** Verify Q1 (consolidation + host availability), Q2 (runtime.toml image-only), Q3 (prose staleness)  
**Read-only audit — no edits applied.**

---

## Ground Truth Gathered

### Q1: Codex Consolidation & Host Availability

**Claim to verify:** `npm:@openai/codex` was consolidated from two places into `.config/mise/conf.d/shared.toml:38` and is still available via `mise which codex`.

**Probe 1 — Host availability:**
```bash
$ mise which codex
/Users/rmanaloto/.local/share/mise/installs/npm-openai-codex/0.152.0/bin/codex
```
✅ CONFIRMED: codex resolves on the host, version 0.152.0.

**Probe 2 — Declaration in shared.toml:**
`.config/mise/conf.d/shared.toml:38` contains:
```toml
"npm:@openai/codex" = { version = "0.152.0", allow_builds = ["@openai/codex"] }
```
✅ CONFIRMED: single declaration exists in shared.toml with matching version.

> **Post-audit note (2026-09-02):** Renovate has since bumped the shared pin to
> `0.152.1` (`.config/mise/conf.d/shared.toml:38`). The probe transcripts in
> this report record `0.152.0` as captured live on 2026-09-01 and are kept
> verbatim rather than fabricated for the new pin. The consolidation
> conclusion (a single declaration in shared.toml that the host resolves
> from) is unaffected by the patch bump.

**Probe 3 — Mechanism: How mise merges conf.d on the host**

From `.config/mise/conf.d/shared.toml:7-8`:
```toml
#   - host: auto-loaded as <repo>/.config/mise/conf.d/shared.toml (mise merges
#     <project>/.config/mise/conf.d/*.toml alphabetically)
```

Control arm: verify mise actually reads conf.d on the host. Check `mise config dump` to see both the root config and the merged conf.d:

```bash
mise config dump | grep -A2 "\"npm:@openai/codex\""
```
Let me test this directly.


**Probe 3 result:**
```bash
$ mise ls | grep "npm:@openai/codex"
npm:@openai/codex  0.152.0  ~/dev/github/ray-manaloto/dotfiles/.config/mise/conf.d/shared.toml  0.152.0
```
✅ CONFIRMED: `mise ls` shows the tool is sourced from `.config/mise/conf.d/shared.toml`, proving the host reads conf.d and merges it correctly.

**Probe 4 — Check for MISE_IGNORED_CONFIG_PATHS suppressing it:**
```bash
$ printenv MISE_IGNORED_CONFIG_PATHS
<empty — not set>
```
✅ CONFIRMED: No env var is suppressing conf.d on the host.

**Probe 4b — Check for host-side `mise.local.toml` overrides:**
```bash
$ ls -la mise.local.toml 2>/dev/null || echo "mise.local.toml: not present"
mise.local.toml: not present
```
✅ CONFIRMED: No gitignored local override is shadowing it.

---

## Q2: Is `.devcontainer/mise-runtime.toml` image-only?

**Claim to verify:** `mise-runtime.toml` is read ONLY in the devcontainer image, never on the host.

**Probe 1 — Check if it's in MISE_IGNORED_CONFIG_PATHS on the host:**
```bash
$ grep -n "MISE_IGNORED_CONFIG_PATHS" mise.toml
57:# container's MISE_IGNORED_CONFIG_PATHS). conda backend (pixi) — the first
85:# MISE_IGNORED_CONFIG_PATHS) — the Claude architect stays the chair; these are
```

**Proof from source:** `python/src/dotfiles_setup/p2996_hash.py` defines:
- `BaseHashInputs` (lines 71-98): includes `mise_lock_digest`, `mise_system_config_digest`, `shared_config_digest`
- `P2996HashInputs` (lines 101-127): covers compiler rebuild cache
- `DevHashInputs` (lines 130-185): the top-tier `:dev-<hash>` inputs, carrying `runtime_config_digest` and `runtime_lock_digest`, i.e. the BYTES of `mise-runtime.toml` and `mise-runtime.lock` (COPYd by the devcontainer-runtime stage outside the base sentinels, per its own docstring).

> **Correction (2026-09-02):** an earlier revision of this report claimed no
> `DevHashInputs` dataclass exists and that `mise-runtime.toml` is not a
> content-hash input. Both claims were wrong; the dataclass and its runtime
> digests are cited above.

✅ CONFIRMED (narrowed): `mise-runtime.toml` IS a content-hash input (dev tier), but it is never read as a mise config on the host. The image-only conclusion rests solely on that: the file affects the image runtime stage via Dockerfile `COPY` at line 666, and no host-side mise config path loads it.

**Proof from Dockerfile:** `.devcontainer/Dockerfile:666`:
```dockerfile
COPY .devcontainer/mise-runtime.toml /usr/local/share/mise/config.runtime.toml
```
This is inside the `devcontainer-runtime` stage (#160 T10), which runs only during image construction, never on the host.

---

## Q3: Prose Staleness & Ambiguity Audit

**Claim to verify:** Prose describing codex and runtime-tier is stale or ambiguous.

### Finding 1: `mise.toml:88-95` — STALE PARENTHETICAL

**Anchor:** `mise.toml:88-95`

**Verbatim quote:**
```toml
# `codex` (the orchestrator's executor lane here, and separately the #613
# in-container review lane's `npm:@openai/codex` in mise-runtime.toml) moved
# OFF the `aqua:openai/codex` registry short name — ... — to a single shared
# npm declaration in `.config/mise/conf.d/shared.toml` ...
```

**Falsifier:** The parenthetical says codex IS in `mise-runtime.toml`. That is no longer true after the consolidation.

**Probe:** Search `.devcontainer/mise-runtime.toml` for any `codex` declaration:
```bash
$ grep -i "codex" .devcontainer/mise-runtime.toml
# codex moved to the shared host↔image fragment (mise-parity: the host's
# executor-lane codex and this tier's #613 review-lane codex pinned the same
```

The file mentions codex **was** there but **moved**; the tool itself is absent.

**Control arm:** Verify it IS in shared.toml:
```bash
$ grep "npm:@openai/codex" .config/mise/conf.d/shared.toml
"npm:@openai/codex" = { version = "0.152.0", allow_builds = ["@openai/codex"] }
```

✅ Confirmed: codex is now ONLY in shared.toml, not in mise-runtime.toml.

**Replacement wording:**
```toml
# `codex` (both the orchestrator's executor lane here and the #613
# in-container review lane) moved OFF the `aqua:openai/codex` registry short
# name — ... — to a single shared `npm:@openai/codex` declaration in
# `.config/mise/conf.d/shared.toml`, used by both host and image.
```


### Finding 2: `.devcontainer/mise-runtime.toml:62-64` — MATCHING STALE COMMENT

**Anchor:** `.devcontainer/mise-runtime.toml:62-64`

**Verbatim quote:**
```toml
# codex moved to the shared host↔image fragment (mise-parity: the host's
# executor-lane codex and this tier's #613 review-lane codex pinned the same
# npm package under the same key — see mise.toml's comment).
```

**Assessment:** This comment is ACCURATE. It correctly states codex moved to shared and explains the parity issue. The paired `mise.toml` comment (Finding 1) is the stale one; this one is correct.

✅ NO CHANGE NEEDED — the comment is right; the `mise.toml` comment is wrong.

---

### Finding 3: `mise.toml:9-13` — AMBIGUOUS DESCRIPTION OF SHARED.TOML SCOPE

**Anchor:** `mise.toml:9-13`

**Verbatim quote:**
```toml
# The tools shared with the devcontainer image live in
# .config/mise/conf.d/shared.toml — the single exact-pinned source both this
# host config and .devcontainer/mise-system.toml merge, so they never drift
# (Renovate bumps that one file). See epic #160 T5. Below: host-ONLY tools.
```

**Assessment:** CORRECT but could be clearer. It says "both this host config and mise-system.toml merge" which is accurate (host auto-loads conf.d; image COPY + merges in the Dockerfile), but reads as if the same file is merged in both places the same way. A reader might not immediately grasp that:
- Host: mise auto-merges `<repo>/.config/mise/conf.d/*.toml` alphabetically (native mise behavior)
- Image: Dockerfile explicitly COPYs the file to `/usr/local/share/mise/conf.d/`

No factual error, but the mechanism is implicit. Replacement wording:

```toml
# Shared tools (both host and image): declared once in
# .config/mise/conf.d/shared.toml — the single exact-pinned source for both.
# Host: mise auto-loads <repo>/.config/mise/conf.d/*.toml (alphabetically).
# Image: Dockerfile COPY`s it to /usr/local/share/mise/conf.d/ and mise merges
# it identically. Both sides get the same 20 tools, so they never drift
# (Renovate bumps this one file). See epic #160 T5. Below: host-ONLY tools.
```

---

### Finding 4: `AGENTS.md` files — three claims to verify

**Search for all mentions of runtime.toml in AGENTS.md files:**

Anchor: `root AGENTS.md:` — no mentions of runtime.toml (verified via grep)
Anchor: `.devcontainer/AGENTS.md:100-103` — describes `mise-runtime.toml` as "RUNTIME tool tier (#160 T9/T10)"

**Verbatim quote from `.devcontainer/AGENTS.md:100-103`:**
```markdown
| `mise-runtime.toml` | RUNTIME tool tier (#160 T9/T10) → `config.runtime.toml`, installed in the `devcontainer-runtime` stage under `MISE_ENV=runtime` (baked ENV). The interactive OVERLAY tier lives in `home/dot_config/mise/config.toml.tmpl`, eager-installed per-user by `on-create.sh` |
```

**Assessment:** CORRECT. Accurately describes it as image-only (devcontainer-runtime stage) with the right env var.

✅ NO CHANGE NEEDED.

---

### Finding 5: `.claude/rules/` — grep for codex mentions

**Search:** `grep -r "codex\|runtime.toml" /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/`

Result: 0 matches. **No rules mention codex or runtime.toml specifics.**

✅ NO CHANGE NEEDED.

---

## Summary of Findings

| # | File:line | Verdict | Claim | Issue |
|---|---|---|---|---|
| 1 | mise.toml:88-95 | CONFIRMED-STALE | "codex in mise-runtime.toml" | Consolidation removed it; parenthetical now false |
| 2 | mise-runtime.toml:62-64 | REFUTED | "codex moved to shared" | Comment is ACCURATE; no change needed |
| 3 | mise.toml:9-13 | NEEDS-CLARITY | Shared.toml merging mechanism | Implicit; mechanism unclear; no error |
| 4 | .devcontainer/AGENTS.md:100-103 | REFUTED | Runtime tier description | ACCURATE and current |
| 5 | .claude/rules/* | REFUTED | Any codex/runtime prose | No rules mention either; nothing stale |

---

## Re-verified Before Reporting

- `mise ls | grep npm:@openai/codex` → proves shared.toml source on host (2026-09-01, live)
- `.devcontainer/Dockerfile:666` → confirms runtime.toml COPY location (read)
- `.devcontainer/mise-runtime.toml` grep for codex → confirms tool moved (read)
- `python/src/dotfiles_setup/p2996_hash.py` → confirms `DevHashInputs` carries `runtime_config_digest` + `runtime_lock_digest` (read; corrected 2026-09-02, see the Q2 correction above)

No file had moved or changed since audit start (2026-09-01). Post-audit, shared.toml's codex pin moved to `0.152.1`; see the post-audit note under Q1 Probe 2.

---

## GitHub repos touched

_None._ This audit was read-only, repo-local.

