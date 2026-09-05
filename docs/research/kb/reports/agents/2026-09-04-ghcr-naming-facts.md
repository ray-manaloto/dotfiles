# GHCR image naming facts (2026-09-04)

Fact-finding for renaming `ghcr.io/ray-manaloto/dotfiles-devcontainer` into
per-target single-platform names. In progress.

## GitHub repos touched

_TBD_

## 1. OCI/distribution-spec repository-name grammar

Source: `opencontainers/distribution-spec` `spec.md`, fetched via
`curl -sL https://raw.githubusercontent.com/opencontainers/distribution-spec/main/spec.md`
(line numbers below are from that raw file, section "Pulling manifests").

> spec.md:149: "Throughout this document, `<name>` MUST match the following regular
> expression:"
> spec.md:150: `` `[a-z0-9]+((\.|_|__|-+)[a-z0-9]+)*(\/[a-z0-9]+((\.|_|__|-+)[a-z0-9]+)*)*` ``

Parsed:
- Each path component is lowercase `[a-z0-9]+` runs joined by `.`, `_`, `__`
  (double underscore), or `-+` (**one or more hyphens** — so consecutive
  hyphens, e.g. `linux--amd64`, ARE spec-legal, matched by `-+`).
- `(\/[a-z0-9]+...)*` means the WHOLE `<name>` may repeat `/`-separated path
  components any number of times — i.e. **nested/multi-segment repository
  paths are legal per the spec grammar itself** (e.g.
  `dotfiles-devcontainer/linux-amd64` matches).
- No uppercase, no other punctuation (`+`, `~`, space, etc.) anywhere.
- **No hard length limit in the MUST grammar.** spec.md:154-156 is an
  "Implementers note" (non-normative): many clients cap the concatenation of
  `<host>[:<port>]/<name>` at 255 chars total; for `registry.example.org:5000`
  that leaves 229 chars for `<name>`. Treat 255 total / ~229 for `ghcr.io/…` as
  a practical soft cap, not a MUST.

## 7. OCI tag grammar

> spec.md:158: "the `<tag-or-digest>` as a tag MUST be at most 128 characters in
> length and MUST match the following regular expression:"
> spec.md:159: `` `[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}` ``

