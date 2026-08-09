# hk Builtins Audit

<!-- GENERATED FILE — do not edit by hand.
     Regenerate: mise run hk-audit
     Gated by: workflow.hk-builtins-audit (suites.toml) + the hk_audit step.
     Authored content lives in python/src/dotfiles_setup/hk_builtins_audit.py
     (NOT_ADOPTED); everything else is read from `hk builtins` + the configs. -->

- **hk version:** hk 1.54.1
- **Builtins available:** 145
- **Wired as builtins:** 28
- **Steps defined in total:** 64 (36 custom, with their own check/fix commands)

A *wired builtin* is referenced as `Builtins.<name>`. A *custom step* is a
`["name"] { … }` block carrying its own commands — it may share a
name with a builtin without being one, which is how the previous
hand-written audit came to list `ruff_format` and `editorconfig-checker`
as builtins in use.

## Wired builtins (28)

| Builtin | Declared in |
|---------|-------------|
| `actionlint` | hk.pkl |
| `betterleaks` | hk.pkl |
| `byte_order_marker` | hk-common.pkl |
| `check_added_large_files` | hk-common.pkl |
| `check_case_conflict` | hk-common.pkl |
| `check_conventional_commit` | hk.pkl |
| `check_executables_have_shebangs` | hk-common.pkl |
| `check_merge_conflict` | hk-common.pkl |
| `check_symlinks` | hk-common.pkl |
| `detect_private_key` | hk-common.pkl |
| `fix_smart_quotes` | hk-common.pkl |
| `ghalint_action` | hk.pkl |
| `ghalint_workflow` | hk.pkl |
| `gitleaks` | hk-common.pkl |
| `hadolint` | hk.pkl |
| `mise` | hk.pkl |
| `mixed_line_ending` | hk-common.pkl |
| `newlines` | hk-common.pkl |
| `no_commit_to_branch` | hk.pkl |
| `pkl` | hk.pkl |
| `python_check_ast` | hk.pkl |
| `python_debug_statements` | hk.pkl |
| `shellcheck` | hk.pkl, hk-image.pkl |
| `taplo` | hk.pkl |
| `trailing_whitespace` | hk-common.pkl |
| `typos` | hk-common.pkl |
| `yamllint` | hk.pkl |
| `zizmor` | hk.pkl |

## Custom steps (36)

Not builtins. Each carries its own `check`/`fix`, so `hk builtins` has no
opinion about them, and neither does this table beyond recording them.

| Step | Declared in |
|------|-------------|
| `agnix` | hk.pkl |
| `bash_logic_budget` | hk.pkl |
| `check` | hk.pkl |
| `chezmoi_template_render` | hk.pkl |
| `classifier_axes` | hk.pkl |
| `claude_agents_md_pairs` | hk.pkl |
| `claude_md_import_stub` | hk.pkl |
| `commit-msg` | hk.pkl |
| `contract_token_uniqueness` | hk.pkl |
| `devcontainer_json_validate` | hk.pkl |
| `doc_refs` | hk.pkl |
| `docker_bake_check` | hk.pkl |
| `dockerfile_host_user_thin_overlay` | hk.pkl |
| `editorconfig-checker` | hk.pkl |
| `fix` | hk.pkl |
| `ghcr_publish_prereqs` | hk.pkl |
| `hk_audit` | hk.pkl |
| `hk_version_parity` | hk.pkl |
| `md_size_budget` | hk.pkl |
| `mise_lock_integrity` | hk.pkl |
| `no_env_dump` | hk.pkl |
| `no_global_skill_leakage` | hk.pkl |
| `no_grep_q_under_pipefail` | hk.pkl |
| `no_hk_depends` | hk.pkl |
| `no_lint_skip` | hk.pkl |
| `no_platform_literals` | hk.pkl |
| `pre-commit` | hk.pkl, hk-image.pkl |
| `pre-push` | hk.pkl |
| `py_ty` | hk.pkl |
| `renovate_config_validate` | hk.pkl |
| `require_pipefail` | hk.pkl |
| `ruff` | hk.pkl |
| `ruff_format` | hk.pkl |
| `test` | hk.pkl |
| `uv_lock_check` | hk.pkl |
| `workflow_hk_skip_hooks` | hk.pkl |

## Deliberately not adopted (24)

The only authored section — a judgement no tool can recover. Edit it in
`hk_builtins_audit.py`; an entry that stops naming a real builtin, or that
names one now wired, fails the gate.

| Builtin | Reason |
|---------|--------|
| `biome` | No JS source in project |
| `black` | Superseded by ruff format |
| `dprint` | Redundant with the taplo/yamlfmt/prettier set |
| `eslint` | No JS source in project |
| `flake8` | Superseded by ruff |
| `go_fmt` | No Go source in project |
| `golangci_lint` | No Go source in project |
| `isort` | Superseded by ruff's I rules |
| `markdown_lint` | Runs markdownlint v1; repo uses markdownlint-cli2 (#154) |
| `mdschema` | Requires a schema file that does not exist yet (#160 T12) |
| `mypy` | Using ty instead |
| `pinact` | GitHub API rate-limit in the hook; use `mise run pin-actions` |
| `pylint` | Superseded by ruff |
| `rubocop` | No Ruby source in project |
| `rumdl` | 591 findings across 56 files — a burn-down project, deferred (#160 T12) |
| `rustfmt` | No Rust source in project |
| `ryl` | Redundant with yamllint |
| `stylelint` | No CSS files |
| `terraform` | No Terraform files |
| `tf_lint` | No Terraform files |
| `tombi` | Redundant with taplo |
| `tombi_format` | Redundant with the taplo formatter |
| `vale` | No formal style guide; network dependency in the hook |
| `xmllint` | No XML files in project |

## Not yet considered (93)

Available in this hk version, neither wired nor explicitly declined.
Listed so the unexamined remainder is visible rather than implied — the
previous audit's biggest silent gap was 87 builtins it never mentioned.

```
alejandra, aqua_update_checksum, asciidoctor, astro, brakeman, buf_format
buf_lint, buildifier_format, buildifier_lint, bundle_audit, cargo_check, cargo_clippy
cargo_deny, cargo_fmt, check_byte_order_marker, clang_format, cmake_format, cocogitto_commit_msg
contextlint, cpp_lint, dclint, deadnix, deno, deno_check
editorconfig-checker, erb, err_check, fasterer, fix_byte_order_marker, go_fumpt
go_imports, go_lines, go_sec, go_vet, go_vuln_check, gomod_tidy
google_java_format, harper, harper_commit_message, hclfmt, hk_test, jq
just_format, knip, knip_strict, ktlint, luacheck, lychee
mix_compile, mix_fmt, mix_test, nil, nix_fmt, nixf_diagnose
nixpkgs_format, ox_lint, oxfmt, php_cs, pinact_update, pkl_format
prettier, reek, revive, rubocop_server, ruff, ruff_format
rumdl_format, ryl_markdown, selene, shellharden, sherif, shfmt
sorbet, sort_package_json, sql_fluff, standard_js, standard_rb, staticcheck
stylua, swiftlint, taplo_format, textlint, tofu, tsc
tsserver, ty, vacuum, vp_check, vp_fmt, vp_lint
xo, yamlfmt, yq
```
