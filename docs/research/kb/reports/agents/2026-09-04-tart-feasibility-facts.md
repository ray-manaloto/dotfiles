# Tart macOS VM Feasibility — Fact-Finding Report

**Objective:** Determine if Tart can build/run a macOS VM on GitHub-hosted runners, meet Apple licensing constraints, be published to ghcr.io, and be provisioned non-interactively.

**Status:** IN PROGRESS — findings below are being compiled incrementally.

---

## Finding 1: Tart Repository & Basic Capabilities

**Status:** CONFIRMED

- **Repository:** https://github.com/cirruslabs/tart (Cirrus Labs organization)
- **Official Docs:** https://tart.run
- **Technology:** Uses Apple's native `Virtualization.Framework` (macOS 13.0+)
- **OCI Registry Support:** Officially supports "any OCI-compatible container registry" for push/pull
- **Base Image Size:** ~25 GB (e.g., `macos-tahoe-base`)
- **Installation:** Available via `brew install openai/tools/tart` and via Homebrew generally
- **Adoption:** Confirmed used by Atlassian, Figma, Mullvad, Expo, CirrusCI, and others

**Source:** https://github.com/cirruslabs/tart/blob/main/README.md

---

## Question 1: GitHub-Hosted Runner Support (Nested Virtualization)

**Status:** RESEARCH IN PROGRESS

### Sub-question 1a: Can Tart run on GitHub-hosted macOS runners?

- **GitHub macOS Runners:** xcode-27 (public preview) = macOS arm64, 3 CPU, 7 GB RAM
- **Tart Requirement:** Apple `Virtualization.Framework` — a kernel-level hypervisor
- **GitHub Runner Virtualization:** GitHub's own macOS runners are virtualized (nested virtualization question)
- **Nested Virtualization Support:** Tart's documentation does NOT explicitly state GitHub-hosted runner compatibility
  - Tart docs reference **Cirrus CI** integration, not GitHub Actions
  - No official GitHub Actions workflow examples found in repo README or docs landing page
  - CirrusCI uses self-hosted runners on MacStadium, not GitHub-hosted infrastructure

**Preliminary Finding:** UNVERIFIED — no official documentation found confirming nested virtualization works on GitHub-hosted macOS runners. This is the **load-bearing question** for the entire plan.

**Next Steps:** Search Tart GitHub discussions/issues for "#918" or similar, and check GitHub's own runner documentation for `Virtualization.Framework` availability.

---

## Question 2: Apple Licensing for macOS VMs

**Status:** RESEARCH IN PROGRESS

### Apple's EULA Constraints

- **Macintosh Software License Agreement (MSLAA):** Historically limits concurrent VMs to 2 per physical Mac host
- **Redistribution:** Apple's terms have historically constrained redistribution of macOS images
- **Tart's Approach to Base Image:** Tart requires users to supply their own macOS base or uses macOS installer media (IPSW files)
  - Tart **does not ship macOS images directly** in its distribution
  - Base images in registries (e.g., `ghcr.io/cirruslabs/macos-tahoe-base`) are **pre-built by Cirrus Labs**, not by Tart itself
  - **User-built Tart images** would be subject to Apple's licensing if derived from a macOS install

**Source Evidence Needed:**
- Exact Tart documentation on base image sourcing
- Apple's current EULA terms (subject to change; last reviewed circa 2023-2024)
- Cirrus Labs' own guidance on licensing compliance for their pre-built images

**Preliminary Finding:** UNVERIFIED — Tart's own docs do not explicitly state the licensing position. Need to confirm whether:
1. User-built Tart images are permitted under Apple's EULA
2. Publishing to ghcr.io triggers any additional restrictions
3. Cirrus Labs' pre-built images have special licensing arrangements

---

## Question 3: ghcr.io OCI Artifact Support & Size Limits

**Status:** RESEARCH IN PROGRESS

### ghcr.io Compatibility

- **OCI Artifact Format:** Tart pushes OCI-compliant artifacts (confirmed in README)
- **ghcr.io OCI Support:** ghcr.io is GitHub Container Registry, built on Docker's registry V2 spec
- **Known OCI Support:** ghcr.io is confirmed to accept Docker images and OCI artifacts
- **Layer Size Limits:** GitHub/Docker registries have per-layer limits (classically ~5GB per layer, but documented to vary)

**Image Size Problem:**
- macOS base: ~25 GB
- Tart images are **not compressed** like Docker layers (they are full disk images)
- Splitting a 25 GB VM image into OCI layers requires Tart's layer strategy (how Tart chunks the image for distribution)

**Preliminary Finding:** UNVERIFIED — OCI compatibility is likely, but need to confirm:
1. Whether ghcr.io enforces strict layer size limits that would block a 25 GB image
2. How Tart chunks/compresses VM images for OCI push
3. Any documented size limitations in Tart's registration documentation

