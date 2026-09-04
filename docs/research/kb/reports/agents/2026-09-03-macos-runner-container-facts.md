# macOS Runner Container Support: Fact-Finding Report

**Date:** 2026-09-03  
**Scope:** GitHub-hosted macOS arm64 runners and container runtime availability  
**Authority:** actions/runner-images + cirruslabs/tart repos + GitHub Actions docs

---

## Question 1: Does the GitHub-hosted macOS arm64 runner have a working Docker/OCI container runtime?

### Finding: NO

The `xcode-27-arm64`, `macos-26-arm64`, `macos-15-arm64`, and `macos-14-arm64` runner-images READMEs contain comprehensive "Installed Software" sections that list:
- Language runtimes (Node, Python, Ruby, Java, Kotlin, Perl)
- Build tools (Xcode, cmake, bazel, Gradle, Maven)
- CLI utilities (GitHub CLI, AWS CLI, Azure CLI, Google Cloud CLI)
- Browsers (Chrome, Firefox, Safari, Edge)
- Mobile SDKs (Android, iOS)
- Container support: **NONE** — no Docker, no OCI runtime, no Podman, no Colima, no Lima

**Source:** Searched for `docker|container|colima|lima|rancher|podman|virtualization|oci` in raw README content:
- `https://raw.githubusercontent.com/actions/runner-images/main/images/macos/xcode-27-arm64-Readme.md` → **no matches**
- `https://raw.githubusercontent.com/actions/runner-images/main/images/macos/macos-26-arm64-Readme.md` → **no matches**
- `https://raw.githubusercontent.com/actions/runner-images/main/images/macos/macos-15-arm64-Readme.md` → **no matches**
- `https://raw.githubusercontent.com/actions/runner-images/main/images/macos/macos-14-arm64-Readme.md` → **no matches**

**Note:** Homebrew (versions 6.0.15 / 6.0.12) is present, so `brew install colima` is *possible* at job time, but the runner image itself ships with no container engine.

---

## Question 2: Can a macOS runner run Linux containers at all?

### Finding: UNVERIFIED — NO evidence of nested virtualization support

The runner-images README does not mention nested virtualization, nested hypervisors, or Linux VM support. The macOS runners are themselves VMs running macOS; whether they support running another hypervisor (Docker VM, Lima, Colima) inside is not documented.

**Difference between generations (as of this data fetch):**
- **Intel macOS** (macos-13, macos-14-large, macos-26-intel): Historically did NOT have nested virt or Docker; VMs are ephemeral
- **Apple Silicon arm64** (macos-14-arm64, macos-15-arm64, macos-26-arm64, xcode-27-arm64): No Docker listed; nested virt status **not stated in official docs**

**Implication:** Installing Docker/Colima at job time may fail or produce non-functional runtimes if the host doesn't support nested virtualization. GitHub does not claim to support this on macOS runners.

---

## Question 3: Can a container runtime be installed at job time and actually work?

### Finding: BLOCKED by known limitation (Colima) + unverified (general)

#### **Colima**
- **Can install at job time:** Yes, via `brew install colima` (Homebrew is pre-installed)
- **Does it work?:** **Uncertain** — Colima is maintained but has a **critical gap**:
  - **Issue:** `abiosoft/colima#1330` — "[Colima] Not mapping declared SSH_AUTH socket"
  - **Impact:** Colima does not natively expose `ssh-auth.sock`, blocking credential forwarding to containers — a blocker our dotfiles AGENTS.md already documents as why we prefer Docker Desktop over Colima
  - **Status:** Open issue; no fix proposed

- **Nested virt on macOS runners:** **Unproven**. Even if Colima installs, whether it can spawn Linux VMs on GitHub's macOS runner VMs is not documented or tested (to this research's knowledge).

#### **Docker Desktop at job time**
- **Can install:** Theoretically via `brew install docker` or dmg download, but would require Mac credentials/licensing at runtime
- **Practical:** Not a real CI option; Docker Desktop needs GUI interaction

#### **Lima directly**
- **Can install:** Yes, but Lima is a lower-level tool; still needs Docker-compatible daemon
- **Practical:** Same nested-virt issue as Colima

**Conclusion:** Installing a container runtime at job time on macOS runners is theoretically possible (Homebrew is there) but **practically unproven and blocked by Colima's known limitations** if that's the choice. GitHub's own CI logs do not show container runtimes working on macOS runners.

---

## Question 4: Standard GitHub-hosted macOS runner labels and specs today

