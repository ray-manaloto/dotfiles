"""repotools te-review: strict reads of TokenEconomizer state and receipt files, and the refusal they raise."""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .models import CodedFailure, ErrorCode

ADAPTER = "tokeneconomizer-0.1.0"


class TeReviewError(Exception):
    """A refusal; collect leaves nothing behind when it raises one, and report in public mode prints only its code.

    The generated CodedFailure is a pydantic model, not an exception, so it can't be raised: this
    carries it to cli.main, which prints it.
    """

    def __init__(self, code: ErrorCode, error: str) -> None:
        super().__init__(error)
        self.failure = CodedFailure(code=code, error=error)
        self.public = False  # report sets it: then only the code is printed


def absolute(flag: str, given: str | Path, whose: str = "its") -> Path:
    """given as a path, refused unless absolute: a relative one would resolve wherever the caller runs from,
    a checkout under a mise task."""
    path = Path(given)
    if not path.is_absolute():
        msg = f"--{flag} is relative; give {whose} absolute path"
        raise TeReviewError(ErrorCode.RELATIVE_PATH, msg)
    return path


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise TeReviewError(ErrorCode.UNREADABLE, f"{path}: {error.strerror}") from None


def present(path: Path) -> bool:
    """Whether path exists; a path that can't be checked fails the collection instead of reading as absent."""
    try:
        path.stat()
    except FileNotFoundError, NotADirectoryError:
        return False
    except OSError as error:
        raise TeReviewError(ErrorCode.UNREADABLE, f"{path}: {error.strerror}") from None
    return True


def listing(folder: Path) -> list[Path]:
    """folder's entries by name; Path.glob would skip a folder it can't read, and here that fails."""
    try:
        return sorted(folder.iterdir())
    except FileNotFoundError, NotADirectoryError:
        return []
    except OSError as error:
        raise TeReviewError(ErrorCode.UNREADABLE, f"{folder}: {error.strerror}") from None


def json_lines(source: str, data: bytes) -> list[tuple[int, object]]:
    """Every line of a JSONL file with its number, or a refusal: no line is skipped."""
    lines = data.split(b"\n")
    if lines[-1]:
        raise TeReviewError(ErrorCode.TRUNCATED_LINE, f"{source}:{len(lines)} has no line end")
    found = []
    for number, line in enumerate(lines[:-1], 1):
        try:
            found.append((number, json.loads(line)))
        # json's errors and a line that is not UTF-8 (UnicodeDecodeError) are both ValueErrors.
        except ValueError:
            raise TeReviewError(ErrorCode.MALFORMED_LINE, f"{source}:{number} is not JSON") from None
    return found


def json_file(source: str, data: bytes) -> object:
    try:
        return json.loads(data)
    # As in json_lines: bad JSON and bytes that are not UTF-8 are both ValueErrors.
    except ValueError:
        raise TeReviewError(ErrorCode.MALFORMED_FILE, f"{source} is not JSON") from None


def conform[M: BaseModel](model: type[M], where: str, raw: object) -> M:
    """raw as model, or UNKNOWN_SCHEMA naming the shape of what was found instead."""
    try:
        return model.model_validate(raw)
    except ValidationError:
        keys = sorted(raw) if isinstance(raw, dict) else [type(raw).__name__]
        fingerprint = hashlib.sha256(json.dumps(keys).encode()).hexdigest()[:12]
        msg = f"{where} has unknown schema fingerprint {fingerprint} for {ADAPTER}"
        raise TeReviewError(ErrorCode.UNKNOWN_SCHEMA, msg) from None