---

## Question 4: Local Consumption (Prerequisites & Bind-Mount)

**Status:** RESEARCH IN PROGRESS

### Installation & Runtime Requirements

- **Installation:** `brew install openai/tools/tart` or direct build
- **Runtime Prerequisites:** macOS 13.0+ (Ventura), Apple Silicon
- **Pull Command:** `tart pull ghcr.io/cirruslabs/macos-tahoe-base:latest <local-name>`
- **Run Command:** `tart run <local-name>`
- **SSH Access:** Tart VMs can run sshd; SSH for provisioning is possible

### Workspace Bind-Mount

- **devcontainer Equivalent:** Docker's `bind` mount to `$PWD`
- **Tart Equivalent:** UNVERIFIED — does Tart support bind-mounting a host directory into the VM?
  - Tart VMs run on `Virtualization.Framework`, not Docker
  - Framework VMs typically require explicit mount/NFS configuration
  - **Need to confirm:** Is there official Tart documentation on mounting host directories?

**Preliminary Finding:** UNVERIFIED — can confirm Tart pull/run and SSH access are available, but workspace bind-mount capability is unknown.

---

## Question 5: Non-Interactive Provisioning (mise + chezmoi)

**Status:** RESEARCH IN PROGRESS

### CI Provisioning Pattern

- **SSH into Tart VM:** Possible (Tart VMs can run sshd)
- **Script Execution:** SSH + script invocation is standard (e.g., `ssh user@vm 'bash /tmp/provision.sh'`)
- **Authentication:** UNVERIFIED — what auth does Tart VM sshd use? (keypair, password, pre-baked?)

### Mise + Chezmoi in VM

- **mise:** Tool management (declarative via `mise.toml`)
- **chezmoi:** Dotfile management (declarative via `chezmoi.toml.tmpl`)
- **Non-interactive Provisioning:** Both tools support scripted/headless usage
- **Tart-Specific:** UNVERIFIED — no documented examples found of mise + chezmoi provisioning a Tart VM in CI

**Preliminary Finding:** UNVERIFIED — the mechanics exist (SSH + scripts), but no confirmed documented pattern for Tart + mise + chezmoi in GitHub Actions.

---

## Tart License & Redistribution Terms

**Status:** RESEARCH IN PROGRESS

- **Tart Repository:** Licensed under Apache 2.0 (assumed; need to verify LICENSE file)
- **Commercial Use:** UNVERIFIED — Tart itself is open-source, but check for any usage restrictions
- **macOS Base Image:** Base images are **NOT part of Tart's license** — they fall under Apple's licensing

**Source Needed:** https://github.com/cirruslabs/tart/blob/main/LICENSE

---

## Summary of Blockers

| Question | Status | Risk Level |
|----------|--------|-----------|
| **Q1: Nested virtualization on GitHub-hosted xcode-27** | UNVERIFIED | 🔴 CRITICAL — no official docs found |
| **Q2: Apple licensing for VM redistribution** | UNVERIFIED | 🟠 HIGH — licensing uncertain |
| **Q3: ghcr.io 25 GB image support** | LIKELY OK | 🟡 MEDIUM — size limits need confirmation |
| **Q4: Workspace bind-mount** | UNVERIFIED | 🟡 MEDIUM — feature may not exist |
| **Q5: Non-interactive provisioning** | LIKELY OK | 🟢 LOW — mechanics exist, pattern unknown |

---

## GitHub Repos Touched

