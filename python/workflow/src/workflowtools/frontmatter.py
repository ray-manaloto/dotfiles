"""SKILL.md and okf concept frontmatter, and YAML that parses, read from the index."""

from pathlib import PurePosixPath

import yaml
from pydantic import ValidationError

from .git import staged, tracked
from .models import Check, Finding, OkfFrontmatter, SkillFrontmatter

# The okf bundles: every Markdown file in them but the map and the log is a concept with a type.
OKF = ("unix/home/.config/agents/workflow/", "docs/research/")
MAPS = {"index.md", "log.md"}


def header(text: str) -> object:
    """The YAML between a leading --- line and the next one, or None when the file has no block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        msg = "unterminated frontmatter block"
        raise ValueError(msg)
    return yaml.safe_load("\n".join(lines[1:end]))


def problem(path: str, text: str) -> str | None:
    name = PurePosixPath(path).name
    try:
        if name == "SKILL.md":
            data = header(text)
            if data is None:
                return "SKILL.md has no frontmatter block"
            SkillFrontmatter.model_validate(data)
        elif path.startswith(OKF) and name.endswith(".md") and name not in MAPS:
            data = header(text)
            if data is None:
                return "okf concept file has no frontmatter block"
            OkfFrontmatter.model_validate(data)
        elif name.endswith((".yml", ".yaml")):
            # A file may hold several --- separated documents (a Kubernetes manifest); parse them all.
            list(yaml.safe_load_all(text))
    except ValidationError as error:
        return "; ".join(f"frontmatter {'.'.join(map(str, e['loc'])) or 'block'}: {e['msg']}" for e in error.errors())
    # YAMLError is not a ValueError; ValueError here is the unterminated block.
    except (yaml.YAMLError, ValueError) as error:
        return f"invalid YAML: {error}" if isinstance(error, yaml.YAMLError) else str(error)
    return None


def findings() -> list[Finding]:
    return [
        Finding(path=path, check=Check.frontmatter, detail=detail)
        for path in tracked("*.md", "*.yml", "*.yaml")
        if (detail := problem(path, staged(path))) is not None
    ]