- First character: alnum or `_` only (no leading `.` or `-`).
- Remaining up to 127 chars: alnum, `.`, `_`, `-`.
- Max total length **128 characters** (hard MUST, unlike the name's soft cap).
- Case-sensitive, mixed case allowed (unlike `<name>`, which is lowercase-only).
- Practically: everything the operator wants encoded (os, arch, runner image,
  base image version, platform triple) fits far more comfortably in a TAG
  (128 chars, mixed case, dots allowed) than in the lowercase-only `<name>`.

## ⚠️ CAVEAT: `gh` in this environment is authenticated as a DIFFERENT account

`gh auth status` → logged in as **`sortakool`** (via `GITHUB_TOKEN` env), not
`ray-manaloto`. Cross-check that surfaced it: `gh api "/user/packages?package_type=container"`
returned two packages owned by `sortakool` (`pixi-devcontainer` id 10054073,
and — coincidentally — its OWN unrelated `dotfiles-devcontainer` id 11199434,
`repo: null`, `visibility: public`), while `gh api /users/ray-manaloto/packages/container/dotfiles-devcontainer`
correctly returned the real package (id **11297534**, owner `ray-manaloto`,
`visibility: private`, `repository: ray-manaloto/dotfiles`).

**Implication: every probe below uses the explicit `/users/ray-manaloto/...` or
`/orgs/.../` form, never the bare `/user/...` form** — the latter resolves to
`sortakool`'s own namespace in this shell, not Ray's. This also means any
future automation reading `gh api /user/packages` in this repo's CI would need
to confirm it runs under a token scoped to `ray-manaloto`, not this ambient
`GITHUB_TOKEN`.

## 4. Package visibility / repo-linkage — current state (control confirmed)

```
$ gh api /users/ray-manaloto/packages/container/dotfiles-devcontainer --jq '{name, package_type, visibility, repository: .repository.full_name}'
{"name":"dotfiles-devcontainer","package_type":"container","visibility":"private","repository":"ray-manaloto/dotfiles"}
```

## 2. Does GHCR support NESTED package paths — CONFIRMED YES, real probe

Control-armed probe (positive case, encoded form):

```
$ gh api "/orgs/github/packages/container/gh-aw-firewall%2Fagent"
{"id":10400595,"name":"gh-aw-firewall/agent","package_type":"container",
 "owner":{"login":"github", ...},"version_count":1128,"visibility":"public",
 "url":"https://api.github.com/orgs/github/packages/container/gh-aw-firewall%2Fagent",
 "repository":{"full_name":"github/gh-aw-firewall", ...},
 "html_url":"https://github.com/orgs/github/packages/container/package/gh-aw-firewall%2Fagent"}
```

`gh-aw-firewall/agent` is a REAL, currently-published nested container package
(1128 versions, owned by the `github` org, source repo `github/gh-aw-firewall`)
— found via the `gh` KB source tree
(`~/dev/github/ray-manaloto/knowledge-base/sources/gh/.github/workflows/dependabot-triage.lock.yml:2`),
which itself references three nested images in one manifest:
`ghcr.io/github/gh-aw-firewall/{agent,api-proxy,squid}:0.28.1`. So the shape
the operator wants — `ghcr.io/OWNER/dotfiles-devcontainer/linux-amd64` — is not
speculative; GitHub's own org runs the identical pattern in production.

**Negative control (same package, unencoded slash) — 404:**

```
$ gh api "/orgs/github/packages/container/gh-aw-firewall/agent"
{"message":"Not Found","documentation_url":"https://docs.github.com/rest","status":"404"}
```

Same package, only the slash-encoding differs → the API genuinely
discriminates on this, confirming the finding is real and not a fluke.

Two probe surfaces on the account's OWN packages (`gh api "/user/packages?package_type=container"`,
`gh api /users/ray-manaloto/packages/container/dotfiles-devcontainer`)
turned up zero slashed names — expected, since this repo has never
published one; the `github/gh-aw-firewall/*` case is the positive control
proving the mechanism exists.

Docker's registry side is consistent with this: `docker push`/`pull` treat
everything between the registry host and the final `:tag`/`@digest` as one
opaque `<name>` per the distribution-spec grammar (finding 1), and that
grammar explicitly allows internal `/`. GHCR's own docs example (`content/packages/working-with-a-github-packages-registry/working-with-the-container-registry.md:139-140`)
shows a `docker pull …/NAMESPACE/IMAGE_NAME:1.14.1` command whose printed
output reads `Status: Downloaded newer image for …/NAMESPACE/IMAGE_NAME/release:1.14.1`
— an extra `/release` segment appearing only in the OUTPUT, not the pulled
ref. This is most likely a stale/copy-pasted example in GitHub's own docs
(inconsistent with every other example on the same page) rather than a
deliberate demonstration — noting it for completeness, not relying on it as
evidence.

## 3. Packages REST API addressing of a nested path — needs `%2F`, and this repo's code does NOT do that

- **The API requires the `/` to be percent-encoded as `%2F` inside the package-name
  path segment.** A literal `/` is parsed as an additional URL path segment and
  404s (proven above, same package, both arms).
- **`gh api` itself does NOT auto-encode a `/` you pass in a path argument** —
  confirmed by the raw-slash 404 above; the caller must embed `%2F` explicitly.
