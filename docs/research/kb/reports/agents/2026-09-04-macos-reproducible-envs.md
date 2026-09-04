# macOS Reproducible Dev Environments: Field Map

**Research date:** 2026-09-04  
**Question:** If you cannot ship a macOS environment as an image the way Linux ships a container, how do real projects give developers a reproducible macOS dev environment?

## Progress

### 1. nix-darwin / Nix flakes on macOS

Searching for public projects using nix-darwin with CI assertions...


### 1. nix-darwin / Nix flakes on macOS

**What it guarantees:** Reproducible package pinning via Nix flakes (lock file). Does NOT pin Apple SDK, Xcode version, CLT version, or the macOS OS version itself — only packages layered on top via nixpkgs.

**Artifacts produced:** `flake.nix` + `flake.lock` (content-addressed lockfile).

**CI convergence assertion:** Nix builds are deterministic; `flake.lock` pins everything. However, **no CI pattern found that proves a macOS developer environment converges** — most nix-darwin users are either:
  - NixOS users where the entire OS is declarative
  - macOS users who apply locally but don't assert reproducibility in CI

**Real projects:**
- [nix-darwin](https://github.com/nix-darwin/nix-darwin) — the framework itself (5.9k stars)
- [dustinlyons/nixos-config](https://github.com/dustinlyons/nixos-config) (3.6k stars) — builds NixOS, not macOS
- [ryan4yin/nix-darwin-kickstarter](https://github.com/ryan4yin/nix-darwin-kickstarter) (663 stars) — flake template for darwin

**Limitation:** Nix cannot declare the OS version, Xcode, or CLT versions — only packages layered on top. A macOS runner can be on any version, and nix-darwin has no way to enforce OS-level consistency.

---

### 2. Homebrew Bundle (`Brewfile` + `brew bundle check`)

**What it guarantees:** Formula/cask versions pinned to specific releases (semantic versioning or exact pins). **Does NOT guarantee `brew bundle check` passes** — the command is idempotent (reruns succeed) but convergence is **NOT machine-enforced** in CI.

**Artifacts produced:** `Brewfile` (declarative) + optional `Brewfile.lock.json` (deterministic lockfile, opt-in).

**CI convergence assertion:** `brew bundle check` can run on `macos-*` runners, but found NO projects that use it in CI to gate PRs. Most dotfiles repos with Brewfiles have NO CI workflows at all.

**Real projects WITH CI:**
- [MikeMcQuaid/strap](https://github.com/MikeMcQuaid/strap) — **PROVISIONING FROM SCRATCH ON `macos-15` RUNNER:**
  - Workflow: `tests.yml` → `strap_sh` job on `macos-15`
  - **Cleans macOS FIRST** (`sudo rm -rf /opt/homebrew /Applications/Xcode.app /Library/Developer/CommandLineTools`)
  - Runs `bin/strap.sh` to provision from scratch
  - **Reruns `bin/strap.sh` immediately** to verify idempotence
  - Then runs `brew config`, `brew doctor`, and test installations
  - **CI result:** Consistently passing (last 5 runs: all success on main, some expected failures on dependabot branches)

**Limitation:** Does not control Xcode/CLT versions or macOS OS version. But strap's workflow demonstrates **strong convergence assertion**: it wipes and rebuilds twice to verify idempotence.

---

### 3. mise / asdf on macOS

**What it guarantees on macOS:** Runtime version pinning (Node, Python, Go, Ruby, etc.). Does NOT pin system libraries, Xcode, or OS version.

**Artifacts produced:** `mise.toml` + `mise.lock` (exact versions).

**CI convergence assertion:** No projects found that run CI on macOS to assert mise convergence. This repo (dotfiles) uses mise locally but does not validate convergence on a fresh macOS CI runner.

**Why limited on macOS:** Unlike a container, macOS runners arrive with pre-installed software that mise cannot declare or control. The host OS, system libraries, and Xcode are runner-provided and **cannot be reset per job**.

**Real projects:** This repo + others, but none with CI-asserted convergence on macOS.

---

### 4. devbox / devenv / flox (Nix wrappers)

**What they guarantee:** Same as nix-darwin — package pinning via Nix, but NOT OS/SDK/CLT control.

**Real projects:** No major public projects found with CI workflows asserting devbox/devenv convergence on macOS. These tools are newer and adoption is lower than Nix or Homebrew.

---

### 5. Dotfiles managers (chezmoi, Ansible) in CI

**What they guarantee:** File/config convergence. Do NOT control Xcode, OS version, or base system state (only overlay).

**CI convergence assertion:** 
- [chezmoi](https://github.com/twpayne/chezmoi) — has `test-macos` job on `macos-15` (in `main.yml`).
  - Tests chezmoi's OWN functionality on macOS, not user dotfiles convergence.
  - Does NOT wipe the runner and rebuild from scratch.

**Limitation:** Dotfiles managers only layer on top of existing system state. CI assertions are weak — green CI means "chezmoi installed OK on this runner", NOT "your full dev environment converges from scratch".

---

### 6. devcontainer spec on macOS

**Result:** The devcontainer spec (containers.dev) has **NO story for macOS host environments**. It is **strictly Linux containers**. The spec defines:
- `.devcontainer/devcontainer.json` for container config
- Support for WSL2 on Windows (Linux inside WSL)
- Support for Docker Desktop (runs Linux VM underneath)
- **Nothing for bare macOS**

This repo uses devcontainers, but they run on a **Linux amd64 base image**, not on macOS.

---

## Highest-Value Find: CI Provisioning from Scratch

**MikeMcQuaid/strap** is the project that most strongly proves macOS dev environment reproducibility:

| Aspect | Guarantees |
|--------|-----------|
| **Fresh provision** | Yes — cleans /opt/homebrew, Xcode, CLT; runs strap.sh |
| **Idempotence** | Yes — reruns strap.sh immediately; both must pass |
| **CI assertion** | Yes — workflow tests.yml gates on success |
| **What's NOT controlled** | macOS version (macos-15 is runner-provided), Xcode version (latest on the runner) |

**Workflow excerpt:**
```yaml
strap_sh:
  runs-on: macos-15
  steps:
    - uses: actions/checkout@v7
    - name: Cleanup macOS
      run: sudo rm -rf /opt/homebrew /Applications/Xcode.app /Library/Developer/CommandLineTools
    - run: bin/strap.sh
      env:
        STRAP_CI: 1
        STRAP_DEBUG: 1
    - name: Rerun bin/strap.sh
      run: bin/strap.sh
      env:
        STRAP_CI: 1
    - run: brew config && brew doctor
    - run: brew install --build-from-source --formula libfaketime
```

**Control arm (positive):** Runs regularly and passes. **Control arm (negative):** Breakage on dependabot branches sometimes occurs, confirming the test discriminates.

---

## What macOS Provisioning Fails to Guarantee

Unlike a VM image or container snapshot:

| Aspect | VM Image | Container | macOS CI (GitHub Actions) |
|--------|----------|-----------|--------------------------|
| **OS version** | Pinned to snapshot | Pinned (base image tag) | ❌ Runner-provided, drifts |
| **Xcode/CLT** | Pinned to snapshot | ❌ N/A (Linux) | ❌ Latest on runner, no pin |
| **System libraries** | Pinned to snapshot | Pinned (base image) | ❌ Runner-provided |
| **Bit-identical reproduction** | ✅ Yes | ✅ Yes (image digest) | ❌ No (runner changes) |
| **Rollback capability** | ✅ Snapshot | ✅ Image retag | ❌ No |
| **Pre-installed runner software** | ✅ Minimal | ✅ Minimal | ❌ Pre-installed (git, Node, Python, Xcode, etc.) — can change under you |

The **key limitation:** GitHub's macOS runners are **live GitHub-maintained machines**, not immutable images. They receive updates in-place. A declaration like `macos-15` means "latest macOS 15.x", not "exact build XYZ".

---

## GitHub Repos Touched

- [nix-darwin/nix-darwin](https://github.com/nix-darwin/nix-darwin) — Nix framework for macOS
- [dustinlyons/nixos-config](https://github.com/dustinlyons/nixos-config) — nix-darwin example (builds NixOS, not macOS dev env)
- [ryan4yin/nix-darwin-kickstarter](https://github.com/ryan4yin/nix-darwin-kickstarter) — nix-darwin starter template
- [MikeMcQuaid/strap](https://github.com/MikeMcQuaid/strap) — **Fresh provision + idempotence CI** on macos-15
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — Dotfiles manager with macOS CI tests
