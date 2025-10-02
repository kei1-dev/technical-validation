#!/usr/bin/env bash

__CONFIGURE_BEDROCK_SAVED_SHELLOPTS="$(set +o)"
set -euo pipefail
trap 'eval "${__CONFIGURE_BEDROCK_SAVED_SHELLOPTS}"; trap - RETURN; unset __CONFIGURE_BEDROCK_SAVED_SHELLOPTS' RETURN

DEFAULT_REGION=${DEFAULT_REGION:-"us-east-1"}
DEFAULT_PRIMARY_MODEL=${DEFAULT_PRIMARY_MODEL:-"us.anthropic.claude-3-7-sonnet-20250219-v1:0"}
DEFAULT_FAST_MODEL=${DEFAULT_FAST_MODEL:-"us.anthropic.claude-3-5-haiku-20241022-v1:0"}
DEFAULT_FAST_MODEL_REGION=${DEFAULT_FAST_MODEL_REGION:-"${DEFAULT_REGION}"}
DEFAULT_MAX_OUTPUT_TOKENS=${DEFAULT_MAX_OUTPUT_TOKENS:-"4096"}
DEFAULT_MAX_THINKING_TOKENS=${DEFAULT_MAX_THINKING_TOKENS:-"1024"}

CONFIG_DIR="${HOME}/.claude"
CONFIG_FILE="${CONFIG_DIR}/bedrock_env"
PROFILE_FILE="${PROFILE_FILE:-${HOME}/.bash_profile}"
PROFILE_SNIPPET_BEGIN="# >>> configure-bedrock.sh >>>"
PROFILE_SNIPPET_END="# <<< configure-bedrock.sh <<<"

AUTO_MODE=false
QUIET_MODE=false

main() {
  ensure_sourced
  parse_args "$@"

  if load_persisted_config; then
    if should_reuse_persisted_config; then
      export_api_key_config
      show_summary "persisted"
      return
    fi
  fi

  if ${AUTO_MODE}; then
    [[ ${QUIET_MODE} == true ]] || echo "[warn] Bedrock の永続化設定がまだ完了していません。'source scripts/configure-bedrock.sh' を実行して初期設定を完了してください。" >&2
    return
  fi

  if ! collect_api_key_inputs; then
    return 1
  fi
  export_api_key_config
  persist_config
  ensure_shell_init_hook
  show_summary "interactive"
}

ensure_sourced() {
  if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "[error] このスクリプトは 'source scripts/configure-bedrock.sh' のように実行してください。" >&2
    exit 1
  fi
}

parse_args() {
  while (($#)); do
    case "$1" in
      --auto)
        AUTO_MODE=true
        ;;
      --quiet)
        QUIET_MODE=true
        ;;
      *)
        echo "[warn] 未知のオプション '$1' を無視します。" >&2
        ;;
    esac
    shift || true
  done
}

load_persisted_config() {
  if [[ -f "${CONFIG_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${CONFIG_FILE}"
    return 0
  fi
  return 1
}

should_reuse_persisted_config() {
  if ${AUTO_MODE}; then
    return 0
  fi

  if [[ ${QUIET_MODE} == true ]]; then
    return 0
  fi

  local answer
  while true; do
    read -rp "[prompt] 既存の Bedrock 設定が見つかりました。現在の設定を再利用しますか？ [Y/n]: " answer
    case "${answer}" in
      ""|[Yy]|[Yy][Ee][Ss])
        return 0
        ;;
      [Nn]|[Nn][Oo])
        return 1
        ;;
      *)
        echo "[warn] Y か N で回答してください。" >&2
        ;;
    esac
  done
}

collect_api_key_inputs() {
  echo "[prompt] Claude Code で使用する Bedrock API キーを入力してください。"
  read -rp "Bedrock API Key: " AWS_BEARER_TOKEN_BEDROCK

  if [[ -z "${AWS_BEARER_TOKEN_BEDROCK}" ]]; then
    echo "[error] Bedrock API Key は必須です。" >&2
    return 1
  fi

  AWS_REGION=${DEFAULT_REGION}
}

