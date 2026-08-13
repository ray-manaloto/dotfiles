# Real Integration Evidence

Do not use mocks, synthetic subprocesses, or self-authored receipts as the sole
evidence that an integration works.

Mocks are acceptable only as supplemental unit controls. A completion claim for
an external CLI, hook, credential path, Graphify release, devcontainer, or
cross-repository dependency requires at least one real invocation through the
public project entrypoint plus its real failure/control arm. If that invocation
cannot run, preserve the reason and mark the capability unverified; do not
replace it with a mock and call the work complete.
