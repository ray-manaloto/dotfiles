# Cold review — `d8fca05` (`fix/841-gcc-pin-os-scoped-smoke`)

Reviewer: Opus 5, cold (no design context supplied; intent inferred from code).
Date: 2026-08-30. Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`.

Reference implementation compared against:
`~/dev/github/ray-manaloto/knowledge-base/sources/mise/src/toolset/tool_request.rs`
— `is_os_supported` at `tool_request.rs:467-484`, `normalize_os` at
`tool_request.rs:664-670`, `normalize_arch` at `tool_request.rs:673-679`,
`ARCH`/`OS` at `cli/version.rs:52-60`, `os` field type at
`toolset/tool_version_options.rs:22`.

---

## Verdict on honesty of a "no findings" call

**A "no findings" verdict would NOT be honest.** The core direction of the
change is right and the two production call sites are correctly reasoned. But:

1. one **HIGH** finding — a test whose stated premise is measurably false on
   this machine, and which will start failing the moment this branch merges;
2. four semantic divergences from the reference implementation the docstring
   claims to mirror, all measured, all producing false FAILs of the smoke.

Conversely, I will not manufacture a finding about the three new unit tests:
I mutation-tested them and they genuinely discriminate. That evidence is below.

---

## What the change does (my reading, from the code)

`parse_declared_tools` / `resolve_declared_tools` /
`resolve_declared_tools_at_base` gain a **required** `arch` keyword and filter
each `[tools]` entry through a new `_tool_os_supported`
(`python/src/dotfiles_setup/image.py:127-159`). The smoke's *expected* tool set
therefore drops entries whose `os = [...]` key excludes the architecture being
smoked, so the tier-1 exact-set `diff`
(`python/src/dotfiles_setup/image.py:380-397`) stops reporting a `<`
declared-not-installed for a tool mise deliberately never installs there.

The real corpus entry that motivates it:
`.devcontainer/mise-system.toml:68` — `"conda:gxx" = { version = "16.2.0", os = ["linux/arm64"] }`.

Two production call sites supply `arch`:

| Site | Source of arch | Verdict |
|---|---|---|
| `build_smoke_docker_cmd` `image.py:986` | `platform_arch(platform)` where `platform` is the very value passed to `docker run --platform` (`image.py:1004-1006`) | **Defensible.** Same fact, one derivation — it cannot disagree with the container. |
| `smoke_script_main` tier 1 `image.py:2032-2034` | `platform_arch(host_platform())` = the container's own `uname` | **Defensible.** This generator runs INSIDE the target container (`scripts/devcontainer-smoke.sh:34`), and `host_platform()` reports the container's arch even under emulation (`platform_target.py:400-409`). The `mise.local.toml`-beats-exec'd-env reasoning is confirmed by the pre-existing `gcc_latest` precedent at `image.py:2043-2062`. |

Making `arch` required rather than defaulted is the right call: a default would
have let one call site keep the bug silently.

---

## Findings

### HIGH | The exec test derives arch from the repo pin while the image it runs is arm64; it breaks on merge | `tests/test_image_smoke_exec.py:130-137`, `tests/test_image_smoke_exec.py:155-159`

The new code resolves the expected set with
`platform_arch(resolve_platform())` and justifies it in a comment:

> `_DEV_IMAGE` is the amd64 image (DOTFILES_PLATFORM pin), run under Rosetta on
> this arm64 Mac host

**That premise is false as measured on this machine, today:**

```
$ docker image inspect ghcr.io/ray-manaloto/dotfiles-devcontainer:dev \
    --format '{{.Os}}/{{.Architecture}}/{{.Variant}}'
linux/arm64/
$ docker run --rm ghcr.io/ray-manaloto/dotfiles-devcontainer:dev uname -m
aarch64
```

Nothing enforces the premise either: `_run_in_image`
(`tests/test_image_smoke_exec.py:105-113`) runs
`docker run --rm -i <image> bash -l` with **no `--platform` flag**, so the
image's own manifest arch decides — and since #676/#736 publish both
architectures, an arm64 host pulls arm64 by default. Meanwhile `mise run
smoke-exec` (`mise.toml:233-237`) inherits the global
`DOTFILES_PLATFORM = linux/amd64/v2` (`mise.toml:152`), so
`resolve_platform()` answers **amd64** for an **arm64** container.

The test passes right now only by accident: `arch=` is currently **inert** for
`resolve_declared_tools_at_base`, because the merge-base blob has no `os` key
at all —

```
$ git show 7f2b85a:.devcontainer/mise-system.toml | grep gxx
"conda:gxx" = "latest"

