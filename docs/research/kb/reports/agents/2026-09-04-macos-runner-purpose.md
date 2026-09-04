---
name: macos-runner-purpose-2026-09-04
description: Facts on GitHub-hosted macOS runner usage; what workloads actually run there and why
metadata:
  type: reference
  date: 2026-09-04
---

# What GitHub-Hosted macOS Runners Are Actually Used For

GitHub-hosted macOS runners (macos-latest / macos-26 / macos-15 / macos-14) **cannot run nested VMs or Linux containers** (GitHub staff, actions/runner-images#13505, 2026-01-08). This report characterizes the real workloads they serve with citations.

## Control arms — methodology validated

| Arm | Query | Expected | Observed | Result |
|---|---|---|---|---|
| **Positive** | `"runs-on: macos-latest"` | 1000+ hits | 20 results (limit applied) | ✓ PASS |
| **Negative** | `"runs-on: macos-xyzqq9999999"` | 0 hits | Empty array `[]` | ✓ PASS |

Search shape confirmed working. No inline `path:` qualifiers (returns empty). Queries paced at ~10/min.

---

## Dominant job categories (verified with real workflows)

### 1. Python Wheel Building (cibuildwheel) — **HIGH VOLUME**

**Real projects:**
- `pypa/cibuildwheel` — the wheel builder itself (test matrix includes macos-15, macos-15-intel)
- `aio-libs/aiohttp` — uses cibuildwheel for CPython .whl distributions
- `facebookresearch/faiss` — C++ bindings, wheel builds on arm64/intel
- `apache/beam` — multi-arch wheel building

**What actually runs:**
```yaml
# From cibuildwheel's test.yml
- os: macos-15-intel
  python_version: '3.13'
- os: macos-15  
  python_version: '3.13'
  test_select: ios  # <-- iOS wheel testing via simulator
  test_runtime: 'args: --simulator "iPhone 16e,OS=18.5"'
```

**Why macOS-only:** Building native CPython wheels for macOS requires the macOS SDK, Clang, and system frameworks. Wheels targeting `macosx_*` platform tags can only be built on macOS.

**macOS-specific components:** cibuildwheel, native C/C++ compilation, Apple SDKs, `xcrun` (for iOS simulator wheels)

### 2. Homebrew Formula Testing — **REQUIRED NATIVE**

**Real project:**
- `Homebrew/brew` — runs `macos-26` (latest ARM)

**What actually runs:**
```yaml
# From Homebrew/brew tests.yml
jobs:
  test:
    runs-on: macos-26
    steps:
      - name: Set up Homebrew
        uses: Homebrew/actions/setup-homebrew@...
      - name: Run brew readall on all casks
        run: brew readall --os=all --arch=all homebrew/cask
```

**Why macOS-only:** Homebrew is a **macOS-only package manager**. Formula validation must run on macOS. Cannot mock or containerize this.

**macOS-specific components:** `brew` CLI, Homebrew-specific validation commands

### 3. Xcode/iOS/tvOS/watchOS Development

**Real evidence:**
- cibuildwheel's iOS wheel tests: `test_select: ios` with `xcrun simctl` simulator args
- Search: `xcodebuild` returned 10+ repos (openMVG, Descent3, processing4, etc.)
- Search: `xcrun simctl` returned repos (microsoft/vscode-react-native, wix/AppleSimulatorUtils, react-native-device-info, etc.)

**Critical fact about simulators:**
- iOS/tvOS/watchOS **simulators are NOT virtual machines**
- They are **userland processes** on the host macOS kernel
- **Do NOT require nested virtualization** — work fine on GitHub runners despite Hypervisor.framework absence
- Example: cibuildwheel tests iOS builds on macos runners with `iPhone 16e,OS=18.5` simulator, proving they work

**Why macOS-only:** Xcode toolchain, Apple SDKs, simulator infrastructure — all macOS-only.

**macOS-specific components:** Xcode, `xcodebuild`, `xcrun`, Apple SDKs, Clang/LLVM Apple variant

### 4. Code Signing and Notarization (Electron, Tauri, macOS apps)

**Search results:** codesign query returned 5 repos:
- `anchore/quill` — binary signing utility
- `DescentDevelopers/Descent3` — game with macOS builds
- `johnno1962/InjectionIII` — macOS app requiring signing
- Additional: Tauri/Electron apps that package for macOS

**Why macOS-only:** `codesign` and `notarytool` are **Apple-only tools**, unavailable on Linux/Windows. Required for shipping macOS apps to end users.

**macOS-specific components:** `codesign`, `notarytool`, Apple Developer certificates/keys, Gatekeeper ecosystem

### 5. Cross-Platform CI (macOS as one leg of a matrix)

**Real projects:**
- `synnaxlabs/synnax` — matrix with ubuntu-latest + ${{ matrix.os }} including macos-latest
- Discord bots (aiko-chan-ai/DiscordBotClient, wecode-ai/WeCut, yixing233/PasteX)
- Numerous Electron/Tauri desktop apps

**Pattern:** 
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
```

**Why:** Test cross-platform Rust/Go/C++ compilation on native macOS to catch:
- macOS-specific linker flags
- System framework availability
- Clang version differences vs Linux GCC
- Architecture-specific code paths (arm64 vs x86_64)

**macOS-specific components:** Native compilation chain, Clang, Apple system frameworks

---

## What can ONLY be done on macOS (vs. what merely runs there)

| Component | Linux container? | macOS runner? | Category |
|---|---|---|---|
| **xcodebuild / Xcode** | ✗ (unavailable) | ✓ | iOS/macOS native |
| **iOS/tvOS/watchOS simulators** | ✗ (need macOS kernel) | ✓ (userland processes) | iOS development |
| **codesign / notarytool** | ✗ (Apple-only) | ✓ | Code signing |
| **Homebrew (brew CLI)** | ✗ (macOS-only) | ✓ | Package management |
| **Apple SDKs (CoreFoundation, etc.)** | ✗ (unavailable) | ✓ | Native development |
| **Clang with Apple patches** | ~ (available but different) | ✓ | Compilation |
| **CPython wheels for macOS** | ✗ (needs macOS SDK) | ✓ | Python distribution |
| **Rust/Go native binaries for macOS** | ~ (possible with cross-compilation, but macOS runners compile natively) | ✓ (native) | Native compilation |

---

## Constraints observed

**Hardware (ARM runners):**
- 3 CPU cores
- 7 GB RAM
- 14 GB disk (noted in runner-images docs)

**Performance:**
- Queue times can be significant (private repos pay premium)
- Slower than Linux runners (generally)
- But necessary for above categories — no alternative exists

**Workflow patterns found:**
- Conditional steps: `if: runner.os == 'macOS'`
- Matrix strategies with OS as variable
- Caching of build artifacts between runs
- Tool setup via GitHub Actions (setup-python, setup-node, etc.)

---

## Why GitHub-hosted macOS runners exist (synthesis)

**Three categories of essential work:**

1. **Apple platform-specific:** Anything using Xcode, codesign, notarytool, Homebrew, or Apple SDKs requires native macOS. No Linux container can substitute.

2. **Native code testing on macOS:** Cross-platform projects (Rust, Go, C++) need to compile and test on actual macOS hardware to catch platform-specific bugs. Virtual macOS (Anka, Colima) exists for CI but GitHub-hosted is simpler and managed.

3. **Python/library distributions:** CPython wheels and compiled libraries targeting macOS must be built on macOS to include the correct system frameworks and architecture tags.

**iOS/tvOS/watchOS simulators are the surprise:** Despite no Hypervisor support, simulators work perfectly fine because they don't need virtualization — they run as regular processes on the host macOS kernel.

---

## GitHub repos touched

- [pypa/cibuildwheel](https://github.com/pypa/cibuildwheel) — Python wheel builder, uses macos runners for testing
- [aio-libs/aiohttp](https://github.com/aio-libs/aiohttp) — CPython wheel building with cibuildwheel
- [facebookresearch/faiss](https://github.com/facebookresearch/faiss) — C++ library with Python wheels
- [apache/beam](https://github.com/apache/beam) — multi-arch Python wheel distribution
- [Homebrew/brew](https://github.com/Homebrew/brew) — Homebrew package manager validation (runs macos-26)
- [pypa/setuptools](https://github.com/pypa/setuptools) — Python packaging (implies wheel testing on macOS)
- [microsoft/vscode-react-native](https://github.com/microsoft/vscode-react-native) — iOS simulator workflows
- [wix/AppleSimulatorUtils](https://github.com/wix/AppleSimulatorUtils) — iOS simulator utilities
- [react-native-device-info/react-native-device-info](https://github.com/react-native-device-info/react-native-device-info) — xcrun/simulator testing
- [synnaxlabs/synnax](https://github.com/synnaxlabs/synnax) — cross-platform CI matrix
- [aiko-chan-ai/DiscordBotClient](https://github.com/aiko-chan-ai/DiscordBotClient) — Electron app on macos-latest
- [anchore/quill](https://github.com/anchore/quill) — code signing utility
- [DescentDevelopers/Descent3](https://github.com/DescentDevelopers/Descent3) — game build with codesign
