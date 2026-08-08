# Context baseline — `/context all`, 2026-08-07

The harness's **own** accounting of what occupies the window, captured from
`/context all` on `claude-opus-5[1m]`. Stored because every prior figure in this
repo was a **byte count with an assumed bytes-per-token divisor**, and this is
the first measurement that reports tokens directly.

⚠️ **It corrects this repo's published numbers upward by ~57%.** See §3.

## 1. Category totals

Session state at capture: 405.8k / 1m tokens (41%).

| Category | Tokens | % of window |
|---|---|---|
| System prompt | 6.2k | 0.6% |
| System tools | 12.3k | 1.2% |
| Custom agents | 4.2k | 0.4% |
| **Memory files** | **58.6k** | **5.9%** |
| Skills | 9.6k | 1.0% |
| Messages | 314.9k | 31.5% |
| Compact buffer | 3.0k | 0.3% |
| Free space | 591.2k | 59.1% |

These eight sum to exactly 1000.0k, which is the control that the list is
complete and non-overlapping.

⚠️ A re-rendered copy of the same output circulated with two extra rows — "MCP
tools (deferred) 18.1k" and "System tools (deferred) 19.2k". **Do not treat those
as additional standing cost**: adding them breaks the sum (1037k > 1m), so they
are either a subdivision of `System tools` or an artifact of the re-render. The
ASCII output above is authoritative.

**Standing overhead before any conversation** — everything except `Messages`,
`Compact buffer` and `Free space`: **90.9k tokens**. Of that, **58.6k (64%) is
this repo's instruction corpus** and **13.8k (15%) is the skill + agent listing**.

## 2. Per-file, the eager instruction corpus

| File | Tokens |
|---|---|
| `.claude/rules/secrets-out-of-the-shell-env.md` | 4,900 |
| `.claude/rules/mise-tasks-only.md` | 4,600 |
| `AGENTS.md` | 4,600 |
| `.claude/rules/research-doc-sources.md` | 3,300 |
| `.claude/rules/probes-need-a-control-arm.md` | 3,100 |
| `.claude/rules/verify-before-advancing.md` | 2,800 |
| `.claude/CLAUDE.md` | 2,500 |
| `.claude/rules/long-running-command-hangs.md` | 2,400 |
| `.claude/rules/do-not.md` | 2,300 |
| `.claude/rules/clarify-before-acting.md` | 2,200 |
| `.claude/rules/tool-currency-and-native-first.md` | 2,200 |
| `.claude/rules/agent-artifact-conventions.md` | 1,700 |
| `.claude/rules/use-tool-builtins.md` | 1,700 |
| `.claude/rules/local-devcontainer-first.md` | 1,600 |
| `.claude/rules/agent-report-persistence.md` | 1,500 |
| `.claude/rules/persistence-gate-retry.md` | 1,300 |
| `.claude/rules/gh-cli-watch.md` | 1,100 |
| `.claude/rules/zero-skip-policy.md` | 1,100 |
| `.claude/rules/ai-cli-invocation.md` | 1,100 |
| `.claude/rules/zero-bash-logic.md` | 1,000 |
| `.claude/rules/research-repo-enumeration.md` | 982 |
| `.claude/rules/clean-git-state.md` | 630 |
| `CLAUDE.md` | 14 |
| **21 rules subtotal** | **42,171** |
| **repo eager subtotal** | **49,285** |
| `MEMORY.md` (auto-memory index) | **9,500** |
| **memory-files total** | **58,785** ≈ the reported 58.6k |

**Control arm:** summing the harness's own per-file figures reproduces its
category total. The per-file list is therefore being read correctly, and is safe
to prioritise from.

## 3. ⚠️ The correction: bytes/token was wrong by 57%

Every token figure this repo published before today was
`bytes ÷ 4`. Measured against the harness:

| | Bytes | Tokens claimed (÷4) | Tokens actual | Error |
|---|---|---|---|---|
| Repo eager | 125,376 | 31,344 | **49,285** | **+57%** |
| `MEMORY.md` | 21,134 | 5,284 | **9,500** | **+80%** |
| Skill + agent listing | 32,595 | 8,148 | **13,800** | **+69%** |

The true divisor for this corpus is **~2.5 bytes/token**, not 4.0 — and for
`MEMORY.md` it is **~2.2**, because a dense index of backticked paths, issue
refs and symbol names tokenises far worse than prose.

