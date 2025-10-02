# Coding Agent Dev Container テンプレート

このリポジトリは Codex CLI と Claude Code を素早く利用開始できる VS Code Dev Container テンプレートです。コンテナを起動すると、必要な言語ランタイムに加えて AWS Bedrock 連携準備や Codex CLI 用設定テンプレートが揃った状態になります。

## リポジトリ構成

- `.devcontainer/devcontainer.json` : Dev Container のベースイメージ、Features、`postCreateCommand` を定義。
- `.devcontainer/codex-config-template/config.toml` : Codex CLI の設定テンプレート。`copy-codex-config.sh` でホームディレクトリに複製できます。
- `scripts/install-tools.sh` : Codex CLI / Claude Code をインストールするセットアップスクリプト。
- `scripts/configure-bedrock.sh` : Bedrock API キーなどを対話的に設定・永続化するユーティリティ。`source` で呼び出します。
- `scripts/copy-codex-config.sh` : Codex CLI 設定テンプレートを `~/.codex/config.toml` へコピーする補助スクリプト。

## 利用手順

1. 任意の作業フォルダに本テンプレートをコピーするか、サブモジュールとして追加します。
2. VS Code と Remote Containers 拡張を使用してフォルダを開き、`Reopen in Container` を選択します。
3. コンテナ初回起動時に `postCreateCommand` が `scripts/install-tools.sh` を実行し、`@openai/codex@latest` と `@anthropic-ai/claude-code@latest` をグローバルにインストールします。
   - 別の導入手順を使いたい場合は、起動前に `CODEX_INSTALL_CMD` / `CLAUDE_CODE_INSTALL_CMD` 環境変数へ任意のコマンドを設定してください。
4. Codex CLI の設定が必要な場合は、`bash scripts/copy-codex-config.sh` を実行してテンプレートを `~/.codex/config.toml` にコピーします。
5. AWS Bedrock を利用する場合は、コンテナ内で `source scripts/configure-bedrock.sh` を実行し、案内に従って API キーを登録します。

## Dev Container 設定

- ベースイメージは `mcr.microsoft.com/devcontainers/base:ubuntu`。
- Features により Node.js (LTS), Python 3.11, AWS CLI をインストール。
- 推奨 VS Code 拡張機能 (Remote Containers, Docker, Python, Node) を自動追加。
- `postCreateCommand` で `scripts/install-tools.sh` を呼び出し、開発ツールの導入を自動化します。

## スクリプト詳細

- `scripts/install-tools.sh`
  - `CODEX_INSTALL_CMD` / `CLAUDE_CODE_INSTALL_CMD` に設定されたコマンドを実行してツールを導入します (既定値はどちらも npm グローバルインストール)。
  - npm が見つからない場合は警告を出して処理を終了し、カスタムコマンドの設定例を表示します。
- `scripts/configure-bedrock.sh`
  - `source scripts/configure-bedrock.sh` の形で実行します。`--auto` や `--quiet` オプションも利用可能です。
  - Bedrock API キーを入力すると、必要な環境変数を export し `~/.claude/bedrock_env` に保存します。
  - `PROFILE_FILE` (既定: `~/.bash_profile`) に自動で読み込み用スニペットを挿入し、次回シェル起動時も設定が適用されるようにします。
- `scripts/copy-codex-config.sh`
  - `.devcontainer/codex-config-template/config.toml` を `~/.codex/config.toml` へコピーします。
  - 出力先は `CODEX_HOME` 環境変数で変更可能です。

## AWS Bedrock 連携

`source scripts/configure-bedrock.sh` を実行すると、以下の環境変数が設定・永続化されます (値は既定値、必要に応じて入力・編集してください)。

```bash
export AWS_BEARER_TOKEN_BEDROCK=<Bedrock API Key>
export AWS_REGION='us-east-1'
export CLAUDE_CODE_USE_BEDROCK='1'
export ANTHROPIC_MODEL='us.anthropic.claude-3-7-sonnet-20250219-v1:0'
export ANTHROPIC_SMALL_FAST_MODEL='us.anthropic.claude-3-5-haiku-20241022-v1:0'
export ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION='us-east-1'
export CLAUDE_CODE_MAX_OUTPUT_TOKENS='4096'
export MAX_THINKING_TOKENS='1024'
```

テンプレートに含まれない追加の環境変数が必要な場合は、`~/.claude/bedrock_env` を直接編集するか、再度スクリプトを実行して上書きしてください。

## 補足

- Dev Container の Features や拡張機能は `.devcontainer/devcontainer.json` を編集してカスタマイズできます。
- チームや環境に合わせて `scripts/install-tools.sh` のデフォルトコマンドや Bedrock のデフォルト値 (`DEFAULT_REGION` など) をリポジトリで上書きして利用する運用も想定しています。
