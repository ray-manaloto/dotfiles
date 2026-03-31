#!/bin/sh
# -e: exit on error
# -u: exit on unset variables
set -eu

if ! chezmoi="$(command -v chezmoi)"; then
    bin_dir="${HOME}/.local/bin"
    chezmoi="${bin_dir}/chezmoi"
    script_dir="$(cd -P -- "$(dirname -- "$(command -v -- "$0")")" && pwd -P)"
    chezmoi_version="latest"
    if [ -f "${script_dir}/.chezmoiversion" ]; then
        chezmoi_version="$(tr -d '[:space:]' < "${script_dir}/.chezmoiversion")"
    fi
    echo "Installing chezmoi to '${chezmoi}'" >&2
    if command -v curl >/dev/null; then
        chezmoi_install_script="$(curl -fsSL get.chezmoi.io)"
    elif command -v wget >/dev/null; then
        chezmoi_install_script="$(wget -qO- get.chezmoi.io)"
    else
        echo "Error: curl or wget required." >&2
        exit 1
    fi
    sh -c "${chezmoi_install_script}" -- -b "${bin_dir}" -t "${chezmoi_version}"
    unset chezmoi_install_script bin_dir
fi

script_dir="$(cd -P -- "$(dirname -- "$(command -v -- "$0")")" && pwd -P)"
# Ensure mise (installed by run_once_before) is on PATH for template output functions
export PATH="$HOME/.local/bin:$PATH"
exec "$chezmoi" init --apply --source="${script_dir}" --no-tty --force
