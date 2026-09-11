# Repowise Is Advisory

Repowise remains enabled as an advisory review signal. It currently fails on
every pull request, but that recurring failure does not make it a required
check and is not a reason to disable it.

`ci-gate` is the repository's only required branch-protection check. A Repowise
failure may still identify a real quality problem and should be read and
dispositioned on its merits; it must not be reported as blocking merge merely
because the check is red.

The `REPOWISE_KNOWLEDGE_BASE_API_KEY` entry in `doctor.toml` keeps the service's
credential visible in the reviewed host baseline. Changing Repowise's advisory
status requires a separate branch-protection decision, not a doctor-config edit.

Decision: 2026-09-10 `/grilling` ruling 9 — keep Repowise and document its
advisory status.
