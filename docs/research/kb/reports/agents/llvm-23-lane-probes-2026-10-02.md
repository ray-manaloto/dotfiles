# LLVM 23 lane — direct signal probes (2026-10-02, lane llvm23)

Probed 2026-10-03 ~01:55 UTC from the Mac host via `curl` (script: four candidate
detection signals, each with a control arm).

| Signal | Result | Control arm |
|---|---|---|
| `dists/llvm-toolchain-resolute-N/Release` | 21→200, 22→200, **23→200**, 24→404, 25→404 | `-bogus99`→404, so the probe discriminates |
| Unnumbered suite `llvm-toolchain-resolute` | 200; its `clang-24` = `1:24~++20260911…+58c46bae2118` (trunk snapshot) ⇒ trunk major − 1 = **23** | — (cross-checks the row above) |
| GitHub `llvm/llvm-project` releases/latest | 302 → `llvmorg-23.1.2` ⇒ **23** | `llvm/zz-nonexistent-repo-q7` → 404 |
| `llvm.sh` `CURRENT_LLVM_STABLE` | **22** (stale) | — disagrees with the three signals above; matches the grilling report |
| `-23` suite `clang-23` version | `1:23.1.3~++20260922084409+67f4a076a097-1~exp1~20260922084419.77` | — |

Three independent routes (highest numbered suite that serves a Release, trunk
snapshot major − 1, releases/latest) agree on 23. apt.llvm.org's own label
(`llvm.sh`) says 22. That is the staleness the rulings name.

## Pin surfaces that carry the major today (static survey, origin/main be45841a)

- `.devcontainer/mise-system.toml`: 52 active `apt:*-22` pins (lines 220-271), commented doc/examples/win
  entries (278-291), and prose comments (50-60, 87-88, 173-217).
- `.devcontainer/Dockerfile`: suite `llvm-toolchain-%s-22` (line 198), `apt-cache policy clang-22` (201-205),
  `/usr/lib/llvm-22/bin` smoke (305-318), `version 22` / `^22` asserts, and comments (152-160, 292-302).
- `renovate.json`: registryUrl `suite=llvm-toolchain-resolute-22` (line 79), plus description prose.
- python: `apt_repo.py`, `apt_pins.py`, `image.py`, `main.py`; also `hk.pkl` and `mise.toml` mention llvm.

## GitHub repos touched

- [llvm/llvm-project](https://github.com/llvm/llvm-project) — releases/latest redirect

## Ray's ruling (2026-10-02, relayed by coordinator dotfiles-20261002b, recorded in its attested task_plan)

1. The detection rule in `llvm-major-detection-sweep-2026-10-02.md` § Recommendation is APPROVED as written.
2. Fork F1 is resolved as "highest served major below M", not hold-at-P, and reconciled with the "never below the
   current pin" invariant: if GATE(M) is false, TARGET = the highest N in [P, M−1] with GATE(N) true; if none exists,
   FAIL LOUD. The assert-only cross-checks stay.