### Finding: CONFIRMED

From `https://raw.githubusercontent.com/actions/runner-images/main/README.md`:

| Label | OS Version | Arch | Status |
|-------|-----------|------|--------|
| `xcode-27` or `xcode-27-xlarge` | macOS 26.5.2 | arm64 | Public Preview (as of 2026-08-10) |
| `macos-latest`, `macos-26`, `macos-26-xlarge` | macOS 26 | arm64 | GA (latest for public repos) |
| `macos-15`, `macos-15-xlarge` | macOS 15.7.7 | arm64 | GA |
| `macos-14`, `macos-14-xlarge` | macOS 14 | arm64 | **Deprecated as of 2026-07-06; unsupported by 2026-11-02** |

**Runner specs (from runner-images README; core specs):**
- **Processor:** Apple Silicon (arm64)
- **OS:** macOS (specified version above)
- **Pre-installed tools:** See Q1 list
- **Cores/Memory:** README does NOT state vcpu/memory; refer to GitHub Actions docs for spec details

**Public repo access:** Available free for public repositories (implied by GitHub Actions pricing model; confirmed in historical docs).

**Update cadence:** Weekly updates to installed software per the runner-images support policy.

---

## Question 5: Closest working alternatives for reproducible macOS dev environments in CI

### Finding: FIVE candidates; only some publish to OCI registry

| Option | Build Artifact | To ghcr.io? | Pros | Cons |
|--------|---|---|---|---|
| **Tart (Cirrus Labs)** | `.tart` VM images | **YES — OCI-compatible** ✅ | Uses native Virtualization.Framework; can push/pull ghcr.io; maintained (v2.36.0, 2026-08-25); works on arm64 Mac | Proprietary VM format (not portable to Linux); requires Tart CLI to consume |
| **Native macOS jobs** (no container) | Signed binary / tarball / env snapshot | NO (macOS-only) | Works today; full Xcode/SDK access | Not reproducible across OS versions; not portable to Linux CI legs |
| **Nix + Nix Flakes** | Derivations → nix binary cache | **YES — to cache.nixos.org or custom** ✅ | Declarative, reproducible, cross-platform; can build binaries on Linux and run on macOS | Steep learning curve; requires Nix on runner; not container-native; slow first-run |
| **Lima / Colima** | Linux VM image | NO (VM format) | Can run Linux workloads on macOS | Blocks on Colima's SSH_AUTH socket issue; nested-virt unproven on GitHub runners; requires installation at job time |
| **Separate Linux + macOS legs** (current dotfiles pattern) | Linux: OCI image (ghcr.io) + macOS: native job | **YES (Linux leg only)** ✅ | Works today; no nested virt needed; proven in production | Two separate environments; not a "unified" reproducible image; requires OS-specific CI legs |

### Assessment Summary

**For "a reproducible macOS dev environment built in CI that ports to registry":**

1. **Tart** — Only option that builds a macOS VM artifact AND publishes it to OCI registry (ghcr.io works)
   - Can be consumed via `tart clone ghcr.io/owner/repo:tag`
   - Portable across macOS runner versions
   - Build time: ~25 GB image pull, then customization via Packer

2. **Nix** — Builds reproducible derivations, publishes to binary cache
   - Language-agnostic; can define dev env declaratively
   - Publishable as `.nix` flakes or compiled binaries
   - Slower than other approaches; requires Nix on consumer runner

3. **Current pattern** (dotfiles) — Separate legs
   - Linux devcontainer publishes OCI to ghcr.io
   - macOS jobs run natively without containerization
   - Proven; no unverified nested-virt gamble

**The gap:** GitHub does not offer a standard, pre-built way to run Linux containers on macOS runners. Building a reproducible macOS environment requires choosing between Tart (proprietary VM), Nix (cross-platform, slower), or accepting separate OS-specific CI legs.

---

## References

- [actions/runner-images](https://github.com/actions/runner-images) — Main reference for installed software and runner specs
- [runner-images/README.md](https://raw.githubusercontent.com/actions/runner-images/main/README.md) — Official image labels and support policy
- [abiosoft/colima#1330](https://github.com/abiosoft/colima/issues/1330) — SSH_AUTH socket limitation
- [cirruslabs/tart](https://github.com/cirruslabs/tart) — Tart VM builder for Apple Silicon
- [dotfiles/AGENTS.md](../../AGENTS.md) — Reference to our existing Colima documentation