$ resolve_declared_tools_at_base(repo, arch='amd64') == \
  resolve_declared_tools_at_base(repo, arch='arm64')
True
```

and I confirmed the exec test is green today:
`pytest -m image_exec …::test_tier1_core_passes_against_dev -q` → `1 passed`.

**Once this branch merges**, the merge-base blob carries
`os = ["linux/arm64"]`. Then `arch=amd64` drops `conda:gxx` from the expected
set, while the arm64 `:dev` has it installed — measured:

```
$ docker run --rm …:dev bash -lc 'mise ls --json | jq …'
conda:gxx|latest|true|/usr/local/share/mise/config.toml
```

→ the tier-1 diff reports `>` installed-not-declared and
`mise run smoke-exec` FAILS.

This is **the same defect class the commit fixes**, reintroduced one layer up:
an expected-set arch taken from a source that can disagree with the container's
real architecture. Production chose `uname` for exactly this reason
(`image.py:2026-2034`); the test chose the repo pin.

**Suggested fix (pick one, not both):** pass `--platform` in `_run_in_image` so
the premise is enforced rather than asserted, **or** derive arch from the
container (`docker run --rm <img> uname -m` → `normalize_arch`) so the test
mirrors production. The second is the one production already argues for.

Corollary: the two exec-test edits carry **no test of their own** — `arch=` is
inert on the current merge-base, so they pass identically with any value. They
are the only part of this diff not covered by a discriminating arm.

---

### MEDIUM | `os = ["linux/x64"]` is dropped here but INSTALLED by mise | `python/src/dotfiles_setup/image.py:154`, `python/src/dotfiles_setup/platform_target.py:104-109`

mise's `normalize_arch` (`tool_request.rs:673-679`) maps
`"x86_64" | "amd64" | "x64" → "x64"`, and `cli::version::ARCH`
(`cli/version.rs:53-60`) is `"x64"` on x86_64 — so mise **matches**
`os = ["linux/x64"]` on amd64. `x64` is one of mise's three documented amd64
spellings.

`dotfiles_setup.platform_target._ARCH_ALIASES` (`platform_target.py:104-109`)
contains only `x86_64 / amd64 / arm64 / aarch64`. `normalize_arch` returns
`None` for anything else (`platform_target.py:377-379`), and `None == "amd64"`
is False. Measured:

```
 False  linux/x64 on amd64
  True  linux/x86_64 on amd64
  True  linux/aarch64 on arm64
```

A `linux/x64`-scoped pin would be installed by mise and omitted from the
expected set → `>` installed-not-declared → false smoke FAIL. Adding
`"x64": "amd64"` to `_ARCH_ALIASES` closes it (and is correct for
`platform_target` generally — `x64` is a real docker/OCI-adjacent spelling).

---

### MEDIUM | The OS half is normalized MORE permissively than mise, keeping tools mise skips | `python/src/dotfiles_setup/image.py:150`, `python/src/dotfiles_setup/image.py:156`

The predicate does `os_part.strip().lower() != "linux"`. mise does neither: it
calls `normalize_os` (`tool_request.rs:664-670`, whose only mappings are
`darwin|macos → macos` and `windows|win → windows`, everything else
pass-through) and compares exactly against `OS`, which is
`env::consts::OS` = `"linux"` (`cli/version.rs:52`). Measured divergences:

| entry | target | mise | this predicate |
|---|---|---|---|
| `LINUX/ARM64` | arm64 | **no match** | `True` |
| `" linux / arm64 "` | arm64 | **no match** | `True` |

Here the predicate is the *permissive* side: it keeps a tool mise will skip, so
the expected set names an uninstalled tool → `<` declared-not-installed → the
**exact #841 false-failure**, back again through a different door. Dropping the
`.strip().lower()` (or applying it consistently on both sides of a
`normalize_os` equivalent) makes the two agree.

---

### MEDIUM | `os = []` means "nowhere" to mise and "everywhere" here | `python/src/dotfiles_setup/image.py:145-146`

`if not os_list: return True` conflates *key absent* with *key present but
empty* — the classic falsy-check bug. mise distinguishes them: `self.os()` is
`Option<Vec<String>>` (`tool_version_options.rs:22`), so `os = []` is
`Some(vec![])`, `.any()` over an empty iterator is `false`, `!matched` →
`is_os_supported()` returns **false** (`tool_request.rs:468-482`). Measured:

```
  True  empty list os=[]  (arch=amd64)
