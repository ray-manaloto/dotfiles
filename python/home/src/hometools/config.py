"""A command's settings, from the TOOLCHAIN_<NAME> values its file task's header sets from mise."""

import os
from collections.abc import Mapping

from pydantic import BaseModel, ValidationError


class ToolchainError(Exception):
    """A failed check or a failed program: its message is the one line the task reports."""


def load[Settings: BaseModel](model: type[Settings], environ: Mapping[str, str] = os.environ) -> Settings:
    """Field <name> comes from TOOLCHAIN_<NAME>; there are no defaults, so a missing one refuses."""
    # Not pydantic-settings: it reads only BaseSettings subclasses, and codegen's base class is one flag for
    # every model, the Hometools root and Failure included. This is p2996's loader (p2996/config.py:21).
    names = {field: f"TOOLCHAIN_{field.upper()}" for field in model.model_fields}
    if missing := [name for name in names.values() if name not in environ]:
        msg = f"hometools: {', '.join(missing)} unset; run it through its mise task"
        raise ToolchainError(msg)
    try:
        return model.model_validate({field: environ[name] for field, name in names.items()})
    except ValidationError as invalid:
        empty = [names[str(error["loc"][0])] for error in invalid.errors()]
        msg = f"hometools: {', '.join(empty)} empty"
        raise ToolchainError(msg) from None
