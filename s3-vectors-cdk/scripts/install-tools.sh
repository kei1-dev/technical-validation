#!/usr/bin/env bash

set -euo pipefail

main() {
  echo "[setup] Codex CLI / Claude Code install script"

  if [ ! -f package.json ] && [ ! -f requirements.txt ]; then
    echo "[info] 実行パス: $(pwd)"
  fi

  : "${CODEX_INSTALL_CMD:=npm install -g @openai/codex@latest}"
  : "${CLAUDE_CODE_INSTALL_CMD:=npm install -g @anthropic-ai/claude-code@latest}"

  install_codex_cli
  install_claude_code

  cat <<'EOT'
EOT
}

install_codex_cli() {
  local name="Codex CLI"
  local cmd="$CODEX_INSTALL_CMD"

  echo "[setup] Installing ${name}"
  if [[ "${cmd}" == npm* ]] && ! command -v npm >/dev/null 2>&1; then
    echo "[warn] npm が見つかりません。Node.js feature の導入を確認してください。"
    return
  fi

  if [ -z "${cmd}" ]; then
    echo "[skip] CODEX_INSTALL_CMD が空のためスキップします。"
    return
  fi

  if eval "${cmd}"; then
    echo "[done] ${name} installation completed."
  else
    echo "[warn] ${name} のインストールに失敗しました。コマンド: ${cmd}" >&2
  fi
}

install_claude_code() {
  local name="Claude Code"
  local cmd="$CLAUDE_CODE_INSTALL_CMD"

  echo "[setup] Installing ${name}"
  if [[ "${cmd}" == npm* ]] && ! command -v npm >/dev/null 2>&1; then
    echo "[warn] npm が見つかりません。Node.js feature の導入を確認してください。"
    return
  fi

  if [ -z "${cmd}" ]; then
    echo "[skip] CLAUDE_CODE_INSTALL_CMD が空のためスキップします。"
    return
  fi

  if eval "${cmd}"; then
    echo "[done] ${name} installation completed."
  else
    echo "[warn] ${name} のインストールに失敗しました。コマンド: ${cmd}" >&2
  fi
}

main "$@"
