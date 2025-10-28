#!/usr/bin/env bash

# Copy the Codex CLI config template into the default config directory.
set -euo pipefail

main() {
  local repo_root template dest_dir dest_file

  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
  template="${repo_root}/.devcontainer/codex-config-template/config.toml"

  if [[ ! -f "${template}" ]]; then
    echo "[error] Template not found at ${template}" >&2
    exit 1
  fi

  dest_dir="${CODEX_HOME:-${HOME}/.codex}"
  dest_file="${dest_dir}/config.toml"

  mkdir -p "${dest_dir}"
  cp "${template}" "${dest_file}"
  echo "[done] Codex CLI config written to ${dest_file}"
}

main "$@"
