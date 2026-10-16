# Copyright (c) 2026 Raymond Manaloto
"""Generated research failure-code enum; edit the schema and rerun codegen."""

from enum import StrEnum


class FailureCode(StrEnum):
    """Closed set of model-visible codes, independent of provider text."""

    CREDITS_EXHAUSTED = "credits-exhausted"
    PREREQUISITE = "prerequisite"
    QUOTA = "quota"
    CREDENTIAL_MISSING = "credential-missing"
    AUTH_FAILED = "auth-failed"
    UNAVAILABLE = "unavailable"
    SANDBOX_DENIED = "sandbox-denied"
    HTTP_ERROR = "http-error"
    INVALID_JSON = "invalid-json"
    SHAPE_ERROR = "shape-error"
    PROVIDER_FAILURE = "provider-failure"
    PROCESS_FAILED = "process-failed"
    TIMEOUT = "timeout"
    REQUEST_FAILED = "request-failed"
    CREDENTIAL_INVALID = "credential-invalid"
    CANARY_FAILED = "canary-failed"
    CANARY_EMPTY = "canary-empty"
    NO_CANARY = "no-canary"
    NOT_FOUND = "not-found"
    REDIRECTED = "redirected"
    EMPTY_OUTPUT = "empty-output"
    IO_ERROR = "io-error"
    OTHER = "other"
