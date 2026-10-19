# Copyright (c) 2026 Raymond Manaloto
"""Generated research skip-reason enum; edit the schema and rerun codegen."""

from enum import StrEnum


class SkipReason(StrEnum):
    """Why research-fanout skipped a source instead of reporting an error."""

    PREREQUISITE = "prerequisite"
    CREDITS_EXHAUSTED = "credits-exhausted"
    QUOTA = "quota"
    CREDENTIAL_MISSING = "credential-missing"
    AUTH_FAILED = "auth-failed"
    UNAVAILABLE = "unavailable"
    SANDBOX_DENIED = "sandbox-denied"
