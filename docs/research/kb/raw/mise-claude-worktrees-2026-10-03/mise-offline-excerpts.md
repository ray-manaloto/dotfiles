# mise source excerpts (KB mirror commit 794948606e02, 2026-09-09)

## src/config/miserc.rs:155-286
```rust
/// Load and merge all miserc settings files.
/// Precedence (highest to lowest):
/// 1. Local .miserc.toml and .config/miserc.toml (closest to cwd wins)
/// 2. Global ~/.config/mise/miserc.toml
/// 3. System /etc/mise/miserc.toml
fn load_miserc_settings() -> Result<MisercSettings> {
    load_miserc_files(find_miserc_files())
}

fn load_miserc_files(files: Vec<PathBuf>) -> Result<MisercSettings> {
    let mut merged = MisercSettings::default();
    // Load in reverse precedence order so later loads override earlier ones
    // Tera is initialized lazily inside render_miserc_template — only paid if a file
    // actually contains template syntax. Shared across all files to avoid redundant clones.
    let mut tera: Option<TeraEngine> = None;

    for path in files.into_iter().rev() {
        if let Ok(content) = file::read_to_string(&path) {
            let config_root = path.parent().unwrap_or(Path::new("."));
            let content = render_miserc_template(&mut tera, &content, config_root);
            let mut settings = toml::from_str::<MisercSettings>(&content)
                .map_err(|e| toml_parse_error(&e, &content, &path))?;
            resolve_ignored_config_paths(&mut settings, config_root);
            merge_settings(&mut merged, settings);
        }
    }

    Ok(merged)
}

fn resolve_ignored_config_paths(settings: &mut MisercSettings, config_root: &Path) {
    let Some(paths) = settings.ignored_config_paths.take() else {
        return;
    };
    settings.ignored_config_paths = Some(
        paths
            .into_iter()
            .map(|path| resolve_ignored_config_path(path, config_root))
            .collect(),
    );
}

pub(crate) fn resolve_ignored_config_path(path: PathBuf, relative_to: &Path) -> PathBuf {
    file::replace_path(path)
        .absolutize_from(relative_to)
        .into_owned()
}

/// Merge source settings into target, where source values override target.
fn merge_settings(target: &mut MisercSettings, source: MisercSettings) {
    if source.env.is_some() {
        target.env = source.env;
    }
    if source.auto_env.is_some() {
        target.auto_env = source.auto_env;
    }
    if source.env_conf_d.is_some() {
        target.env_conf_d = source.env_conf_d;
    }
    if source.ceiling_paths.is_some() {
        target.ceiling_paths = source.ceiling_paths;
    }
    if source.ignored_config_paths.is_some() {
        target.ignored_config_paths = source.ignored_config_paths;
    }
    if source.override_config_filenames.is_some() {
        target.override_config_filenames = source.override_config_filenames;
    }
    if source.override_tool_versions_filenames.is_some() {
        target.override_tool_versions_filenames = source.override_tool_versions_filenames;
    }
}

/// Find all miserc.toml files in order of precedence (highest first).
fn find_miserc_files() -> Vec<PathBuf> {
    let mut files = Vec::new();
    let ceiling_paths = env_ceiling_paths();

    // Local hierarchy: .miserc.toml and .config/miserc.toml in cwd and ancestors
    // Use raw std::env to avoid depending on our lazy statics
    if let Ok(cwd) = std::env::current_dir() {
        // Walk up the directory tree, but stop at home or root
        let home: &Path = &dirs::HOME;
        for dir in cwd.ancestors() {
            if ceiling_paths.contains(dir) {
                break;
            }
            let path = dir.join(".miserc.toml");
            if path.is_file() {
                files.push(path);
            }
            // Stop at home directory to avoid searching too far
            if dir == home || dir.parent().is_none() {
                break;
            }
            let path = dir.join(".config").join("miserc.toml");
            if path.is_file() {
                files.push(path);
            }
        }
    }

    // Global: ~/.config/mise/miserc.toml
    let global_path = dirs::CONFIG.join("miserc.toml");
    if global_path.is_file() {
        files.push(global_path);
    }

    // System: /etc/mise/miserc.toml (or MISE_SYSTEM_CONFIG_DIR)
    let system_dir = env::MISE_SYSTEM_CONFIG_DIR.clone();
    let system_path = system_dir.join("miserc.toml");
    if system_path.is_file() {
        files.push(system_path);
    }

    files
}

fn env_ceiling_paths() -> BTreeSet<PathBuf> {
    // Only the raw env var is available here; env::MISE_CEILING_PATHS also
    // falls back to .miserc, which would recurse during .miserc discovery.
    env::var_os("MISE_CEILING_PATHS")
        .map(|v| {
            std::env::split_paths(&v)
                .filter(|p| !p.as_os_str().is_empty())
                .map(file::replace_path)
                .collect()
        })
        .unwrap_or_default()
}

#[cfg(test)]
```
## settings.toml:430-456
```toml
[ceiling_paths]
default = []
description = "Directories where mise stops searching for config files."
docs = """
Directories where mise stops searching for config files. By default, mise
will search from the current directory up to the root of the filesystem.

Setting this to a list of directories will stop the search when one of
those directories is reached. Config files **in** the ceiling directory
itself are excluded—only directories below it are searched. For example,
if `MISE_CEILING_PATHS="/home/user"`, then `/home/user/mise.toml` is
**not** loaded, but `/home/user/projects/myapp/mise.toml` is.

This follows the same semantics as Git's `GIT_CEILING_DIRECTORIES`.

This is an early-init setting: it must be set in `.miserc.toml`, environment
variables, or CLI flags. Setting it in `mise.toml` will have no effect because
config file discovery has already occurred by the time `mise.toml` is read.

Paths are separated by the OS path separator when using the environment variable,
`mise settings set`, or `mise settings add` (`:` on Unix, `;` on Windows).
"""
env = "MISE_CEILING_PATHS"
parse_env = "list_by_os_path_separator"
rc = true
rust_type = "BTreeSet<PathBuf>"
type = "ListPath"
```
## docs/configuration/environments.md:49-90
## Setting MISE_ENV in .miserc.toml

