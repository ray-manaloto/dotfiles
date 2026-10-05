# Copyright (c) 2026 Raymond Manaloto
"""datamodel-codegen post-formatter: generated models import from the codec.

Only `dotfiles_setup.codec` may import msgspec (ruff TID251 plus the tree sweep
`tests/test_codec.py::test_no_module_outside_the_codec_calls_msgspec_directly`).
datamodel-codegen's msgspec output always writes `from msgspec import ...`, and
nothing in its configuration remaps that module, so this formatter does. It is
wired once, in `python/pyproject.toml` `[tool.datamodel-codegen]`
`custom-formatters`, and runs after the ruff formatters
(`datamodel_code_generator.format.CodeFormatter._format_code`, 0.83.0). So it
replaces the module name in place and leaves the import order ruff already
settled. Measured 2026-10-03: the #1502 ship failed in-container on two
generated modules before this existed.
"""

from __future__ import annotations

import re

from datamodel_code_generator.format import CustomCodeFormatter

_FROM_MSGSPEC = re.compile(r"^from msgspec import ", re.MULTILINE)
_ANY_MSGSPEC_IMPORT = re.compile(r"^\s*(?:import msgspec|from msgspec)", re.MULTILINE)
_CODEC_IMPORT = "from dotfiles_setup.codec import "


class CodeFormatter(CustomCodeFormatter):
    """Point generated `from msgspec import` lines at `dotfiles_setup.codec`."""

    def apply(self, code: str) -> str:
        """Rewrite the import module, refusing any msgspec import it cannot map.

        Raises:
            ValueError: A msgspec import of another shape (`import msgspec`,
                `from msgspec.x import`) survived the rewrite, so the generated
                module would still cross the codec boundary.
        """
        rewritten = _FROM_MSGSPEC.sub(_CODEC_IMPORT, code)
        if _ANY_MSGSPEC_IMPORT.search(rewritten):
            message = (
                "generated code imports msgspec in a shape codegen_imports cannot "
                "rewrite; export the name from dotfiles_setup.codec and map it here"
            )
            raise ValueError(message)
        return rewritten
