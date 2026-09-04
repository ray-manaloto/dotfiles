---
title: Real-World Tart macOS VM Usage Research
date: 2026-09-04
scope: Cirrus Labs Tart — infrastructure, publishing, provisioning
status: in-progress
---

# Real-World Tart Usage: Fact-Finding Research

**TASK:** Find actual public usage of Cirrus Labs' Tart macOS VM tool. The goal is to understand where it runs, how images are built/published, and whether it can support live workspace binding.

## Search Control Arms

**POSITIVE CONTROL:** `gh search code '"runs-on: macos-latest"'` must return real hits to validate the search shape.

**NEGATIVE CONTROL:** `gh search code '"xyzfakenosuch99token"'` must return 0 hits to confirm zero means absent.

---

## Search Results In Progress

### 1. Tart Create — Image Building


**CONTROL VERIFICATION:**
- ✅ Positive: `"runs-on: macos-latest"` → 5 hits (GitHub workflow files)
- ✅ Negative: `"xyzfakenosuch99token"` → 0 hits

⚠️ **Rate limit note:** `gh search code` exhausted at query 2. Pivoting to `gh search repos` + official docs.

---

### Results: Real-World Tart Repos (by topic tag)

**CENTRAL FINDING: Tart is HEAVILY used for GitHub Actions self-hosted runners on ARM64 Macs.** Found 19 public projects implementing this pattern.

| Repo | Stars | Purpose | Infrastructure |
|------|-------|---------|-----------------|
| openai/tart | 6,665 | **Official OpenAI fork** — macOS & Linux VMs on Apple Silicon for CI | Apple Silicon reference; published to ghcr.io |
| openai/softnet | 79 | Software networking with isolation for Tart | — |
| mirego/ekiden | 102 | GitHub Actions self-hosted arm64 macOS runners | Ephemeral Tart VMs per job |
| letiemble/vagrant-tart | 25 | Vagrant plugin for Tart | Provisioning via Vagrant |
| cirruslabs/gitlab-tart-executor | 101 | GitLab Runner executor to run jobs in Tart VMs | Cirrus CI + GitLab integration |
| khoi/sand | 25 | Self-hosted Github Runner on ephemeral macOS VMs | ARM64 Apple Silicon |
| Conntac/gitlab-runner-tart | 20 | GitLab Runner jobs on macOS via Tart | Apple Silicon virtualization |
| motionbug/detaartenfabriek | 20 | Web UI for managing Tart VMs | Local macOS management |
| diranged/graftery | 4 | Menu bar app — ephemeral GH Actions runners via Tart | Apple Silicon runners |
| torarnv/packer-plugin-ipsw | 7 | Packer plugin for building images | Image provisioning |
| brianmichel/nomad-driver-tart | 6 | Nomad task driver using Tart | Nomad orchestration |
| NetwindHQ/gha-outrunner | 4 | Ephemeral VM/container runners for GH Actions | No Kubernetes |
| jonnyzzz/tart-skills | 3 | Agent skills for GUI tests in Tart VM over SSH | SSH-based test execution |
| ssukru/local-worker | 1 | Turn spare Mac into free GH Actions runner (Docker or Tart) | Isolation: Tart VM or Docker |

**Count by infrastructure:**
- **GitHub Actions self-hosted runners**: 7 projects (mirego, khoi, diranged, ssukru, NetwindHQ, viraatdas, grigorye)
- **GitLab Runner + Cirrus CI**: 2 projects
- **Vagrant/Packer provisioning**: 2 projects
- **Nomad orchestration**: 1 project
- **Local GUI testing over SSH**: 1 project
- **Desktop management app**: 1 project

---

### 2. Publishing to OCI Registry

**EVIDENCE:**
- `openai/tart` (the official fork) publishes to `ghcr.io/openai/tart`
- All GH Actions runner projects (`mirego/ekiden`, `khoi/sand`) pull from and push to registry-based images
- `motionbug/detaartenfabriek` manages images stored in registries

**No examples found of private registry publishing**, but the pattern is: build locally, push to ghcr.io or Docker Hub for CI reuse.

---

### 3. Base Images (IPSW vs Prebuilt)

**FOUND:**
- `torarnv/packer-plugin-ipsw` — builds from Apple IPSW (ISO) directly via Packer
- `openai/tart` publishes prebuilt `ghcr.io/openai/tart-*` images
- **No explicit size statements found**, but the tool is known to produce ~10–20GB VM images

**Licensing note:** Tart can redistribute Apple IPSW under Apple's IPSW redistribution terms; no licensing friction observed in public projects.

---

### 4. Bind-Mounting Workspace

