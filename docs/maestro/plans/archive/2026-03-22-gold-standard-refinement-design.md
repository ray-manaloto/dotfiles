# Design Document: Gold Standard Refinement

**Date**: 2026-03-22
**Status**: Approved
**Complexity**: Complex
**Design Depth**: Deep

## 1. Objective
Establish a high-rigor "Gold Standard" for the dotfiles repository, integrating TDD for infrastructure, automated dependency updates via Renovate, and a formalized "Definition of Done" (DoD) protocol for all tool management.

## 2. Architectural Approach: "The Infrastructure Guardian"
This approach centers on polyglot testing and automated governance to ensure environmental integrity.

### 2.1 Automated Updates (Renovate)
- **Mechanism**: Use Renovate's native `mise` manager to track and update versions in `home/dot_config/mise/config.toml.tmpl`.
- **Integration**: Renovate will also manage standard backends (`cargo:`, `npm:`, `go:`) and the custom `aqua:` registry if used.

### 2.2 Polyglot TDD Framework
- **Shell Layer (bats-core)**: Handles fast, low-level binary reachability and path checks.
- **Logic Layer (Python/pytest)**: Handles complex functional validations, version string parsing, and agentic state audits.
- **TDD Workflow**: Every new tool must have a failing `bats` or `pytest` check *before* it is added to the declarative configuration.

### 2.3 Formalized DoD Protocol (The "Acceptance Interview")
Every tool installation or modification must satisfy three quantifiable metrics:
1. **Capability**: A specific "Smoke Test" command that proves functionality.
2. **Environment**: Verification of required aliases, shims, and environment variables.
3. **Path**: Confirmation of the exact installation location to prevent system pollution.

## 3. Core Stack
- **Managers**: Mise, Renovate.
- **Testing**: bats-core, pytest.
- **Standards**: Zero-Bash (Logic), Zero-Skips (Linting).

## 4. Repository Structure (Updates)
- `tests/infra/`: New directory for `bats` infrastructure tests.
- `python/src/dotfiles_setup/audit.py`: Updated to act as the logic-heavy test runner.
- `renovate.json`: Project-wide update policy.

## 5. Decision Matrix
| Feature | Choice | Rationale |
|---------|--------|-----------|
| Update Engine | Renovate | Native Mise support and broad ecosystem coverage. |
| Test Runner | Polyglot (bats + pytest) | Combines shell-native speed with Python's rich logic capabilities. |
| Transition | Audit-First Migration | Ensures existing foundational tools are verified before new features are added. |

## 6. Constraints & Success Criteria
- **Zero Logic duplication**: Shell tests check "existence"; Python tests check "correctness."
- **100% CI Coverage**: Every commit must trigger the full polyglot test suite.
- **Verifiable Results**: Audit output must include numerical/string results for all checks.
