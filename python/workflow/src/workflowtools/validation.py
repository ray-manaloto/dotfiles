"""Field checks the generated models call (datamodel-codegen --validators); nothing here imports the models."""

from pydantic import ValidationInfo

MODES = ("listing", "rebuild", "plan")


def one_mode[T](value: T, info: ValidationInfo) -> T:
    """Tickets takes one of --listing, --rebuild and --plan; the generated model checks each through this function.

    datamodel-codegen generates field validators only, so each mode checks the modes validated before it.
    """
    if value and any(info.data.get(mode) for mode in MODES if mode != info.field_name):
        msg = "workflowtools tickets: use one of --listing, --rebuild, --plan"
        raise ValueError(msg)
    return value
