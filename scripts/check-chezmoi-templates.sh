#!/usr/bin/env bash
# Render-check every tracked chezmoi template (#160 T12.5, decision 19).
# `chezmoi execute-template --source home` renders each *.tmpl with the
# source's .chezmoi.toml.tmpl data on THIS machine — a template that
# references undefined data or has bad syntax fails here at commit time
# instead of at `chezmoi init --apply` inside the container (onCreate).
# Thin wrapper by design (zero-bash-logic rule): iterate + render, no logic.
set -euo pipefail

rc=0
while IFS= read -r tmpl; do
	# The CONFIG template renders in init context with its own function
	# namespace (promptBoolOnce, …) that execute-template lacks; `--init`
	# enables it. Dotfile templates render in the normal context.
	if [ "$tmpl" = "home/.chezmoi.toml.tmpl" ]; then
		render() { chezmoi --source "$PWD/home" execute-template --init; }
	else
		render() { chezmoi --source "$PWD/home" execute-template; }
	fi
	if ! render <"$tmpl" >/dev/null; then
		echo "$tmpl: chezmoi execute-template failed (bad syntax or undefined data)" >&2
		rc=1
	fi
done < <(git ls-files 'home/**/*.tmpl' 'home/*.tmpl')
exit $rc
