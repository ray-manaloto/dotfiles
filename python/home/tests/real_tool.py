"""Find a tool's real binary on PATH, never mise's command-wrapper link to `mise` that can stand in for it."""

import os
from pathlib import Path


def real_which(name: str, path: str | None = None) -> str | None:
    """The first `name` on PATH that is not a link to mise (a command wrapper), or None when only wrappers exist."""
    # A wrapper in mise's command-wrappers directory is a link to `mise`; run under a thin environment (the
    # nightly's launchd, then `mise run`) it reads the real global config and exits before the tool runs.
    # `mise` itself is the one name that resolves to mise.
    for folder in (os.environ["PATH"] if path is None else path).split(os.pathsep):
        candidate = Path(folder) / name
        if (
            candidate.is_file()
            and os.access(candidate, os.X_OK)
            and (name == "mise" or candidate.resolve().name != "mise")
        ):
            return str(candidate)
    return None