export_api_key_config() {
  : "${AWS_BEARER_TOKEN_BEDROCK:?AWS_BEARER_TOKEN_BEDROCK is required.}"
  : "${AWS_REGION:?AWS_REGION is required.}"

  export AWS_BEARER_TOKEN_BEDROCK
  export AWS_REGION
  export CLAUDE_CODE_USE_BEDROCK="1"
  export ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-${DEFAULT_PRIMARY_MODEL}}"
  export ANTHROPIC_SMALL_FAST_MODEL="${ANTHROPIC_SMALL_FAST_MODEL:-${DEFAULT_FAST_MODEL}}"
  export ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION="${ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION:-${DEFAULT_FAST_MODEL_REGION}}"
  export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-${DEFAULT_MAX_OUTPUT_TOKENS}}"
  export MAX_THINKING_TOKENS="${MAX_THINKING_TOKENS:-${DEFAULT_MAX_THINKING_TOKENS}}"
}

persist_config() {
  mkdir -p "${CONFIG_DIR}"

  {
    printf "export AWS_BEARER_TOKEN_BEDROCK=%q\n" "${AWS_BEARER_TOKEN_BEDROCK}"
    printf "export AWS_REGION=%q\n" "${AWS_REGION}"
    printf "export CLAUDE_CODE_USE_BEDROCK=%q\n" "${CLAUDE_CODE_USE_BEDROCK}"
    printf "export ANTHROPIC_MODEL=%q\n" "${ANTHROPIC_MODEL}"
    printf "export ANTHROPIC_SMALL_FAST_MODEL=%q\n" "${ANTHROPIC_SMALL_FAST_MODEL}"
    printf "export ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION=%q\n" "${ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION}"
    printf "export CLAUDE_CODE_MAX_OUTPUT_TOKENS=%q\n" "${CLAUDE_CODE_MAX_OUTPUT_TOKENS}"
    printf "export MAX_THINKING_TOKENS=%q\n" "${MAX_THINKING_TOKENS}"
  } > "${CONFIG_FILE}"

  chmod 600 "${CONFIG_FILE}"
}

ensure_shell_init_hook() {
  local profile_file="${PROFILE_FILE}"

  mkdir -p "$(dirname "${profile_file}")"
  [[ -f "${profile_file}" ]] || touch "${profile_file}"

  local snippet
  IFS='' read -r -d '' snippet <<'SNIPPET' || true
# >>> configure-bedrock.sh >>>
BEDROCK_ENV_FILE="$HOME/.claude/bedrock_env"
if [[ -f "$BEDROCK_ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$BEDROCK_ENV_FILE"
fi
# <<< configure-bedrock.sh <<<
SNIPPET

  if grep -Fq "${PROFILE_SNIPPET_BEGIN}" "${profile_file}"; then
    local tmp
    tmp=$(mktemp)
    awk -v begin="${PROFILE_SNIPPET_BEGIN}" -v end="${PROFILE_SNIPPET_END}" -v snippet="${snippet}" '
      BEGIN {in_block = 0}
      index($0, begin) == 1 {
        print snippet;
        in_block = 1;
        next;
      }
      index($0, end) == 1 {
        in_block = 0;
        next;
      }
      in_block == 1 {next}
      {print}
    ' "${profile_file}" > "${tmp}"
    mv "${tmp}" "${profile_file}"
  else
    printf '\n%s\n' "${snippet}" >> "${profile_file}"
  fi
}

show_summary() {
  ${QUIET_MODE} && return

  case "$1" in
    persisted)
      echo "[done] 永続化済みの Bedrock 設定を読み込みました。"
      ;;
    *)
      echo "[done] Bedrock API 環境変数を設定し、${CONFIG_FILE} に保存しました。"
      ;;
  esac

  cat <<EOT
- AWS_BEARER_TOKEN_BEDROCK
- AWS_REGION=${AWS_REGION}
- CLAUDE_CODE_USE_BEDROCK=${CLAUDE_CODE_USE_BEDROCK}
- ANTHROPIC_MODEL=${ANTHROPIC_MODEL}
- ANTHROPIC_SMALL_FAST_MODEL=${ANTHROPIC_SMALL_FAST_MODEL}
- ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION=${ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION}
- CLAUDE_CODE_MAX_OUTPUT_TOKENS=${CLAUDE_CODE_MAX_OUTPUT_TOKENS}
- MAX_THINKING_TOKENS=${MAX_THINKING_TOKENS}
EOT
}

main "$@"