- **This repo's code interpolates the package name RAW, with no encoding, in
  three places** — all would 404 against a slashed name today:
  - `python/src/dotfiles_setup/ghcr.py:167` —
    `["api", f"/orgs/{owner}/packages/container/{package_name}"]`
  - `python/src/dotfiles_setup/ghcr.py:185` —
    `f"/orgs/{owner}/packages/container/{package_name}/versions?per_page=20"`
  - `.github/workflows/ghcr-cleanup.yml:69` —
    `"/users/${OWNER}/packages/container/${PACKAGE}/versions?per_page=100"`
  - `.github/workflows/ghcr-cleanup.yml:100` —
    `"/users/${OWNER}/packages/container/${PACKAGE}/versions/${version_id}"`

  **Verdict: if `PACKAGE`/`package_name` were ever set to a value containing a
  literal `/` (e.g. `dotfiles-devcontainer/linux-amd64`), every one of these
  four call sites would 404** — none percent-encodes the slash. This is a real
  break, not a hypothetical; it was proven against the exact same code shape
  (`gh api "path/with/slash"`) two paragraphs up.

## 5. Practical limit on container packages per account

No count-based limit found in GitHub's docs. `content/billing/concepts/product-billing/github-packages.md`:
- "{% data variables.product.prodname_registry %} usage is **free** for
  **public packages**. In addition, data transferred in from any source is
  free." (line 22)
- "**Billing for container image storage:** Container image storage and
  bandwidth for the {% data variables.product.prodname_container_registry %}
  is currently free." (NOTE block, ~line 62)
- Private packages are billed by **storage + data-transfer quota** tied to
  plan (Free: 500MB/1GB·mo, Pro: 2GB/10GB·mo, etc. — shared with Actions
  artifact storage), never by package **count**.

Control arm for the absence claim: searched `github/docs` for a dedicated
quotas/limits page (`content/billing/reference/quotas-and-limits.md` → 404;
confirmed via `curl -s ... | wc -l` → 0 lines) and via GitHub code search
(`gh api "/search/code?q=..."`) — the billing concept page above is the
authoritative source that exists, and it names storage/transfer, never count,
as the constrained resource. "No documented count limit" here means "searched
and found the real quota doc, which quantifies something else," not "gave up
searching."

## GitHub repos touched