```

Opposite verdicts. The faithful test is `if os_list is None: return True`.
Nobody writes `os = []` today, but the whole point of a predicate that claims
to mirror an upstream one is that it survives inputs nobody wrote yet.

---

### LOW | A bare-string `os = "linux"` is silently dropped rather than rejected | `python/src/dotfiles_setup/image.py:147`

`for entry in os_list` over a `str` iterates **characters**; none equals
`"linux"`, so the tool is silently omitted. Measured: `os = "linux"` → `False`.
mise's field is `Option<Vec<String>>` (`tool_version_options.rs:22`), so the
same TOML is a hard deserialization error there — loud, not silent. A silent
wrong answer where the reference errors is the worse of the two.

---

### LOW | Unhandled `TypeError` on a non-iterable `os` value | `python/src/dotfiles_setup/image.py:147`

Measured: `os = 5` → `TypeError: 'int' object is not iterable`, escaping
`parse_declared_tools`. This is at least *loud* — it would surface as a
traceback out of `dotfiles-setup image smoke-script --tier 1`, whose stdout is
captured and eval'd by `scripts/devcontainer-smoke.sh:34` under
`set -euo pipefail`, so it fails honestly. Informational; I would not gate the
merge on it. Note it only because the docstring's stated contract
(`image.py:129-144`) enumerates spec shapes and this one is outside it.

---

### LOW | Docstring says "mirrors is_os_supported"; it mirrors only its first half | `python/src/dotfiles_setup/image.py:130-133`

mise's `is_os_supported` ends with `self.ba().is_os_supported()`
(`tool_request.rs:483`) — a **backend-level** OS check that consults the
registry (`cli/args/backend_arg.rs:703-711`). A tool can be skipped by mise for
that reason with no `os` key present at all. Not reachable for this repo's
conda/npm/github/core backends on linux (I did not find a counterexample), so
this is a docstring-precision finding, not a behaviour one. Say "mirrors the
`os`-key half of `is_os_supported`".

---

### LOW | `arch` is documented as pre-normalized but not normalized or asserted | `python/src/dotfiles_setup/image.py:141-143`

The docstring requires callers to pass a docker-normalized arch. Nothing
enforces it, and the failure is silent: `arch="x86_64"` makes every slashed
entry return `False`. Both current call sites go through `platform_arch`, so
they are correct — but `resolve_declared_tools` / `resolve_declared_tools_at_base`
are module-level API already imported by two test modules, and `uname -m` is
the natural thing for a future caller to reach for. `normalize_arch` is already
imported at `image.py:31`; `arch = normalize_arch(arch) or arch` at the top is
free and removes the footgun.

---

### LOW (style) | The `"linux"` literal is inlined twice inside the loop | `python/src/dotfiles_setup/image.py:150`, `python/src/dotfiles_setup/image.py:156`

On the hardcode-vs-parameter question the brief raises: **I agree with the
decision** to fix the OS half rather than thread it — the justification at
`image.py:135-140` is sound (every image this project builds is a Linux
container) and matches how `os_arch` / `expected_uname_machine` already behave
(`platform_target.py:446-458`). My only note is placement: the literal appears
twice in a loop body, and `platform_target` is where every other platform fact
in this repo lives. If it ever needs threading, a `TARGET_OS = "linux"`
constant there is the seam.

Conversely, nothing in this diff is parameterized that should be fixed.

---

## Did the new tests actually FAIL if the production change were reverted?

Checked explicitly rather than assumed, with **two sharp mutations** — the
signature stayed intact in both, so a failure is caused by the *semantics*, not
by an arity change. Mutations applied via a pytest plugin in the scratchpad
(no repo file edited).

**Mutation A — pre-fix semantics** (`_tool_os_supported → always True`):

```
CONTROL (unmutated):  8 passed
MUTATED:              2 failed, 6 passed
  FAILED test_parse_declared_tools_omits_os_scoped_entry_on_other_arch
  FAILED test_resolve_declared_tools_honors_real_os_scoped_pin
