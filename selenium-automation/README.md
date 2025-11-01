# Google Cloud Vertex AI Setup for Claude Code

このディレクトリには、Claude CodeでGoogle Cloud Vertex AIを使用するための設定スクリプトが含まれています。

## 前提条件

以下の準備が必要です：

1. **Google Cloudプロジェクト**
   - Google Cloudアカウントを持っていること
   - プロジェクトが作成済みであること
   - 課金が有効化されていること

2. **Google Cloud CLI（オプション）**
   - gcloud CLIは必須ではありません
   - 未インストールの場合、セットアップスクリプトが自動インストールを提案します
   - 公式インストーラーを使用して自動インストールされます（`~/google-cloud-sdk`）
   - Apple Silicon (M1/M2/M3)とIntel Macの両方に対応
   - 手動インストール方法: https://cloud.google.com/sdk/docs/install

3. **認証（対話モードでは自動、非対話モードでは事前に必要）**
   - **gcloudユーザー認証**: gcloud CLIコマンドを実行するため（`gcloud auth login`）
   - **Application Default Credentials (ADC)**: Claude CodeがVertex AIを利用するため（`gcloud auth application-default login`）
   - 詳細は[認証エラーが発生する](#認証エラーが発生する)セクションを参照

4. **Claude Code**
   - Claude Codeがインストールされていること

## セットアップ手順

### 1. Vertex AI設定のセットアップ

#### 対話モード（デフォルト）

対話的にセットアップを実行：

```bash
./scripts/setup-vertex-ai.sh
```

スクリプトが各ステップで確認を求めます。

#### 非対話モード（完全自動）

確認プロンプトなしで自動実行：

```bash
./scripts/setup-vertex-ai.sh -y YOUR_PROJECT_ID
```

**使用可能なオプション:**

```bash
./scripts/setup-vertex-ai.sh [OPTIONS] [PROJECT_ID]

OPTIONS:
  -y, --yes                  すべての確認をスキップ（自動承認）
  -p, --project PROJECT      プロジェクトIDを指定
  --skip-gcloud-install      gcloud CLIインストールをスキップ
  --skip-profile-update      シェルプロファイル更新をスキップ
  --skip-auth                ADC認証をスキップ
  -h, --help                 ヘルプ表示
```

**使用例:**

```bash
# 完全自動セットアップ（推奨: 認証を事前に実行）
gcloud auth login
gcloud auth application-default login
./scripts/setup-vertex-ai.sh -y my-project-id

# Application Default Credentials (ADC) だけ後で手動実行
gcloud auth login
./scripts/setup-vertex-ai.sh -y --skip-auth my-project-id
gcloud auth application-default login

# gcloud CLIがインストール済みの場合
gcloud auth login
gcloud auth application-default login
./scripts/setup-vertex-ai.sh -y --skip-gcloud-install --project my-project-id

# 環境変数を使用
export GOOGLE_CLOUD_PROJECT=my-project-id
gcloud auth login
gcloud auth application-default login
./scripts/setup-vertex-ai.sh -y
```

**重要: 非対話モード（-y）を使用する場合は、事前に認証を完了してください**

#### 処理内容

スクリプトは以下の処理を行います：

- Google Cloud CLIのインストール確認
  - 未インストールの場合、自動インストールを提案（対話モード）または自動実行（-y）
  - Google公式インストーラーを使用して自動インストール
  - アーキテクチャ（Apple Silicon/Intel）を自動検出
  - インストール先: `~/google-cloud-sdk`
  - シェル検出（Zsh/Bash）と自動プロファイル更新
  - `.zshrc`または`.bashrc`に自動追加（バックアップ作成）
- プロジェクトIDの設定（引数、`-p`オプション、または対話入力）
- **gcloudユーザー認証の確認**（`gcloud auth login`）
  - gcloud CLIコマンド実行に必要
  - 対話モード: 未認証の場合は自動実行
  - 非対話モード（-y）: 未認証の場合はエラーで終了（事前認証が必要）
- Vertex AI APIの有効化（未有効の場合）
- **Application Default Credentials (ADC)の設定**（`gcloud auth application-default login`）
  - Claude CodeがVertex AIを利用するために必要
  - 対話モード: 未設定の場合は自動実行
  - 非対話モード（-y）: スキップ（後で手動実行が必要）
- リージョン設定（デフォルト: `asia-northeast1` - 東京）
- `.env`ファイルの作成（環境変数参照用）
- `.claude/settings.json`ファイルの作成（Claude Code設定）
- `.gitignore`の更新

### 2. Claude Codeの使用

セットアップ完了後、以下のコマンドでClaude CodeがVertex AIを経由してClaude Sonnet 4.5を使用します：

```bash
claude
```

**重要:**
- `.claude/settings.json`が自動的に読み込まれるため、`source .env`は不要です
- このディレクトリ内で`claude`コマンドを実行すると、Vertex AIが使用されます
- 起動時に "Sonnet 4.5 · Claude Pro" ではなく "Sonnet 4.5 · Vertex AI" と表示されることを確認してください

### 3. 設定の削除

Vertex AI設定を削除する場合は、以下のコマンドを実行します：

#### 対話モード（デフォルト）

確認プロンプトありで実行：

```bash
./scripts/teardown-vertex-ai.sh
```

#### 非対話モード（完全自動）

確認プロンプトなしで自動実行：

```bash
./scripts/teardown-vertex-ai.sh -y
```

**使用可能なオプション:**

```bash
./scripts/teardown-vertex-ai.sh [OPTIONS]

OPTIONS:
  -y, --yes                    すべての確認をスキップ（自動承認）
  --skip-shell-cleanup         シェルプロファイルのクリーンアップをスキップ
  --skip-gcloud-uninstall      gcloud CLI のアンインストールをスキップ
  -h, --help                   ヘルプ表示
```

**使用例:**

```bash
# 対話モード（確認プロンプトあり）
./scripts/teardown-vertex-ai.sh

# 完全自動削除（全て削除）
./scripts/teardown-vertex-ai.sh -y

# プロジェクト設定のみ削除（gcloud CLI とシェルプロファイルは保持）
./scripts/teardown-vertex-ai.sh -y --skip-shell-cleanup --skip-gcloud-uninstall

# 設定とgcloud CLIを削除、シェルプロファイルは保持
./scripts/teardown-vertex-ai.sh --skip-shell-cleanup
```

#### 削除される内容

スクリプトは以下の処理を行います：

**常に削除:**
- `.env`ファイル（バックアップ作成）
- `.claude/settings.json`（バックアップ作成）
- `.claude/`ディレクトリ（空の場合）

**デフォルトで削除（オプションでスキップ可能）:**
- シェルプロファイル（`.zshrc`または`.bashrc`）から gcloud CLI の設定行を削除
  - 削除前にバックアップ作成（例: `~/.zshrc.bak.20250101-120000`）
  - setup スクリプトで追加された行のみを削除
- `~/google-cloud-sdk` ディレクトリ（gcloud CLI本体）

**削除されないもの:**
- Vertex AI API の有効化状態（GCPプロジェクト側）
- Application Default Credentials（`~/.config/gcloud/application_default_credentials.json`）
- gcloud のプロジェクト設定

#### バックアップ

すべての削除前に自動的にバックアップが作成されます：

- バックアップディレクトリ: `.vertex-ai-backup-YYYYMMDD-HHMMSS`
- バックアップ内容:
  - `.env` ファイル
  - `.claude/` ディレクトリ
  - シェルプロファイル（変更する場合のみ）

## 作成されるファイル

### `.claude/settings.json`

**Claude Codeの設定ファイル（メイン設定）:**

```json
{
  "env": {
    "CLAUDE_CODE_USE_VERTEX": "1",
    "ANTHROPIC_VERTEX_PROJECT_ID": "your-project-id",
    "CLOUD_ML_REGION": "global",
    "VERTEX_REGION_CLAUDE_4_5_SONNET": "asia-northeast1",
    "ANTHROPIC_MODEL": "claude-sonnet-4-5@20250929"
  }
}
```

このファイルがClaude Codeによって自動的に読み込まれ、Vertex AI統合が有効になります。

### `.env`

**環境変数の参照用ファイル：**

```bash
# Claude Code Vertex AI Configuration
# Required environment variables for Claude Code with Vertex AI

# Enable Vertex AI integration
CLAUDE_CODE_USE_VERTEX=1

# Google Cloud Project ID
ANTHROPIC_VERTEX_PROJECT_ID=your-project-id

# Cloud ML Region (use 'global' for automatic routing, or specific region)
CLOUD_ML_REGION=global

# Regional model override for asia-northeast1 (Tokyo)
VERTEX_REGION_CLAUDE_4_5_SONNET=asia-northeast1

# Default model to use
ANTHROPIC_MODEL=claude-sonnet-4-5@20250929

# Optional: Disable prompt caching if needed
# DISABLE_PROMPT_CACHING=1
```

**注意:** このファイルは参照用です。実際の設定は`.claude/settings.json`から読み込まれます。

## トラブルシューティング

### gcloud CLIがインストールされていない

セットアップスクリプトを実行すると、自動インストールを提案します：

**自動インストールの流れ:**
1. Google公式インストーラーを自動ダウンロード＆インストール
2. アーキテクチャ（Apple Silicon/Intel）を自動検出
3. インストール先: `~/google-cloud-sdk`
4. シェル（Zsh/Bash）を自動検出
5. シェルプロファイル（`.zshrc`または`.bashrc`）への自動追加を提案
6. 承認すると：
   - バックアップファイル作成（例: `~/.zshrc.bak.20250101-120000`）
   - プロファイルに自動追記
   - 現在のセッションとすべての新しいセッションで利用可能

**重要:** スクリプトは `~/google-cloud-sdk` が存在する場合、自動的にPATHに追加します。そのため、一度インストールすれば、シェルプロファイルに追加していなくても、スクリプト実行中は利用可能です。

**手動でプロファイルを追加する場合:**

自動追加を拒否した場合、または後で追加したい場合：

```bash
# Zshの場合
echo "if [ -f '$HOME/google-cloud-sdk/path.zsh.inc' ]; then source '$HOME/google-cloud-sdk/path.zsh.inc'; fi" >> ~/.zshrc
echo "if [ -f '$HOME/google-cloud-sdk/completion.zsh.inc' ]; then source '$HOME/google-cloud-sdk/completion.zsh.inc'; fi" >> ~/.zshrc
source ~/.zshrc

# Bashの場合
echo "if [ -f '$HOME/google-cloud-sdk/path.bash.inc' ]; then source '$HOME/google-cloud-sdk/path.bash.inc'; fi" >> ~/.bashrc
echo "if [ -f '$HOME/google-cloud-sdk/completion.bash.inc' ]; then source '$HOME/google-cloud-sdk/completion.bash.inc'; fi" >> ~/.bashrc
source ~/.bashrc
```

**完全に手動でインストール:**
- 公式サイトからダウンロード: https://cloud.google.com/sdk/docs/install

### Vertex AI APIが有効化できない

プロジェクトで課金が有効になっているか確認してください：
https://console.cloud.google.com/billing

### 認証エラーが発生する

#### 2種類の認証について

このスクリプトでは**2種類の認証**が必要です：

1. **gcloudユーザー認証** (`gcloud auth login`)
   - **目的**: gcloud CLIコマンド（`gcloud services enable`など）を実行するため
   - **エラー例**: "You do not currently have an active account selected"
   - **解決方法**:
     ```bash
     gcloud auth login
     ```

2. **Application Default Credentials (ADC)** (`gcloud auth application-default login`)
   - **目的**: Claude CodeがVertex AI APIを利用するため
   - **エラー例**: Vertex AIへの接続エラー
   - **解決方法**:
     ```bash
     gcloud auth application-default login
     ```

#### 認証状態の確認

```bash
# gcloudユーザー認証の確認
gcloud auth list

# ADCの確認
gcloud auth application-default print-access-token
```

#### 非対話モード（-y）を使用した場合

**推奨フロー（両方を事前に実行）:**
```bash
gcloud auth login
gcloud auth application-default login
./scripts/setup-vertex-ai.sh -y my-project-id
```

**ADCだけ後で実行する場合:**
```bash
gcloud auth login
./scripts/setup-vertex-ai.sh -y --skip-auth my-project-id
gcloud auth application-default login
```

### Claude Sonnet 4.5が利用できない

リージョンによってはモデルが利用できない場合があります。別のリージョンを試してください：

- `us-central1` (アイオワ)
- `us-east5` (コロンバス)
- `europe-west1` (ベルギー)

リージョンを変更するには、`.env`ファイルの`GOOGLE_CLOUD_REGION`を編集してください。

### 認証情報を完全にリセットしたい

```bash
gcloud auth application-default revoke
```

### teardown スクリプトでシェルプロファイルを誤って変更してしまった

teardown スクリプトは削除前に自動的にバックアップを作成します：

**バックアップからの復元:**

```bash
# バックアップファイルを確認
ls -la ~/.zshrc.bak.* # または ~/.bashrc.bak.*

# 最新のバックアップから復元（タイムスタンプを確認）
cp ~/.zshrc.bak.20250101-120000 ~/.zshrc
# または
cp ~/.bashrc.bak.20250101-120000 ~/.bashrc

# 復元後、ターミナルを再起動またはプロファイルを再読み込み
source ~/.zshrc  # または source ~/.bashrc
```

**手動で gcloud CLI の設定を再追加:**

シェルプロファイルに以下を追加：

```bash
# Zsh の場合
echo "if [ -f '$HOME/google-cloud-sdk/path.zsh.inc' ]; then source '$HOME/google-cloud-sdk/path.zsh.inc'; fi" >> ~/.zshrc
echo "if [ -f '$HOME/google-cloud-sdk/completion.zsh.inc' ]; then source '$HOME/google-cloud-sdk/completion.zsh.inc'; fi" >> ~/.zshrc
source ~/.zshrc

# Bash の場合
echo "if [ -f '$HOME/google-cloud-sdk/path.bash.inc' ]; then source '$HOME/google-cloud-sdk/path.bash.inc'; fi" >> ~/.bashrc
echo "if [ -f '$HOME/google-cloud-sdk/completion.bash.inc' ]; then source '$HOME/google-cloud-sdk/completion.bash.inc'; fi" >> ~/.bashrc
source ~/.bashrc
```

### 誤って gcloud CLI を削除してしまった

setup スクリプトを再実行すれば自動的に再インストールされます：

```bash
./scripts/setup-vertex-ai.sh
```

または、手動でインストール：

```bash
# 公式サイトからダウンロード
# https://cloud.google.com/sdk/docs/install

# または setup スクリプトのインストール部分のみ実行したい場合
# スクリプトが自動検出してインストールを提案します
```

### 非対話モードでエラーが発生する

**「Project ID is required in non-interactive mode」エラー:**

非対話モード（`-y`）では、プロジェクトIDを引数で指定する必要があります：

```bash
# 正しい使用方法
./scripts/setup-vertex-ai.sh -y my-project-id
# または
./scripts/setup-vertex-ai.sh -y --project my-project-id
# または環境変数を使用
export GOOGLE_CLOUD_PROJECT=my-project-id
./scripts/setup-vertex-ai.sh -y
```

**ヘルプの表示:**

使用方法を確認したい場合：

```bash
./scripts/setup-vertex-ai.sh -h
# または
./scripts/setup-vertex-ai.sh --help
```

## セキュリティに関する注意事項

### コミット可能なファイル

以下のファイルは**機密情報を含まない**ため、Gitにコミットして共有できます：

- `.env` - 環境変数の設定（プロジェクトID、リージョンなど）
- `.claude/settings.json` - Claude Code設定

これらのファイルには以下の情報のみが含まれます：
- Google CloudプロジェクトID
- リージョン設定
- モデル名
- 設定フラグ

### 機密情報の保存場所

以下の認証情報は**別の場所に安全に保存**されます：

- **Application Default Credentials (ADC)**
  - 保存場所: `~/.config/gcloud/application_default_credentials.json`
  - Gitにコミットされません
  - ユーザーごとに個別に管理

### 注意事項

- サービスアカウントキーファイル（`.json`）を使用する場合は、絶対にリポジトリに含めないでください
- `.gitignore`に追加して保護してください

## バックアップについて

セットアップおよび削除スクリプトは自動的にバックアップを作成します：

### セットアップ時のバックアップ

**setup-vertex-ai.sh 実行時:**

1. **シェルプロファイルのバックアップ**
   - gcloud CLIインストール時にシェルプロファイルを変更する前に自動バックアップ
   - 形式: `~/.zshrc.bak.YYYYMMDD-HHMMSS` または `~/.bashrc.bak.YYYYMMDD-HHMMSS`
   - 場所: ホームディレクトリ（`~/`）

### 削除時のバックアップ

**teardown-vertex-ai.sh 実行時:**

1. **Vertex AI 設定のバックアップ**
   - `.env` ファイル
   - `.claude/` ディレクトリ
   - 形式: `.vertex-ai-backup-YYYYMMDD-HHMMSS/`
   - 場所: プロジェクトディレクトリ

2. **シェルプロファイルのバックアップ**（クリーンアップする場合）
   - シェルプロファイルから gcloud CLI 設定を削除する前に自動バックアップ
   - 形式: `~/.zshrc.bak.YYYYMMDD-HHMMSS` または `~/.bashrc.bak.YYYYMMDD-HHMMSS`
   - 場所: ホームディレクトリ（`~/`）

### バックアップの復元

バックアップファイルは手動で復元できます：

```bash
# プロジェクト設定の復元
cp .vertex-ai-backup-YYYYMMDD-HHMMSS/.env .
cp -r .vertex-ai-backup-YYYYMMDD-HHMMSS/.claude .

# シェルプロファイルの復元
cp ~/.zshrc.bak.YYYYMMDD-HHMMSS ~/.zshrc
source ~/.zshrc
```

## 参考リンク

- [Google Cloud Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Claude on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
