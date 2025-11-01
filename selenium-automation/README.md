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

## Selenium自動化とAI処理

このプロジェクトでは、Seleniumによる画面自動化とVertex AI（Claude）を組み合わせたインテリジェントな画面処理自動化を実現します。

### セットアップ

#### 1. Python環境のセットアップ

Pipenvを使用して仮想環境を構築します：

```bash
# Pipenv環境の有効化
pipenv shell

# または、Pipenv経由でコマンドを実行
pipenv run python examples/01_basic_scraping.py
```

#### 2. 必要なパッケージ

以下のパッケージがインストールされています：

- `selenium` - Web自動化フレームワーク
- `webdriver-manager` - ChromeDriverの自動管理
- `anthropic[vertex]` - Vertex AI経由でClaude APIを使用
- `google-cloud-aiplatform` - Vertex AIサポート
- `python-dotenv` - 環境変数管理
- `beautifulsoup4` - HTML解析
- `lxml` - XML/HTML処理
- `pandas` - データ処理

### プロジェクト構造

```
selenium-automation/
├── src/                    # メインソースコード
│   ├── automation/         # Selenium自動化モジュール
│   │   ├── browser.py      # ブラウザ操作
│   │   └── scraper.py      # データ抽出
│   ├── ai_processing/      # AI処理モジュール
│   │   └── analyzer.py     # コンテンツ分析
│   └── utils/              # ユーティリティ
│       ├── config.py       # 設定管理
│       ├── logger.py       # ロギング
│       └── file_utils.py   # ファイル操作
├── examples/               # サンプルスクリプト
│   ├── 01_basic_scraping.py      # 基本的なスクレイピング
│   ├── 02_text_analysis.py       # テキスト分析
│   ├── 03_structured_data.py     # 構造化データ抽出
│   └── 04_form_interaction.py    # フォーム操作
├── tests/                  # テストコード
├── output/                 # 実行結果の出力先
├── Pipfile                 # Python依存関係定義
└── .env                    # 環境変数設定
```

### 使用例

#### 1. 基本的なスクレイピング

```bash
pipenv run python examples/01_basic_scraping.py
```

Webページにアクセスし、スクリーンショットとHTMLソースを取得します。

#### 2. テキスト分析（AI活用）

```bash
pipenv run python examples/02_text_analysis.py
```

Webページからテキストを抽出し、AIで以下を実行：
- 要約生成
- キーポイント抽出
- 質問応答

#### 3. 構造化データ抽出

```bash
pipenv run python examples/03_structured_data.py
```

Webページから表などの構造化データを抽出し、CSV保存とAI分析を実行します。

#### 4. フォーム操作

```bash
pipenv run python examples/04_form_interaction.py
```

フォームを検出し、AIで適切なデータを生成して入力します。

### カスタムスクリプトの作成

独自の自動化スクリプトを作成する例：

```python
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation.browser import Browser
from automation.scraper import Scraper
from ai_processing.analyzer import ContentAnalyzer
from utils.logger import setup_logger
from utils.config import config

# ロギング設定
logger = setup_logger()

def main():
    # AI分析器の初期化
    analyzer = ContentAnalyzer()

    # ブラウザ起動（コンテキストマネージャで自動クリーンアップ）
    with Browser(headless=False) as browser:
        # ページにアクセス
        browser.navigate("https://example.com")
        browser.wait_for_page_load()

        # HTMLを取得してパース
        html = browser.get_page_source()
        scraper = Scraper(html)

        # テキスト抽出
        text = scraper.get_text()

        # AIで分析
        summary = analyzer.summarize(text)
        print(f"要約: {summary}")

        # スクリーンショット
        browser.screenshot(str(config.output_dir / "screenshot.png"))

if __name__ == "__main__":
    main()
```

### 主要クラスとメソッド

#### Browser クラス (src/automation/browser.py)

```python
# ブラウザインスタンス作成
browser = Browser(headless=False)

# ページ遷移
browser.navigate("https://example.com")

# 要素の検索
element = browser.find_element(By.CSS_SELECTOR, ".class-name")

# テキスト入力
browser.input_text(By.NAME, "username", "test_user")

# クリック
browser.click(By.ID, "submit-button")

# スクリーンショット
browser.screenshot("output/screenshot.png")

# ブラウザ終了
browser.close()
```

#### Scraper クラス (src/automation/scraper.py)

```python
# HTMLからスクレイパー作成
scraper = Scraper(html_content)

# テキスト抽出
text = scraper.get_text(".main-content")

# 表データの抽出
df = scraper.extract_table("table.data")

# 構造化データの抽出
items = scraper.extract_structured_data(
    item_selector=".product",
    field_selectors={
        "name": ".product-name",
        "price": ".product-price"
    }
)
```

#### ContentAnalyzer クラス (src/ai_processing/analyzer.py)

```python
# AI分析器の初期化
analyzer = ContentAnalyzer()

# 要約生成
summary = analyzer.summarize(text, max_length="medium")

# キーポイント抽出
key_points = analyzer.extract_key_points(text, num_points=5)

# 質問応答
answer = analyzer.answer_question(text, "What is this about?")

# 構造化情報の抽出
data = analyzer.extract_structured_info(
    text,
    fields=["name", "date", "price"]
)
```

### 環境変数

`.env`ファイルで以下の設定をカスタマイズできます：

```bash
# Vertex AI設定（setup-vertex-ai.shで自動設定）
ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
CLOUD_ML_REGION=global
ANTHROPIC_MODEL=claude-sonnet-4-5@20250929

# ブラウザ設定（オプション）
BROWSER_HEADLESS=false          # ヘッドレスモード
BROWSER_TIMEOUT=30              # タイムアウト（秒）

# 出力設定（オプション）
OUTPUT_DIR=output               # 出力ディレクトリ
LOG_LEVEL=INFO                  # ログレベル
```

### トラブルシューティング

#### ChromeDriverが見つからない

`webdriver-manager`が自動的にChromeDriverをダウンロードしますが、失敗する場合：

```bash
# Chromeブラウザが最新版か確認
# Chromeを更新後、再度スクリプトを実行
```

#### Vertex AIの認証エラー

```bash
# Application Default Credentialsを再設定
gcloud auth application-default login
```

#### メモリ不足エラー

ヘッドレスモードを有効にしてメモリ使用量を削減：

```python
browser = Browser(headless=True)
```

または、環境変数で設定：

```bash
export BROWSER_HEADLESS=true
```

### ベストプラクティス

1. **コンテキストマネージャの使用**: ブラウザは常に`with`文で使用し、自動クリーンアップを保証
2. **待機処理**: ページロード待機やタイムアウト設定を適切に行う
3. **エラーハンドリング**: try-exceptで例外を適切に処理
4. **ログ出力**: `setup_logger()`でロギングを有効化し、デバッグを容易に
5. **レート制限**: 同一サイトへの連続アクセスは適切な間隔を空ける

## 参考リンク

### Vertex AI / Claude Code
- [Google Cloud Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Claude on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)

### Selenium / Web自動化
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Selenium with Python](https://selenium-python.readthedocs.io/)
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager)