**What this does and does not invalidate.** The BYTE measurements stand: they
were taken with the size engine's own classifier and cross-checked to the CLI
total. What was wrong is only the **conversion**, and it was wrong in the
direction that understates the problem. Restated:

- eager instruction corpus: **58.6k tokens**, not ~36.8k
- plus the listing: **72.4k tokens** of standing instruction context
- the whole standing overhead: **90.9k tokens**

The lesson is `probes-need-a-control-arm.md` rule 6, applied to a **constant**
rather than a measurement: `bytes ÷ 4` arrived as folklore, was never armed
against this corpus, and was then reported as a finding. A conversion factor is
an inherited number too.

## 4. What the harness itself suggests

> Memory files using 58.6k tokens (6%) → save ~17.6k
> Largest: `MEMORY.md` (9.5k), `secrets-out-of-the-shell-env.md` (4.9k),
> `mise-tasks-only.md` (4.6k). Use `/memory` to review and prune stale entries.

Its top three match this repo's own byte-ordered head exactly, which is a second
route to the same priority list.

## 5. Bearing on `docs/specs/progressive-disclosure-eager-context.md`

- §1's headline is understated; the corrected figures above supersede it.
- The trigger-shape classification is **unaffected** — it is a partition of the
  same files, and shares are byte-proportional.
- The corpus ratchet should stay pinned in **bytes** (deterministic, gate-visible)
  while reporting tokens alongside, since the tokeniser is not ours to pin.
- `MEMORY.md` at 9.5k tokens is the single largest instruction file — larger than
  any rule and than `AGENTS.md`. The spec defers it to phase 4; this measurement
  argues it is the biggest single lever available.

## 6. Second capture, after disabling 6 unused plugins — and a REFUTED hypothesis

`/doctor` disabled 6 zero-use plugins (code-modernization, feature-dev,
session-report, a duplicate exa, claude-md-management, claude-code-setup), then
`/context all` was re-run. Both captures are on the same session, same model.

| Category | Before | After | Δ |
|---|---|---|---|
| System prompt | 6.2k | 6.2k | 0 |
| System tools | 12.3k | **14.3k** | **+2.0k** |
| Custom agents | 4.2k | 3.0k | −1.2k |
| Memory files | 58.6k | 58.6k | 0 |
| Skills | 9.6k | 7.6k | −2.0k |
| **Standing overhead** | **90.9k** | **89.7k** | **−1.2k** |

Skills + agents fell **−3.2k**, as predicted. But `System tools` rose **+2.0k**,
so the net saving is **−1.2k**, not the ~3.3k projected. That rise is
**unexplained** and is recorded rather than rationalised — the plausible story
(disabling plugins changed what is deferred vs resident) is untested.

### ⚠️ The hypothesis was REFUTED, and the real cause is mundane

The prediction was: the skill listing is saturated at ~1% of the window, so
freeing plugin descriptions would let 11 absent project skills back in. It
**failed on both arms**:

- the listing dropped to **7.6k, comfortably under budget** — and
- **not one of the 15 absent skills reappeared.** The same 9 project skills are
  listed before and after.

The actual cause, found by inventorying frontmatter and the settings cascade:

| Mechanism | Count |
|---|---|
| `skillOverrides: "off"` in `.claude/settings.local.json` | **12** |
| `disable-model-invocation: true` in the skill's own frontmatter | **4** (one also in the 12) |
| **Total explained** | **15 of 15** |

**Zero unexplained, zero over-explained.** Every absent skill is absent *by
deliberate configuration*. Nothing was broken, nothing was crowded out, and the
plugin cleanup — while a real if smaller saving — repaired no functional defect,
because there was no functional defect.

The generalisable error: a plausible mechanism (budget saturation) was fitted to
a real observation (skills missing) without first checking the **boring**
explanation (someone turned them off). The settings cascade was read for
`defaultMode` and `enabledPlugins` in the same session and `skillOverrides` was
simply not looked at. *Check the config before theorising about the engine.*

### One stale entry worth cleaning

`skillOverrides` names **`omc-hud-wrapper-diagnostic`**, a skill that no longer
exists on disk — a leftover from the disabled `oh-my-claudecode` plugin. Harmless
but misleading: an override for a nonexistent skill reads as a live decision.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the corpus
  measured; the spec and gate this baseline corrects