- [opencontainers/distribution-spec](https://github.com/opencontainers/distribution-spec) — `spec.md` `<name>`/`<tag>` grammar (findings 1, 7)
- [github/docs](https://github.com/github/docs) — container-registry usage docs, package visibility/inheritance docs, GitHub Packages billing/quota doc (findings 2, 4, 5)
- [github/gh-aw-firewall](https://github.com/github/gh-aw-firewall) — real nested-package control-arm target (`ghcr.io/github/gh-aw-firewall/agent`), referenced from the `gh` repo's own workflow lockfiles (finding 2)
- [cli/gh](https://github.com/cli/gh) — offline KB source tree grepped for `ghcr.io` nested-image usage in its own CI (`gh/.github/workflows/dependabot-triage.lock.yml`)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo: blast-radius grep (finding 6), `ghcr.py`/`ghcr-cleanup.yml` API-call sites (finding 3)

## 6. Blast radius — every site already binding the image name

`grep -rn "dotfiles-devcontainer" .` (excluding `.git/` and this report):
**130 hits across 60 files.** Grouped by category (representative lines; full
list is the grep output, reproducible with the same command):

**Workflow (`.github/workflows/`, 4 hits, 4 files):**
- `build-publish.yml:63` — `IMAGE_NAME: ray-manaloto/dotfiles-devcontainer` (env)
- `ci.yml:52` — same `IMAGE_NAME` env
- `image-analysis.yml:37` — same `IMAGE_NAME` env
- `ghcr-cleanup.yml:52` — `PACKAGE: dotfiles-devcontainer` (job env)

**Python (`python/src/dotfiles_setup/`, 8 hits, 7 files):**
- `config.py:33` — `base_image: str = "ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"`
- `sync.py:106` — `base_repo: str = "ghcr.io/ray-manaloto/dotfiles-devcontainer"`
- `docker.py:285` — `DEFAULT_BASE_IMAGE = "ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"`
- `main.py:1815` — CLI default `"dotfiles-devcontainer"`
- `eval_cases.py:113` — literal `docker pull ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`
- `hook_guard.py:75,304,672` — the `docker pull …dotfiles-devcontainer` deny-rule pattern (see hook-guard category below)

**Contract tokens (`python/verification/suites.toml`, 6 hits):**
- `suites.toml:661-667` — contract `ci.image-name-dotfiles-devcontainer`,
  `per_path_tokens = { ".github/workflows/ci.yml" = ["ray-manaloto/dotfiles-devcontainer"] }`
- `suites.toml:999` — `per_path_tokens = { ".devcontainer/Dockerfile.host-user" = ["ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"] }`
- `suites.toml:1012,1017` — a contract asserting `devcontainer.json` must NOT
  hardcode a bare `"dotfiles-devcontainer:` tag (would shadow the mise/CI
  `BASE_IMAGE` override)

**mise tasks (`mise.toml`, 4 hits — all `env = {...}` defaults inside task bodies):**
- `mise.toml:286` — `[tasks.up]` env default `BASE_IMAGE`
- `mise.toml:352` — `[tasks.dev-rebuild]` env default `BASE_IMAGE`
- `mise.toml:381` — `[tasks.verify-image]` env default `BASE_IMAGE`
- `mise.toml:244` — a comment showing the override form
  (`BASE_IMAGE=ghcr.io/ray-manaloto/dotfiles-devcontainer:latest mise run up`)
- (`mise.local.toml.example:28,50` — two more, as documentation for per-clone overrides)

**hook-guard (`python/src/dotfiles_setup/hook_guard.py` + its tests, 8 hits):**
- `hook_guard.py:304` — the actual deny regex:
  `` _CMD + r"docker\s+(?:image\s+)?pull\b[^;&|\n]*dotfiles-devcontainer" ``
- `hook_guard.py:75,672` — docstrings describing that same rule
- `tests/test_hook_guard.py:32,183,222,484,603` — five tests asserting the
  deny fires (and one, line 222, checking a DIFFERENT image + the literal
  string in an echo doesn't false-positive)

**Docs (top-level + `.devcontainer/`, 6 hits):**
- `AGENTS.md:11,69` — registry name + `:dev` publish description
- `CONTEXT.md:18` — Build-Type-2 description
- `.devcontainer/AGENTS.md:11` — same
- `.devcontainer/Dockerfile.host-user:5` — `ARG BASE_IMAGE=ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`
- `.devcontainer/devcontainer.json:6` — a comment showing the resolved image

**Skills (2 hits, near-duplicate files):**
- `.claude/skills/devcontainer-workflow/SKILL.md:10`
- `.agents/skills/devcontainer-workflow/SKILL.md:10` (this repo carries a
  duplicate under `.agents/` as well as `.claude/`)

**Other config (3 hits):**
- `docker-bake.hcl:6` — `default = "dotfiles-devcontainer"` (bake target var default)
- `.trivyignore:1` — comment naming the image the CVE allowlist is for
- `.gitleaks.toml:7` — `title = "dotfiles-devcontainer"` (gitleaks config title, cosmetic)

**Tests (8 files besides `test_hook_guard.py` above):**
`test_image_smoke.py` (7), `test_ghcr.py` (6), `test_devcontainer_names.py` (4),
`test_sync.py` (3), `test_image_smoke_exec.py` (1), `test_image_manifest.py` (1),
`test_config.py` (1) — asserting the current name/defaults from the python
modules above.

**Not-blast-radius (historical archive, excluded from remediation but part of
the raw count):** ~78 of the 130 hits are inside `docs/research/kb/reports/**`,
`docs/research/runs/**`, `docs/research/trail/**`, `docs/specs/**`,
`docs/ultrapowers/**`, and `missions/**` — past research/spec/audit artifacts
that reference the current name as history. Per `agent-artifact-conventions.md`
these stay verbatim and are NOT rename targets.

**Total: 130 hits / 60 files** (raw grep count); **~52 hits across ~24 files**
are live bindings (workflow/python/contract/mise/hook-guard/docs/skill/bake/
trivy/gitleaks/tests) that a rename must touch; the remainder is archived
research prose.
