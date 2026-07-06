#!/usr/bin/env bash
# Render-check every tracked chezmoi template (#160 T12.5, decision 19).
# A template that references undefined data or has bad syntax fails here
# at commit time instead of at `chezmoi init --apply` inside the
# container (onCreate).
# Thin wrapper by design (zero-bash-logic rule): iterate + render, no logic.
#
# Hermetic by construction: `chezmoi execute-template` reads template data
# from the machine's existing chezmoi config, which a fresh CI runner does
# not have (PR #169: `.remote` resolved locally, failed in CI). So render
# home/.chezmoi.toml.tmpl first — validating it AND producing the [data]
# block — then render every other template against that temp config.
set -euo pipefail

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
cfg="$tmpdir/chezmoi.toml"

# The CONFIG template renders in init context with its own function
# namespace (promptBoolOnce, …) that execute-template lacks; `--init`
# enables it.
chezmoi --source "$PWD/home" execute-template --init \
	<home/.chezmoi.toml.tmpl >"$cfg"

rc=0
while IFS= read -r tmpl; do
	# Rendered above; it is the data source, not a consumer.
	if [ "$tmpl" = "home/.chezmoi.toml.tmpl" ]; then
		continue
	fi
	if ! chezmoi --config "$cfg" --source "$PWD/home" execute-template \
		<"$tmpl" >/dev/null; then
		echo "$tmpl: chezmoi execute-template failed (bad syntax or undefined data)" >&2
		rc=1
	fi
done < <(git ls-files 'home/**/*.tmpl' 'home/*.tmpl')
exit $rc