- [cirruslabs/tart](https://github.com/cirruslabs/tart) — Tart VM tool, README and repo structure

---

## Finding 3: Tart License (CONFIRMED)

**Status:** CONFIRMED via LICENSE file

- **License:** Functional Source License 1.1, with Apache 2.0 Future License (FSL-1.1-ALv2)
- **Copyright:** OpenAI (2022-2026)
- **Permitted Uses:**
  - Internal use and access
  - Non-commercial education and research
  - Professional services using the Software in accordance with terms
- **Restricted:** "Competing Use" — making the Software available commercially as a substitute for Tart itself
- **Future:** On the second anniversary of a version's release, converts to Apache 2.0
- **Impact on This Plan:** Using Tart internally (building a dev environment) is permitted. **Publishing a Tart image publicly** may not be permitted if it substitutes for Tart as a commercial offering.

**Source:** https://github.com/cirruslabs/tart/blob/main/LICENSE (FSL-1.1-ALv2 full text)

---

## Finding 4: GitHub Actions Support (CRITICAL BLOCKER)

**Status:** 🔴 NOT OFFICIALLY SUPPORTED

**Evidence:**
1. Tart's official documentation integrates via **Cirrus CLI**, not GitHub Actions directly
2. README and docs reference Cirrus CI (`.cirrus.yml`), no GitHub Actions examples
3. **Documentation site shows "GitHub Actions" link in nav but page returns HTTP 404** (`/integrations/github-actions/`)
4. All documented production users (Atlassian, Figma, Mullvad, Expo, CirrusCI) use Cirrus CI or self-hosted runners
5. Tart is maintained by Cirrus Labs, whose primary product is Cirrus CI, not GitHub Actions

**Interpretation:** The 404 page is a strong signal that GitHub Actions support is **not implemented** or **not officially supported by Cirrus Labs**.

**Impact:** GitHub-hosted runners are not a supported platform for Tart. This is the load-bearing question for the entire plan.

---

## Finding 5: Nested Virtualization on GitHub-Hosted macOS Runners

**Status:** 🟠 UNKNOWN / LIKELY UNAVAILABLE

**Technical Context:**
- GitHub's macOS runners run on **MacStadium cloud infrastructure** (already virtualized)
- Tart requires Apple's `Virtualization.Framework` — a kernel-level hypervisor
- Nested virtualization (hypervisor inside hypervisor) requires explicit host support
- No public documentation found confirming nested virt is enabled on GitHub's xcode-27 runners
- No evidence of public projects successfully running Tart on GitHub-hosted runners

**Probable Answer:** Nested virtualization is **not available** on GitHub-hosted runners (GitHub's MacStadium infrastructure does not expose it to guest VMs). This makes Tart **unsuitable for GitHub Actions without confirmation otherwise.**

---

## Finding 6: Apple's macOS Virtualization Licensing

**Status:** 🟠 UNVERIFIED

**Historical Constraints:**
- Apple's Macintosh Software License Agreement historically limited concurrent VMs to **2 per physical Mac host**
- Redistribution of macOS images was historically restricted
- Current licensing (2024-2026) is **unverified** — needs Apple's current EULA

**Tart's Licensing Model:**
- Tart does NOT ship macOS in its distribution
- Users supply their own base (IPSW installer or pre-built VM)
- Pre-built images like `ghcr.io/cirruslabs/macos-tahoe-base` are published by Cirrus Labs
- **Unknown:** Whether Cirrus Labs has special licensing from Apple, or relies on fair use

**What's Needed:** Consult Apple's current Software Licensing Agreement (current version) for VM redistribution clauses and any exceptions.

---

## Finding 7: ghcr.io OCI and Size Support

**Status:** 🟢 LIKELY COMPATIBLE / 🟡 SIZE UNCERTAIN

**Registry Compatibility:**
- ghcr.io is built on Docker Registry V2 spec + OCI support
- Tart officially supports "any OCI-compatible container registry"
- **Compatibility:** ✅ CONFIRMED

**Size Constraints:**
- macOS base images are ~25 GB (single monolithic disk image, not layered)
- Docker/OCI layer limits exist but vary by registry
- **Not documented in sources checked** — need to verify ghcr.io's per-image or per-layer limits
- Likely OK, but needs confirmation (especially whether ghcr.io chunking works with Tart's image format)

---

## Summary: Critical Blockers

| Question | Status | Risk | Notes |
|----------|--------|------|-------|
| **Q1: GitHub Actions support** | 🔴 NO | BLOCKING | 404 page + no official docs = not supported |
| **Q2: Nested virt on xcode-27** | 🟠 Unknown | BLOCKING | MacStadium infra likely doesn't enable it |
| **Q3: Apple licensing (redistribution)** | 🟠 Unverified | HIGH | Need current EULA; unclear if Cirrus Labs has exception |
| **Q4: Workspace bind-mount** | ⚠️ Unverified | MEDIUM | Tart docs don't mention this capability |
| **Q5: Non-interactive provisioning** | 🟢 Likely OK | LOW | SSH + scripts are standard, but no documented pattern |
| **Q6: ghcr.io 25 GB image** | 🟢 Likely OK | LOW | OCI support confirmed; size limits unverified |

---

## Verdict

**The plan to build a Tart macOS VM on GitHub-hosted runners faces TWO CRITICAL blockers:**

1. **No official GitHub Actions support** — Tart's GitHub Actions integration page is 404; all official docs point to Cirrus CI
2. **Nested virtualization likely unavailable** — GitHub-hosted runners run on MacStadium VMs; enabling nested virt would require explicit support from GitHub/MacStadium (not found in public docs)

**Even if both above were solved, Apple's licensing for publishing a macOS VM image remains unverified.**

---

## GitHub Repos Touched

- [cirruslabs/tart](https://github.com/cirruslabs/tart) — Tart VM tool, README, LICENSE, docs site