```

**Mutation B — over-aggressive fix** (drop *every* `os`-scoped entry):

```
MUTATED:              2 failed, 6 passed
  FAILED test_parse_declared_tools_keeps_os_scoped_entry_on_matching_arch
  FAILED test_resolve_declared_tools_honors_real_os_scoped_pin
```

Conclusion: **the three new unit tests are genuinely armed in both directions.**
`…_keeps_os_scoped_entry_on_matching_arch` passing under Mutation A is not a
weakness — it is the second arm, and its own docstring says so; Mutation B
proves it discriminates. `…_honors_real_os_scoped_pin` fails under both, which
is what a real-corpus end-to-end arm should do.

The one gap is stated in the HIGH finding: the two **exec**-test edits are
discriminated by nothing, because `arch=` is currently inert against the
merge-base blob.

Coupling note (accepted, not a finding): `…_honors_real_os_scoped_pin` reads
the live `.devcontainer/mise-system.toml`, so removing the `conda:gxx` pin
turns it red. Its docstring is explicit about being the real-corpus arm, and
the synthetic-fixture pair covers the same semantics independently, so the
coupling is bought deliberately.

---

## Things I checked and found CORRECT

- `linux/arm64/v8` (a full triple mistakenly used as an `os` entry) → `False`
  on **both** sides. Python's `partition("/")` and Rust's `split_once('/')`
  both split on the first slash, leaving `"arm64/v8"`, which neither
  `normalize_arch` recognises. Measured.
- `linux/x86_64` on amd64 and `linux/aarch64` on arm64 → `True` on both sides.
  The two normalizers use different canonical vocabularies (`amd64` vs `x64`)
  but each compares within its own, so the result agrees. Measured.
- `os = ["macos"]` on a linux target → `False` on both sides. This is the shape
  `mise.toml:68` actually uses for `conda:ffmpeg`. Measured.
- Bare-string spec (`python = "latest"`) → `True`; table with no `os` key →
  `True`. Both match mise. Measured.
- **Every failure mode above is a false FAIL, never a false PASS.** Whether the
  predicate over-drops or over-keeps, the tier-1 `diff`
  (`image.py:380-397`) reports it as `<` or `>` and exits 1. No divergence in
  this diff can turn a broken image green. That materially lowers the severity
  of MEDIUMs 1-3.
- The `>` installed-not-declared direction is untouched by the change: the
  installed side is still `mise ls --json` filtered by `.installed == true`
  (`image.py:381-387`).
- All call sites were enumerated; none was missed. `resolve_declared_tools*` /
  `parse_declared_tools` appear only at `image.py:986`, `image.py:2033`,
  `image.py:200/204/210`, `image.py:1949`, and in the two test modules.

---

## Suggested priority

1. **HIGH** — fix the exec test's arch source (pin `--platform` in
   `_run_in_image`, or read the container's `uname`). It breaks on merge.
2. **MEDIUM** — add `"x64": "amd64"` to `_ARCH_ALIASES`; drop the
   `.strip().lower()` on the OS half; change `if not os_list` to
   `if os_list is None`. Three one-liners, each with an obvious unit test.
3. **LOW** — docstring precision on "mirrors `is_os_supported`"; normalize
   `arch` defensively.

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — read `src/toolset/tool_request.rs`,
  `src/toolset/tool_version_options.rs`, `src/cli/version.rs`,
  `src/cli/args/backend_arg.rs`, `src/oci/mod.rs` from the local knowledge-base
  source tree, to compare `is_os_supported` / `normalize_os` / `normalize_arch`
  against the new Python predicate.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo
  under review.
