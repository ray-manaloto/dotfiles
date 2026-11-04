"""Field checks the generated models call (datamodel-codegen --validators); nothing here imports the models."""

from pydantic import ValidationInfo


def unique_clients[T](clients: list[T], _info: ValidationInfo) -> list[T]:
    """Config.clients is uniqueItems in the schema; the generated model checks it through this function."""
    if len(set(clients)) != len(clients):
        msg = "names a client twice"
        raise ValueError(msg)
    return clients
