#!/usr/bin/env bash
# Render-check every tracked chezmoi template (#160 T12.5, decision 19).
# A template that references undefined data or has bad syntax fails here
# at commit time instead of at `chezmoi init --apply` inside the
# container (onCreate).
# Thin wrapper by design (zero-bash-logic rule): iterate + render, no logic.
#
# Hermetic by construction (PR #169, two CI-only failures):
# - `chezmoi execute-template` reads template data from the machine's
#   existing chezmoi config, which a fresh CI runner does not have
#   (`.remote` resolved locally, failed in CI). So render
#   home/.chezmoi.toml.tmpl first — validating it AND producing the
#   [data] block — then render every other template against that temp
#   config.
# - That config's [scriptEnv] pins PATH to $HOME/.local/bin + mise shims
#   (+ system dirs), and chezmoi applies it to `output`-spawned commands
#   (probe-verified; the docs' "scripts only" undersells it). CI installs
#   mise outside every pinned dir, so `output "mise" …` failed there. Run
#   chezmoi with a temp HOME seeded with .local/bin/mise → the real mise,
#   making the exec environment machine-independent too.
set -euo pipefail

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
fakehome="$tmpdir/home"
mkdir -p "$fakehome/.local/bin"
ln -s "$(command -v mise)" "$fakehome/.local/bin/mise"
cfg="$tmpdir/chezmoi.toml"

# The CONFIG template renders in init context with its own function
# namespace (promptBoolOnce, …) that execute-template lacks; `--init`
# enables it.
HOME="$fakehome" chezmoi --source "$PWD/home" execute-template --init \
	<home/.chezmoi.toml.tmpl >"$cfg"

rc=0
while IFS= read -r tmpl; do
	# Rendered above; it is the data source, not a consumer.
	if [ "$tmpl" = "home/.chezmoi.toml.tmpl" ]; then
		continue
	fi
	if ! HOME="$fakehome" chezmoi --config "$cfg" --source "$PWD/home" \
		execute-template <"$tmpl" >/dev/null; then
		echo "$tmpl: chezmoi execute-template failed (bad syntax or undefined data)" >&2
		rc=1
	fi
done < <(git ls-files 'home/**/*.tmpl' 'home/*.tmpl')
exit $rc
