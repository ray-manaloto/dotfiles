# #1523 — /code-review high

- Target: merge SHA `4facf6433133ccc7646f0f026ab47967871dabd8` (the target, not a base)
- Lens: built-in `/code-review high` (forked, task `acc15f2691a62f320`, 29 tool uses, 232s)
- Verdict: **FINDINGS** — 8 (severity triage + second read below the verbatim block)

## Verbatim result

```json
[
  {
    "file": "python/verification/suites.toml",
    "line": 199,
    "summary": "The new `build.devcontainer-no-secret-argv` contract uses `require_lines`. That handler only checks that the line appears somewhere in the file, so the contract can stay green while the leak comes back.",
    "failure_scenario": "`require_lines` (verify.py:398-404) builds a set of every normalised line in the file. It does not parse JSONC and does not skip comments. Example: someone later adds `\"userEnvProbe\": \"loginInteractiveShell\",` further down devcontainer.json. jsonc-parser keeps the last duplicate key, so the CLI goes back to the login-shell probe and puts every Doppler secret on the host `docker exec -e` argv again. The original line is still there, so `mise run verify` passes. The same happens if the line is moved inside a `/* ... */` block comment. The commit message says the contract 'fails on value change, deletion and commenting-out', but that only holds for `//` comments."
  },
  {
    "file": ".devcontainer/devcontainer.json",
    "line": 128,
    "summary": "Saying the probe 'added nothing but the leak' is wrong. Lifecycle hooks and non-login `devcontainer exec` used to get mise's activated `[env]`, and now they don't. That changes what the smoke tests actually check.",
    "failure_scenario": "mise-system.toml `[env]` sets `_.path=[/usr/lib/llvm-22/bin]`, `CC=gcc`, `CXX=g++`, `LANG`/`LC_ALL=C.UTF-8` and `HK_MISE=1`. `docker exec`'s Config.Env has none of these. `mise run smoke` (mise.toml:487) and postCreateCommand both run `scripts/devcontainer-smoke.sh` without a login shell. So line 49, `which clang++ python uv hk`, now finds `/opt/clang-p2996/bin/clang++` (the Bloomberg fork on Config.Env PATH) and no longer the llvm-22 clang++. The compiler-presence check passes even if llvm-22's unversioned binaries are missing. Any non-shim command in those hooks also runs with no locale and no CC/CXX."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 195,
    "summary": "The contract checks the source text of one file, not the configuration the CLI actually ends up using. A deeper check already exists: the `devcontainer read-configuration` layer in hk.pkl.",
    "failure_scenario": "The CLI merges image `devcontainer.metadata` labels and feature metadata into the final config. A text match on devcontainer.json cannot see a different `userEnvProbe` coming from the merged config, nor a duplicate key. hk.pkl:137 already runs `devcontainer read-configuration`. Running it with `--include-merged-configuration` and asserting `mergedConfiguration.userEnvProbe == \"none\"` would check what the CLI will really use, and it fixes finding 1 as well."
  },
  {
    "file": ".devcontainer/devcontainer.json",
    "line": 112,
    "summary": "The root cause is still there. All Doppler secrets go into the container's Config.Env through `runArgs --env-file`, so anything on the host that can reach the docker socket can still read them. This change only closes one way they leaked out.",
    "failure_scenario": "On the host, `docker inspect <container> --format '{{.Config.Env}}'`, or any tool that dumps container config, still prints DB_PASSWORD and every other secret, with no `ps` needed. The suite says secrets 'must never reach a HOST' surface, but only the argv is enforced. The deeper fix is runtime resolution inside the container, which is #83 (fnox/doppler in-container); this change stops the symptom, not the cause."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 200,
    "summary": "The required line includes the trailing comma and has to stay on a single line. A harmless reformat would make the gate fail for no real reason.",
    "failure_scenario": "Move `userEnvProbe` to the last property of its object, or let a JSONC formatter drop the trailing comma or reflow the key and value. Each line becomes `\"userEnvProbe\": \"none\"` without the comma. `_normalise` only collapses whitespace, so the gate fails even though the effective value is still `none`. This is the formatter tripwire the require_lines docstring says it avoids."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 192,
    "summary": "No pytest pins the new contract's fail arm. The commit message says it was armed by hand only, so nothing in CI catches it if the gate stops working.",
    "failure_scenario": "Example: a later edit changes the handler, the path or the line literal, and the suite stops matching anything meaningful. tests/ never mutates devcontainer.json to check that this suite fails. The only evidence the gate can fail is the alpine probe described in the commit message, which nothing re-runs."
  },
  {
    "file": ".devcontainer/devcontainer.json",
    "line": 120,
    "summary": "The new security invariant is not added to the 'Secrets Injection (Doppler)' section of `.devcontainer/AGENTS.md`, which is the doc that describes the S1 path.",
    "failure_scenario": "`.claude/rules/tool-currency-and-native-first.md` rule 5 says: 'Sync the describing docs/skills in the SAME change'. `.devcontainer/AGENTS.md:44-65` describes the env-file flow without the userEnvProbe requirement. Someone working from that doc, for example to restore login-shell PATH in hooks, gets no warning that the default probe leaks every secret to the host argv."
  },
  {
    "file": "python/verification/suites.toml",
    "line": 193,
    "summary": "The same long explanation of the leak and how it was armed is copied three times: the devcontainer.json comment, the suite description and the commit message.",
    "failure_scenario": "Three copies of the same story will drift apart. The suite description already says 'in-container visibility is unchanged', which finding 2 shows is not true for mise-activated env. The suite description could be one line that points to the devcontainer.json comment, so the reasoning lives in one place."
  }
]
```

## Lane triage (second read) — appended after receipt

Re-read at `785c3708` (current main HEAD); the lines are unchanged since the merge.

| # | Severity | Second read | Disposition |
|---|---|---|---|
| 1 | MED | CONFIRMED. `verify.py:398-404` reduces each file to a set of normalised lines, so a later duplicate `"userEnvProbe": "loginInteractiveShell"` key or a `/* */` block around the line leaves the gate green. | Issue A (gate robustness), with 3, 5 and 6 |
| 2 | MED | CONFIRMED. `scripts/devcontainer-smoke.sh:48` runs `which clang++ python uv hk` outside a login shell under `devcontainer exec` (`mise.toml:493`) and postCreate (`devcontainer.json:246`). Config.Env PATH is `/opt/gcc-latest/bin:/opt/clang-p2996/bin:…` (`Dockerfile:628`). mise's `_.path=/usr/lib/llvm-22/bin`, CC/CXX, LC_ALL and HK_MISE (`mise-system.toml:373-381`) are therefore absent, so the tier-1 `which clang++` now resolves the p2996 fork, not llvm-22. Before #1523 the default probe imported the login-shell env. | Issue B (smoke lost mise env) |
| 3 | LOW | Fix proposal for 1: assert `mergedConfiguration.userEnvProbe` through `devcontainer read-configuration --include-merged-configuration`. | Folded into A |
| 4 | LOW / posture | Correct that `docker inspect` still shows Config.Env. Secrets-in-env is Ray's 2026-08-02 decision (`secrets-out-of-the-shell-env.md`), and docker-socket access is already host-user equivalent. #83 is CLOSED. | No issue. Noted for the coordinator |
| 5 | LOW | Confirmed. The trailing comma is part of the required literal. | Folded into A |
| 6 | LOW | Confirmed. There is no pytest fail arm for this suite. | Folded into A |
| 7 | LOW | `.devcontainer/AGENTS.md` does not mention the invariant. | Folded into B (doc sync) |
| 8 | NIT | The rationale is duplicated in 3 places. | None |

Existing-issue search (`gh api /search/issues`, control `devcontainer` → 433 hits): `userEnvProbe` → only #1523/#668/#1526, all closed. Neither A nor B is a duplicate.

## GitHub repos touched

_None._ (local git objects only)

## Issues filed

- A → [#1593](https://github.com/ray-manaloto/dotfiles/issues/1593)
- B → [#1594](https://github.com/ray-manaloto/dotfiles/issues/1594)
