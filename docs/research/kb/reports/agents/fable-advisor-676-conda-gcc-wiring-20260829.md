# fable-advisor — #676/#698 conda-gcc wiring decision (2026-08-29)

## Brief given to the agent

> Decision: how to add conda-forge `gcc` as arm64's modern-GCC slot for
> issue #676/#698 (dotfiles repo, devcontainer image), per Ray's 2026-08-10
> ruling recorded in docs/specs/devcontainer-gcc162-dual-arch.md section
> "D31": kayari.org's gcc-latest .deb is x86_64-only by upstream policy
> (permanent, not a gap), so arm64 gets conda-forge `gcc` (16.1.0, same
> coverage linux-64/linux-aarch64: 204 files each) as its modern-GCC
> substitute. amd64 keeps gcc-latest AND would also gain conda gcc (giving
> amd64 3 gcc's: system/apt gcc, conda gcc, gcc-latest; arm64 2: system gcc,
> conda gcc).
>
> Two options weighed:
>
> A) Add `"conda:gcc" = "latest"` UNCONDITIONALLY to
> `.devcontainer/mise-system.toml`'s tool list (next to the many other
> existing `"conda:X" = "latest"` entries). mise resolves conda packages per
> the container's OWN native architecture at install time, so this single
> declaration installs correctly on both amd64 and arm64 with zero
> Dockerfile/TARGETARCH branching.
>
> B) Conditionally install conda gcc only on arm64 via a TARGETARCH branch
> in the Dockerfile (mirroring the existing gcc-latest pattern), keeping
> amd64 at exactly 2 gcc's and arm64 at 2, avoiding a 3rd gcc on amd64 that
> nothing currently asks for.
>
> Files to read: `.devcontainer/mise-system.toml` (lines 1-90 for the conda
> tool list pattern, lines 280-340 for [settings]),
> `.devcontainer/Dockerfile` lines 560-636 (the gcc-latest
> TARGETARCH-conditional block, for contrast), and
> `docs/specs/devcontainer-gcc162-dual-arch.md` around line 1585-1629
> (section "D31") for Ray's actual ruling text — check whether Ray's ruling
> implies amd64 should ALSO get conda gcc (making it 3) or NOT (staying at
> 2, only arm64 gets it).
>
> Give a verdict under 300 words: which option, and why, citing the
> files/lines you read.

## Verbatim report

Verdict: **Option A** — unconditional `"conda:gcc" = "latest"` in
`.devcontainer/mise-system.toml`.

What I read:

- `docs/specs/devcontainer-gcc162-dual-arch.md:1585-1611` (D31): Ray's
  ruling scopes the *asymmetry* to gcc-latest, not to conda gcc. The text
  says arm64's "modern-GCC slot goes to conda-forge gcc" and that the count
  is "3 on amd64, 2 on arm64 **until the conda GCC lands**" — phrased as
  conda gcc landing generally, with no clause excluding amd64. Nothing in
  D31 asks for a second arch branch; `platform_target.GCC_LATEST_ARCHES` is
  explicitly named as "the one place the asymmetry is stated" (`:1609-1610`).
  Option B would create a second place stating it, which that sentence
  argues against.
- `.devcontainer/mise-system.toml:55-83`: sixteen `"conda:X" = "latest"`
  entries, all unconditional, all resolved per-arch by the conda backend. A
  conditional conda install via Dockerfile branching would be the only tool
  in the file treated that way, and would bypass the lockfile tiering
  (`mise-system.lock` locks per published arch via `lockfile_platforms`
  since #698 — a Dockerfile-side conda install gets no lock at all).
- `.devcontainer/Dockerfile:580-613`: the `TARGETARCH` branch exists because
  kayari's artifact *physically cannot* install on arm64. Conda gcc has no
  such constraint (D31's table: identical 204-file coverage both arches), so
  the branch pattern doesn't apply.

The extra gcc on amd64 is a non-cost: conda tools live in isolated per-tool
prefixes behind mise shims, and `ENV PATH` (`Dockerfile:620`) prepends
`/opt/gcc-latest/bin`, so bare `g++` on amd64 still resolves to gcc-latest.

The one risk that decides against B isn't the third compiler — it's that
B's Dockerfile-installed conda gcc would be unlocked and un-Renovate-tracked,
recreating exactly the "nothing tracked the dimension" failure D31
documents (`:1616-1619`).

One thing to verify after landing: amd64's "exactly 3 gcc" self-check (R1)
— confirm it counts 4 now or update the invariant alongside
`GCC_LATEST_ARCHES`.

## Disposition (architect, same session)

Adopted Option A as specced. The declaration was subsequently corrected
from `conda:gcc` to `conda:gxx` after cold review found `gcc` is C-only on
conda-forge (see the sibling report
`opus-cold-review-676-conda-gxx-20260829.md`) — the advisor's architectural
reasoning (unconditional, shared declaration, no Dockerfile branching)
carried through unchanged; only the specific package name was wrong and was
fixed downstream. The advisor's flagged follow-up ("verify the exactly-3-gcc
self-check") was investigated and found to belong to a separate,
still-blocked epic (GCC 16.2, spec requirement R1.4) — explicitly out of
scope for #676/#698, not touched.

## GitHub repos touched

_None — this consult worked entirely from the local spec doc, Dockerfile,
and mise-system.toml; no external repos were fetched._
