# Copyright (c) 2026 Raymond Manaloto
"""Auto-repair `GCC_LATEST_DEB_SHA256` to match the pinned gcc-latest .deb.

kayari.org (jwakely's gcc-latest server) publishes **no checksum or
signature**, so the sha256 in `.devcontainer/Dockerfile` is a
LOCALLY-computed integrity pin. Renovate bumps the dated `GCC_LATEST_DEB`
filename via the `custom.gcc-latest` datasource but cannot compute the sha
of the new .deb, so a bump leaves `GCC_LATEST_DEB_SHA256` stale ->
`sha256sum -c` fails at build time (the "red by design" friction, issue
#249). This module recomputes the sha from the pinned filename and
rewrites the ARG **only when it drifted**, so the `gcc-sha-repair`
workflow can green a Renovate gcc bump automatically.

The sha stays **pinned** in the Dockerfile (reproducible, hermetic): this
recomputes it from the same immutable dated URL the build fetches, giving
byte-level drift detection between repair-time and build-time. It is NOT a
trust anchor (kayari serves no signature) — the dated filename is the
reproducibility handle, the sha the tamper/corruption check.

Mirrors `p2996_refresh.py`: read the pin, resolve upstream via an
injectable seam, rewrite only on change with a strict `subn` count so a
renamed/removed ARG fails loud instead of silently no-op'ing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = logging.getLogger(__name__)

# Must match the download URL in `.devcontainer/Dockerfile` (the RUN that
# fetches "${KAYARI_BASE_URL}${GCC_LATEST_DEB}").
KAYARI_BASE_URL = "https://kayari.org/gcc-latest/"
SHA256_HEX_LEN = 64
_DOWNLOAD_CHUNK = 1 << 20  # 1 MiB — stream a ~480 MB .deb without buffering it.
# No hard total timeout: the .deb is ~480 MB, so a slow-but-progressing link
# must be allowed to finish. Fail fast on a dead connection, and abort only a
# genuinely STALLED transfer (below _MIN_BYTES_PER_SEC for _STALL_SECONDS).
_CONNECT_TIMEOUT_SECONDS = 30
_STALL_SECONDS = 120
_MIN_BYTES_PER_SEC = 1024

# `ARG GCC_LATEST_DEB=gcc-latest_17.0.0-20260705git88752b86ff1a.deb`
_DEB_PATTERN = re.compile(
    r"^ARG GCC_LATEST_DEB=(?P<deb>gcc-latest_[0-9A-Za-z._-]+\.deb)\s*$",
    re.MULTILINE,
)
# `ARG GCC_LATEST_DEB_SHA256=<64 lowercase-hex>` — split so `subn` rewrites
# only the digest, preserving the ARG prefix.
_SHA_PATTERN = re.compile(
    r"(ARG GCC_LATEST_DEB_SHA256=)(?P<sha>[0-9a-f]{" + str(SHA256_HEX_LEN) + r"})",
)


@dataclass(frozen=True)
class RepairResult:
    """Outcome of a gcc-sha repair attempt."""

    changed: bool
    deb: str
    old_sha: str
    new_sha: str

    def as_json(self) -> str:
        """Render the result as a one-line JSON object."""
        return json.dumps(asdict(self))


def _validate_sha(value: str, source: str) -> str:
    """Return `value` if it is a 64-char lowercase-hex sha256.

    Raises:
        ValueError: when `value` is not a well-formed sha256 digest.
    """
    if len(value) != SHA256_HEX_LEN or not all(c in "0123456789abcdef" for c in value):
        msg = (
            f"{source} must be a {SHA256_HEX_LEN}-char lowercase-hex sha256; "
            f"got {value!r}"
        )
        raise ValueError(msg)
    return value


def parse_pins(dockerfile_text: str) -> tuple[str, str]:
    """Return `(deb_filename, pinned_sha)` from the Dockerfile text.

    Raises:
        ValueError: when either ARG is missing (so a repair can never run
            against a renamed/removed pin).
    """
    deb_match = _DEB_PATTERN.search(dockerfile_text)
    if deb_match is None:
        msg = "no `ARG GCC_LATEST_DEB=gcc-latest_*.deb` found in Dockerfile"
        raise ValueError(msg)
    sha_match = _SHA_PATTERN.search(dockerfile_text)
    if sha_match is None:
        msg = "no `ARG GCC_LATEST_DEB_SHA256=<64-hex>` found in Dockerfile"
        raise ValueError(msg)
    return deb_match.group("deb"), sha_match.group("sha")


def _default_fetcher(url: str) -> str:
    """Stream `url` via curl and return its sha256 hexdigest.

    Downloads with `curl -fsSL` (the same fetcher the Dockerfile uses; `-f`
    makes an HTTP 404 a non-zero exit) and hashes the byte stream in Python
    without buffering the ~480 MB body. Subprocess is this repo's blessed
    fetch mechanism (see `p2996_refresh`'s git ls-remote); no HTTP client
    dependency is introduced.

    Raises:
        RuntimeError: when curl exits non-zero — a 404 means the pinned
            dated .deb has aged out of kayari's rolling window, a real,
            loud failure the caller must surface, not paper over.
    """
    digest = hashlib.sha256()
    curl_cmd = [
        "curl",
        "-fsSL",
        "--connect-timeout",
        str(_CONNECT_TIMEOUT_SECONDS),
        "--speed-limit",
        str(_MIN_BYTES_PER_SEC),
        "--speed-time",
        str(_STALL_SECONDS),
        url,
    ]
    with subprocess.Popen(
        curl_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        # Bind to a local so the type checker narrows away the `| None`
        # (stdout=PIPE guarantees a pipe; this branch is unreachable).
        stdout = proc.stdout
        if stdout is None:
            msg = "curl subprocess produced no stdout pipe"
            raise RuntimeError(msg)
        for chunk in iter(lambda: stdout.read(_DOWNLOAD_CHUNK), b""):
            digest.update(chunk)
        _, stderr = proc.communicate()
    if proc.returncode != 0:
        msg = (
            f"curl failed (rc={proc.returncode}) fetching {url}: "
            f"{stderr.decode(errors='replace').strip()}"
        )
        raise RuntimeError(msg)
    return digest.hexdigest()


def compute_sha(
    deb: str,
    fetcher: Callable[[str], str] | None = None,
    *,
    base_url: str = KAYARI_BASE_URL,
) -> str:
    """Download `deb` from `base_url` and return its validated sha256.

    `fetcher` is a test seam: a callable `(url) -> sha256_hexdigest`.
    """
    fetch = fetcher or _default_fetcher
    url = f"{base_url}{deb}"
    logger.info("Fetching gcc-latest .deb to compute sha256: %s", url)
    return _validate_sha(fetch(url), f"computed sha256 of {deb}")


def replace_sha(dockerfile_text: str, new_sha: str) -> str:
    """Return `dockerfile_text` with `GCC_LATEST_DEB_SHA256` set to `new_sha`.

    Raises:
        ValueError: when the ARG is missing (so a silent no-op rewrite can
            never mask a renamed/removed pin).
    """
    new_text, count = _SHA_PATTERN.subn(rf"\g<1>{new_sha}", dockerfile_text)
    if count != 1:
        msg = (
            "expected exactly one GCC_LATEST_DEB_SHA256 ARG in Dockerfile, "
            f"found {count}"
        )
        raise ValueError(msg)
    return new_text


def repair(
    repo_root: Path,
    *,
    fetcher: Callable[[str], str] | None = None,
    write: bool = True,
) -> RepairResult:
    """Recompute the gcc-latest sha and rewrite the ARG if it drifted.

    Writes `.devcontainer/Dockerfile` only when the sha changed (so an
    already-correct pin leaves the file byte-identical — no spurious
    commit). With `write=False` this is a pure check: it still downloads
    and compares, but never mutates the file.
    """
    dockerfile_path = repo_root / ".devcontainer" / "Dockerfile"
    dockerfile_text = dockerfile_path.read_text()
    deb, old_sha = parse_pins(dockerfile_text)
    new_sha = compute_sha(deb, fetcher)
    if new_sha == old_sha:
        logger.info("GCC_LATEST_DEB_SHA256 already matches %s (%s)", deb, new_sha)
        return RepairResult(changed=False, deb=deb, old_sha=old_sha, new_sha=new_sha)
    if write:
        dockerfile_path.write_text(replace_sha(dockerfile_text, new_sha))
        logger.info("Repaired GCC_LATEST_DEB_SHA256: %s -> %s", old_sha, new_sha)
    else:
        logger.warning(
            "GCC_LATEST_DEB_SHA256 drift for %s: pinned %s, actual %s",
            deb,
            old_sha,
            new_sha,
        )
    return RepairResult(changed=True, deb=deb, old_sha=old_sha, new_sha=new_sha)


def gcc_sha_main(repo_root: Path, *, check: bool = False) -> int:
    """CLI entry: `repair` writes on drift; `--check` reports without writing.

    Returns 0 when the pin already matches (or was repaired). In `--check`
    mode returns 1 on drift so a caller can gate on it; the emitted JSON
    line carries `changed`/`old_sha`/`new_sha` for the workflow to consume.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = repair(repo_root, write=not check)
    sys.stdout.write(result.as_json() + "\n")
    if check and result.changed:
        return 1
    return 0
