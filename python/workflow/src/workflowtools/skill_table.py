"""The workflow docs' skills.md against the user-scope mattpocock-skills plugin install."""

import re
from pathlib import Path

from .frontmatter import header
from .git import top
from .models import Check, Finding, InstalledPlugins, PluginManifest, PluginRecord, Skipped

TABLE = "unix/home/.config/agents/workflow/skills.md"
PLUGIN = "mattpocock-skills@mattpocock"
ROW = re.compile(r"^\|\s*`([a-z-]+)`\s*\|\s*(user-only|model)\s*\|", re.MULTILINE)
PIN = re.compile(r'^upstream_commit:\s*"?([0-9a-f]{40})"?\s*$', re.MULTILINE)


def installed() -> PluginRecord | None:
    """The plugin's user-scope install, the one every repository's sessions load, or None."""
    records = Path.home() / ".claude/plugins/installed_plugins.json"
    if not records.is_file():
        return None
    plugins = InstalledPlugins.model_validate_json(records.read_text()).plugins
    return next((r for r in plugins.get(PLUGIN, []) if r.scope == "user"), None)


def flags(root: Path) -> dict[str, str]:
    """Each skill's name and whether only the user can start it, as its SKILL.md says."""
    manifest = PluginManifest.model_validate_json((root / ".claude-plugin/plugin.json").read_text())
    result = {}
    for skill in manifest.skills:
        data = header((root / skill / "SKILL.md").read_text())
        user_only = isinstance(data, dict) and data.get("disable-model-invocation") is True
        result[Path(skill).name] = "user-only" if user_only else "model"
    return result


def findings() -> list[Finding] | Skipped:
    record = installed()
    if record is None or not Path(record.install_path).is_dir():
        # CI and other machines have no install: say so rather than fail.
        return Skipped(check=Check.skill_table, reason=f"{PLUGIN} has no user-scope install")
    text = (top() / TABLE).read_text()
    pin = PIN.search(text)
    if pin is None:
        return [Finding(path=TABLE, check=Check.skill_table, detail="no full upstream_commit in its frontmatter")]
    if record.git_commit_sha != pin.group(1):
        detail = (
            f"installed plugin is {record.git_commit_sha}, the table pins {pin.group(1)}; re-verify the workflow docs "
            "against the new SKILL.md files, then move the pin"
        )
        return [Finding(path=TABLE, check=Check.skill_table, detail=detail)]
    table = dict(ROW.findall(text))
    have = flags(Path(record.install_path))
    details = [
        f"{name}: the table says {table.get(name, 'nothing')}, SKILL.md says {flag}"
        for name, flag in sorted(have.items())
        if table.get(name) != flag
    ]
    details += [f"{name}: in the table, not in the plugin" for name in sorted(set(table) - set(have))]
    return [Finding(path=TABLE, check=Check.skill_table, detail=detail) for detail in details]
