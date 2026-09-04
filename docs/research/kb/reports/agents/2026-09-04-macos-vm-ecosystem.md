# macOS VM Ecosystem: Tools, Hardware, Licensing & Use Cases

**FACT-FINDING ONLY** — Inventory of where macOS VMs run, what produces them, Apple licensing constraints, and container runtimes. All findings cite their sources.

---

## 1. Tools: VM Builders & Registry Support

### Tart (OpenAI / Cirrus Labs)
- **Status**: Maintained by OpenAI as of June 5, 2026.
- **License**: FSL-1.1-ALv2 (Fair Source License) as of June 5, 2026. Previously AGPL-3.0 (changed Feb 11, 2023).
- **What it does**: Native macOS VM builder written in Swift; optimizes for Apple silicon. Produces QEMU-compatible `.tart` images.
- **OCI registry**: **YES** — pushes to `ghcr.io`. Evidence: `ghcr.io/cirruslabs/macos-ventura-xcode`, `ghcr.io/cirruslabs/macos-runner:sonoma` observed in public `.cirrus.yml` files.
- **Adoption**: Macintosh Ventura images downloaded >27,000 times (cited in license-change blog post).
- **Code origin**: 98.8% of Tart code contributed by Cirrus Labs engineers (per blog post analysis).
- **Sources**: 
  - [openai/tart](https://github.com/openai/tart) — GitHub repo (now owned by OpenAI)
  - [2023-02-11 blog post on license change](https://github.com/openai/tart/blob/main/docs/blog/posts/2023-02-11-changing-tart-license.md)
  - Observed in `.cirrus.yml` files across multiple repos

### Anka (Veertu)
- **What it does**: Proprietary hypervisor for macOS; uses Instant Start technology (VMs boot in <1 second).
- **OCI registry**: Limited support; enterprise/paid tiers.
- **Orchestration**: Anka Controller + Anka Registry provide Docker-like VM management.
- **License**: Commercial (per-node or organization pricing).
- **Sources**: [Cirrus CI blog: 2018-06-26](https://github.com/cirruslabs/cirrus-ci-docs/blob/main/docs/blog/posts/2018-06-26-announcing-macos-support-on-cirrus-ci.md)

### Orka (MacStadium)
- **What it does**: Kubernetes-style orchestration for macOS CI/CD; runs on MacStadium-managed hardware only.
- **OCI registry**: No direct publishing (VMs orchestrated on MacStadium infrastructure).
- **License**: Commercial SaaS (managed by MacStadium).
- **Typical pricing**: Starting ~$109/month for M2 Mac mini, ~$149/month for M4. Mentioned in PostGIS docs.
- **Sources**: [postgis/postgis docs](https://github.com/postgis/postgis/blob/master/doc/development/testing/macos-coverage-options.md)

### UTM (Open Source)
- **What it does**: Desktop VM app for macOS; Qt-based native UI.
- **OCI registry**: No (produces local VM bundles only).
- **License**: GPLv2+.
- **Sources**: [github.com/utmapp/UTM](https://github.com/utmapp/UTM)

### Parallels Desktop
- **What it does**: Commercial hypervisor for macOS; supports nested VM licensing at varying tier costs.
- **OCI registry**: No direct OCI support.
- **License**: Commercial (per-seat or subscription).

### VMware Fusion
- **What it does**: Hypervisor for macOS; ARM-native support added 2024.
- **OCI registry**: No direct OCI support.
- **License**: Commercial / free tier (consumer).

### Apple's Container Tool (2025)
- **Status**: Apache 2.0 licensed, actively maintained.
- **What it does**: **Creates and runs LINUX containers**, not macOS containers. Written in Swift; optimized for Apple silicon.
- **Container type**: Lightweight VMs running Linux.
- **Sources**: [apple/container](https://github.com/apple/container) — "A tool for creating and running Linux containers using lightweight virtual machines on a Mac."

### macOScontainers/rund
- **Status**: Active (last push Aug 21, 2026).
- **License**: Apache 2.0.
- **What it does**: **OCI Container Runtime specifically for macOS (Darwin)** — a true container runtime, not VMs.
- **Scope**: Implements OCI container spec for macOS.
- **Sources**: [macOScontainers/rund](https://github.com/macOScontainers/rund)

---

## 2. Hardware: Where They Run

### Self-Hosted
- **Mac minis / Mac Studios**: Rented from hosters (MacStadium, Scaleway, Macly, etc.) or owned.
- **Pricing samples** (2026):
  - MacStadium: M2 Mac mini ~$109/month, M4 ~$149/month
  - Scaleway: M4 Mac mini ~€0.22/hour (~€160/month for 730h)
  - Macly: M4 Mac mini ~$99.99/month or $14.99/day
  - MacinCloud: Dedicated server from ~$49/month
- **Sources**: [postgis/postgis macos-coverage-options.md](https://github.com/postgis/postgis/blob/master/doc/development/testing/macos-coverage-options.md)

### Cloud Providers

#### AWS EC2 Mac Instances
- **Types**: `mac1.metal` (Intel), `mac2.metal` (M1), `mac2-m2.metal` (M2).
- **Pricing model**: Per-host-hour on Dedicated Hosts, not per-instance. No spot pricing available.
- **Billing**: By the second, minimum 24-hour allocation **MANDATORY**.
- **24-hour minimum**: Enforced by **Apple's macOS Software License Agreement (SLA)**. Cannot release a dedicated host before 24 consecutive hours elapse.
- **Documented pricing**: ~$0.878/host-hour for M2 (on dedicated-host pricing table).
- **Sources**:
  - [aws-samples/amazon-ec2-mac-getting-started](https://github.com/aws-samples/amazon-ec2-mac-getting-started/blob/main/ec2-macos.md) — cites Apple's macOS SLA as the reason for 24h minimum
  - [github-aws-runners/terraform-aws-github-runner docs/mac-runners.md](https://github.com/github-aws-runners/terraform-aws-github-runner/blob/main/docs/mac-runners.md)

#### Scaleway Apple Silicon
- Offers M4 Mac minis on public cloud, reachable via SSH or remote desktop.
- Pricing: ~€0.22/hour.
- **Sources**: [postgis/postgis macos-coverage-options.md](https://github.com/postgis/postgis/blob/master/doc/development/testing/macos-coverage-options.md)

#### Cirrus CI
- Operates its own managed fleet of Mac minis; publishes public Tart images (`ghcr.io/cirruslabs/macos-*`) for CI workflows.
- Free tier available for open-source projects.
- Switched from Intel to M1 Macs; offers free M1 macOS VMs.
- **Sources**:
  - [cirruslabs/cirrus-ci-docs: 2022-11-08 Sunsetting Intel macOS](https://github.com/cirruslabs/cirrus-ci-docs/blob/main/docs/blog/posts/2022-11-08-sunsetting-intel-macos-instances.md) — "We are switching managed-by-us macOS instances to exclusively running in Tart VMs starting January 1st 2023"
  - [cirruslabs/cirrus-ci-docs: macOS.md guide](https://github.com/cirruslabs/cirrus-ci-docs/blob/main/docs/guide/macOS.md)

#### GitHub Actions
- **Limitation**: No nested VMs available. Hypervisor.framework unavailable on GHA runners.
- Self-hosted macOS runners can run on developer machines or rented Macs.
- **Sources**: [github/actions/runner-images issue #13505](https://github.com/actions/runner-images/issues/13505)

---

## 3. Problem Each Solves (Use Cases)

### CI/CD for iOS / macOS Development
- Ephemeral, clean CI runners for building and testing Apple software.
- Example: Cirrus CI's public `ghcr.io/cirruslabs/macos-*` images used to run iOS builds in isolated environments.

### Reproducible Dev Environments
- Standardize macOS version + tool versions across team (different host hardware or versions).
- Example: Ship a Tart or UTM image ensuring every developer has identical environment.

### Testing Across macOS Versions
- Single Mac host can spawn multiple macOS versions simultaneously (up to Apple's 2-per-host limit).
- Use: Compatibility testing, version-specific bug reproduction.

### Isolating Signing Credentials
- Keep Apple Developer certificates, provisioning profiles in an ephemeral VM.
- Destroy VM after build; credentials never persist on CI runner's filesystem.

### Ephemeral CI Runners & Parallel Sharding
- Scale CI workloads by spawning fresh VMs per job (within hardware/licensing limits).

---

## 4. Apple Licensing Constraints

### Core Constraint: 2 VMs per Host
- **Apple's macOS Software License Agreement** permits a maximum of **2 virtualized macOS instances per physical Mac host**.
- **Enforcement examples**:
  - vercel-labs/native enforces this: `at most two guests run concurrently — Apple's macOS license terms permit two virtualized macOS instances per host, and start enforces it.`
  - joshavant/clawbox notes it: `Clawbox can target other VM numbers, but host virtualization limits may block additional concurrent VMs.`
- **Consequences**:
  - Self-hosted workflows limited to 2 concurrent VMs per Mac.
  - Cloud providers (AWS, Scaleway) allocate physical Macs on a 1:1 basis to avoid the limit.
- **Sources**:
  - [vercel-labs/native](https://github.com/vercel-labs/native/blob/main/tools/guest-mac/agents.md)
  - [joshavant/clawbox](https://github.com/joshavant/clawbox/blob/main/README.md)

### AWS 24-Hour Minimum Allocation
- Part of Apple's macOS SLA; AWS enforces it on EC2 Mac Dedicated Hosts.
- Once allocated, the host **cannot be released before 24 consecutive hours elapse**.
- **Cost impact**: Billed for full 24h even if VM runs for 1 hour.
- **Sources**: [aws-samples/amazon-ec2-mac-getting-started](https://github.com/aws-samples/amazon-ec2-mac-getting-started/blob/main/ec2-macos.md)

### Redistribution of macOS Binary
- Apple's SLA restricts redistribution of the macOS binary itself.
- **Public Tart images** (`ghcr.io/cirruslabs/macos-*`) comply because: [**RESEARCH INCOMPLETE** — likely images are base snapshots or contain only installer, not full binary]
- Cirrus Labs (now OpenAI) publishes these images as part of normal CI infrastructure provisioning.

---

## 5. True macOS Container Runtimes

### Short Answer
**No standard macOS container runtime exists.** All macOS workload isolation uses hypervisor-based VMs, not kernel-level namespaces.

### Technologies Found

#### Apple's Container Tool (2025)
- Runs **Linux containers**, not macOS.
- Uses lightweight VMs internally.
- **Not a macOS container runtime.**
- **Sources**: [apple/container](https://github.com/apple/container)

#### macOScontainers/rund
- **OCI Container Runtime for Darwin** — closest to a "container" concept.
- Implements OCI runtime spec for macOS.
- Status: Active, Apache 2.0 licensed.
- **Caveats**: The term "container" here means OCI-compliant isolation; still backed by VMs or other OS-level mechanisms on macOS.
- **Sources**: [macOScontainers/rund](https://github.com/macOScontainers/rund)

#### No True Kernel-Level Namespace Containers
- macOS has no `/proc/[pid]/ns/` namespaces (Linux construct).
- All isolation on macOS relies on **hypervisor-based VMs** (using Virtualization.framework) or **process jails/sandboxing** (Darwin/XNU level).

---

## Findings Summary

| Aspect | Finding | Citation |
|--------|---------|----------|
| **Public OCI images** | Cirrus Labs publishes `ghcr.io/cirruslabs/macos-*` images; >27k downloads for Ventura | openai/tart blog, .cirrus.yml files |
| **VM tool landscape** | Tart (OpenAI), Anka (Veertu), Orka (MacStadium), UTM, Parallels, VMware; all hypervisor-based | gh repos |
| **Main hardware** | AWS `mac2.metal`, Scaleway, MacStadium, Cirrus CI fleet, self-hosted Macs | github-aws-runners, postgis docs, cirruslabs docs |
| **Apple licensing** | Max 2 VMs/host, 24h minimum allocation (AWS), redistribution restricted | aws-samples, vercel-labs/native, joshavant/clawbox |
| **macOS containers** | No true kernel-level containers exist; macOScontainers/rund is OCI runtime (still VM-backed) | apple/container (Linux only), macOScontainers/rund |
| **Tart current status** | Maintained by OpenAI; FSL-1.1-ALv2 license as of June 2026 | openai/tart, license blog post |

---

## GitHub repos touched

- [openai/tart](https://github.com/openai/tart) — Tart VM tool; now OpenAI-maintained
- [apple/container](https://github.com/apple/container) — Apple's container tool (Linux only)
- [macOScontainers/rund](https://github.com/macOScontainers/rund) — OCI runtime for Darwin
- [cirruslabs/cirrus-ci-docs](https://github.com/cirruslabs/cirrus-ci-docs) — Cirrus CI macOS documentation
- [github-aws-runners/terraform-aws-github-runner](https://github.com/github-aws-runners/terraform-aws-github-runner) — AWS Mac runner docs
- [aws-samples/amazon-ec2-mac-getting-started](https://github.com/aws-samples/amazon-ec2-mac-getting-started) — AWS Mac SLA & licensing
- [postgis/postgis](https://github.com/postgis/postgis) — macOS coverage options (pricing comparison)
- [vercel-labs/native](https://github.com/vercel-labs/native) — Enforces 2-VM limit
- [joshavant/clawbox](https://github.com/joshavant/clawbox) — Documents 2-VM constraint
- [utmapp/UTM](https://github.com/utmapp/UTM) — UTM VM tool