You can set `MISE_ENV` in a `.miserc.toml` file, which is loaded early, before
other config files are discovered. This lets you commit your environment
configuration to version control:

```toml
# .miserc.toml
env = ["development"]
```

### Templates in .miserc.toml

`.miserc.toml` supports [Tera templates](/templates#miserc-template-support),
which is useful for settings like `ceiling_paths` that reference home or XDG directories:

<div v-pre>

```toml
# .miserc.toml

# Stop config search at $HOME
ceiling_paths = ["{{ env.HOME }}"]

# Or use the XDG config home variable
ignored_config_paths = ["{{ xdg_config_home }}/mise/shared.toml"]
```

</div>

Only OS-level context is available (environment variables, `cwd`, `arch()`, `os()`,
etc.); settings from `mise.toml` are not yet loaded at this stage.

File locations searched (in order of precedence):

1. `.miserc.toml` and `.config/miserc.toml` in the current directory and parent directories
2. `~/.config/mise/miserc.toml` (global)
3. `/etc/mise/miserc.toml` (system)

`MISE_ENV` cannot be set in `mise.toml` because it determines which config
files are loaded in the first place.

## docs/templates.md:532-600
## Template Support in .miserc.toml {#miserc-template-support}

`.miserc.toml` files support Tera templates, but with a **limited context**: `.miserc.toml`
is loaded very early — before `mise.toml`, settings, and the main config are parsed — so
only information available at the OS level can be used.

### Available context

- `env: HashMap<String, String>` – OS environment variables (same as in `mise.toml`)
- `config_root: PathBuf` – Directory containing the `.miserc.toml` file
- `cwd: PathBuf` – Current working directory
- `xdg_cache_home`, `xdg_config_home`, `xdg_data_home`, `xdg_state_home` – XDG base directories
- Context-independent [functions](#functions), including `arch()`, `os()`, `os_family()`, `num_cpus()`, and `choice()`; exclusions are listed below.
- All [filters](#filters): `absolute`, `dirname`, `basename`, `hash`, etc.

### Not available

- `mise_env` – This is what `.miserc.toml` defines; it cannot reference itself
- `exec()` – Requires settings, which are not yet loaded
- `read_file()` – Not registered in the early-init context (needs per-file directory resolution that is not set up at this stage)
- `mise_bin`, `mise_pid` – Not meaningful at this stage

### miserc.toml Examples

<div v-pre>

```toml
# /workspaces/vcs/.config/miserc.toml

# Use $HOME to set a ceiling path (stops config search at home directory)
ceiling_paths = ["{{ env.HOME }}"]

# Paths are relative to the directory containing this miserc file.
# Recursive glob patterns are supported.
ignored_config_paths = ["../vendor/**/mise.toml"]
```

</div>

Conditionals work too — `{% if %}` blocks at the top level produce empty lines when the
condition is false, which TOML ignores:

<div v-pre>

```toml
# ~/.config/mise/miserc.toml
{% if os() == "linux" %}
ceiling_paths = ["{{ env.HOME }}/work"]
{% endif %}
```

</div>

::: tip
If a template fails to render (e.g. due to an undefined variable), mise logs a warning
and falls back to the raw content.
:::

::: warning
If your `.miserc.toml` values contain literal <span v-pre>`{{`</span>, `{%`, or `{#` characters
(not intended as templates), wrap them in a `{% raw %}...{% endraw %}` block to prevent Tera
from interpreting them.
:::
