# Live probes — mise 2026.10.1 macos-arm64, scratch fixture (mktemp -d), 2026-10-03

Fixture: `main/{mise.toml,mise.local.toml,.config/mise/conf.d/shared.toml}` each set `[env] FROM_MAIN*`;
`main/.claude/worktrees/wt/{mise.toml,.config/mise/conf.d/shared.toml}` set `FROM_WT*`. Run with
`MISE_TRUSTED_CONFIG_PATHS=<fixture>` (fixture-only trust; nothing global changed).

| Arm | Setup | cwd | Probe | Result |
|---|---|---|---|---|
| A (control, leak expected) | no .miserc, no env | wt | `mise config ls` | main mise.toml, mise.local.toml, conf.d/shared.toml listed + wt files — LEAK reproduced |
| B (fix) | config_root template in BOTH main & wt `.miserc.toml` | wt | `mise config ls` | only wt files |
| B2 (cross-check route) | tightened template (also checks `.claude`) | wt | `mise env` | only FROM_WT, FROM_WT_CONFD |
| C / C2 (no regression) | same | main | `config ls` / `env` | all three FROM_MAIN* present |
| D (hazard) | template only in MAIN; wt copy = `auto_env=false` only (old base) | wt | `mise env` | LEAK (main's config_root resolves to main → no ceiling) |
| E (measured env fix) | no miserc template; `MISE_CEILING_PATHS=<main>/.claude/worktrees` | wt | `mise env` | only FROM_WT* |
| F | template in both | wt/sub/deep | `mise env` | only FROM_WT* (works from subdirs) |
| G | template in both, no MISE_TRUSTED_CONFIG_PATHS | wt | `mise env` | only FROM_WT* — .miserc needs no trust |

Template that WORKS (Tera 2, miserc engine):
```toml
auto_env = false
{% if config_root | dirname | basename == "worktrees" and config_root | dirname | dirname | basename == ".claude" %}
ceiling_paths = ["{{ config_root | dirname }}"]
{% endif %}
```

`cwd`-based variants FAILED: `cwd is containing(..)`, `cwd is starting_with("/")`, `cwd | as_str` + `is containing`
-> template render fails -> mise falls back to RAW content -> HARD `mise::config::parse_error` (every mise command
in that tree fails). `"/.claude/worktrees/" in cwd` and `cwd | split(...)` rendered but did NOT match (leak). So the
template must be armed; a render failure is fatal, not a warning, in practice. (src/config/miserc.rs:146-151 warns and
returns raw content; the raw `{% %}` line is invalid TOML.)

`mise settings get ceiling_paths` returned `[]` even with the working template -> NOT a valid probe for miserc
values (control arm failed); use `mise config ls` / `mise env`.