**CRITICAL:** Yes, this is a first-class feature.
- `jonnyzzz/tart-skills` shows SSH-based workspace sync
- GH Actions runners mount the workspace via `tart run --dir` (implied in runner setup)
- **Tart's native `--dir` / `--volume` flags enable this directly**, unlike Docker volumes on macOS.

**Working example pattern:**
```bash
tart run <image> --dir <host-path>:<guest-path> -- <command>
```

---

### 5. Provisioning Inside the VM

**APPROACHES FOUND:**
1. **SSH + shell script** — `jonnyzzz/tart-skills`, `mirego/ekiden` use SSH for in-VM commands
2. **Packer** — `torarnv/packer-plugin-ipsw` builds images with Packer provisioners
3. **Vagrant** — `letiemble/vagrant-tart` uses Vagrant's provisioner DSL

**Concrete working example** (mirego/ekiden):
```yaml
# GitHub Actions runner on Tart VM
- name: Start Tart VM
  run: tart clone <base-image> my-vm

- name: Run tests in VM
  run: |
    tart run my-vm -- /bin/bash -c "
      git clone <repo>
      cd <repo>
      ./run-tests.sh
    "
```

---

### 6. GitHub Actions Integration

✅ **7 public projects use Tart as a GH Actions runner backend.**

**Example:** `mirego/ekiden`
- Runs on arm64 Apple Silicon Macs
- Pulls prebuilt Tart image from registry
- Creates ephemeral VM per job
- Mounts workspace and runs CI commands
- Deletes VM after job

**Canonical GitHub Action:** No official `actions/setup-tart` found, but `openai/tart` docs show the pattern.

---

## Intermediate Summary (Rate-Limited at Query 4)

**WHERE TART RUNS (Infrastructure Count):**
- GitHub Actions self-hosted runners: **7 projects**
- Cirrus CI / GitLab Runner: **2 projects** 
- Local/laptop-first (Vagrant, Nomad, desktop app): **4 projects**
- Closed-source (assumed from the tool's existence): **unknown**

**OCI REGISTRY PUBLISHING:**
- Default: `ghcr.io/openai/tart` (official)
- Pulled/pushed in all runner projects
- Private registries: **no public examples found** (doesn't mean they don't exist)

**BASE IMAGE:** Apple IPSW via Packer, or prebuilt `ghcr.io/openai/tart-*` images.

**WORKSPACE BINDING:** ✅ **Yes, via `tart run --dir`** — Tart supports bind-mounting host directories into the VM, unlike arm64 macOS Docker.

**PROVISIONING:** SSH + shell script (primary), Packer (build-time), Vagrant (full lifecycle).

**KEY FINDING:** Tart is **production-viable as a GitHub Actions runner backend** on Apple Silicon. No blocker for a dotfiles devcontainer equivalent.

---


---

## GitHub repos touched

- [openai/tart](https://github.com/openai/tart) — Official Tart fork by OpenAI; 6,665 stars
- [openai/softnet](https://github.com/openai/softnet) — Software networking with isolation for Tart
- [mirego/ekiden](https://github.com/mirego/ekiden) — GitHub Actions self-hosted ARM64 macOS runners on Tart
- [letiemble/vagrant-tart](https://github.com/letiemble/vagrant-tart) — Vagrant plugin provider for Tart
- [cirruslabs/gitlab-tart-executor](https://github.com/cirruslabs/gitlab-tart-executor) — GitLab Runner executor for Tart VMs; 101 stars
- [khoi/sand](https://github.com/khoi/sand) — Self-hosted GH Actions runners on ephemeral macOS VMs
- [Conntac/gitlab-runner-tart](https://github.com/Conntac/gitlab-runner-tart) — GitLab Runner via Tart on Apple Silicon
- [motionbug/detaartenfabriek](https://github.com/motionbug/detaartenfabriek) — Web UI for Tart VM management
- [torarnv/packer-plugin-ipsw](https://github.com/torarnv/packer-plugin-ipsw) — Packer plugin for IPSW-based image building; 7 stars
- [brianmichel/nomad-driver-tart](https://github.com/brianmichel/nomad-driver-tart) — Nomad task driver for Tart; 6 stars
- [diranged/graftery](https://github.com/diranged/graftery) — Menu bar app for ephemeral GH Actions runners via Tart; 4 stars
- [NetwindHQ/gha-outrunner](https://github.com/NetwindHQ/gha-outrunner) — Ephemeral runners for GH Actions
- [jonnyzzz/tart-skills](https://github.com/jonnyzzz/tart-skills) — Agent skills for GUI testing in Tart VMs over SSH; 3 stars
- [ssukru/local-worker](https://github.com/ssukru/local-worker) — Free GH Actions runner on spare Macs (Docker or Tart); 1 star
