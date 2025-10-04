# Azure Static Website ARM Template Development

このリポジトリは、Azure Storage Account に対して ARM テンプレートを作成し、Azure CLI でデプロイしたうえで Static Website 機能を有効化・検証するためのワークスペースです。

## 前提条件

- Azure サブスクリプションへのアクセス権
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) 2.40 以降
- (任意) ARM テンプレートの編集に使用するエディタ
- Dev Container を利用する場合は、[VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) 拡張機能または GitHub Codespaces
- (任意) Claude Code / Codex CLI を使用する場合は、Amazon Bedrock API へのアクセス権

## フォルダ構成

```
.
├── README.md
├── .claude/
│   └── settings.local.json               # Claude Code ローカル設定
├── .devcontainer/
│   ├── devcontainer.json                 # Dev Container 設定
│   └── codex-config-template/
│       └── config.toml                   # Codex CLI 設定テンプレート
├── .mcp.json                             # MCP 設定
├── templates/
│   ├── storage-account.json              # ARM テンプレート（サブスクリプションレベル）
│   └── storage-account.parameters.json   # パラメーターファイル
└── scripts/
    ├── configure-bedrock.sh              # Bedrock API 環境設定スクリプト
    ├── copy-codex-config.sh              # Codex 設定コピースクリプト
    └── install-tools.sh                  # Claude Code / Codex CLI インストールスクリプト
```

## Azure CLI によるデプロイ手順

### 1. ログインと利用サブスクリプションの選択
```bash
az login
az account set --subscription <subscription-id-or-name>
```

### 2. リソースグループの作成

Azure CLIでリソースグループを作成します：

```bash
az group create \
  --name rg-staticwebsite-dev \
  --location japaneast \
  --tags environment=development project=static-website \
  --debug
```

### 3. パラメーターファイルの編集

`templates/storage-account.parameters.json` を編集し、以下の値を環境に合わせて変更してください：

- `storageAccountPrefix`: Storage Account名のプレフィックス（3-16文字、小文字と数字のみ）
  - 日付（yyyyMMdd形式、8文字）が自動的に付与されます
  - **重要**: プレフィックス + 日付の合計が3-24文字以内である必要があります
  - 例: `stwebdev`（7文字） → `stwebdev20251002`（15文字）
  - プレフィックスは最大16文字まで指定可能ですが、日付と合わせて24文字を超えないよう注意してください
- `dateString`: デプロイ日付（yyyyMMdd形式、8文字固定）
- `location`: デプロイ先リージョン（デフォルト: japaneast）
- `sku`: レプリケーション方式（デフォルト: Standard_LRS）
- `environment`: 環境（development, staging, production）

### 4. ARM テンプレートのデプロイ（リソースグループレベル）

作成したリソースグループにStorage Accountをデプロイします：

```bash
az deployment group create \
  --resource-group rg-staticwebsite-dev \
  --template-file templates/storage-account.json \
  --parameters @templates/storage-account.parameters.json \
  --debug
```

このコマンドにより、以下が作成されます：
- Storage Account（StorageV2、Hot tier）
- Blob Service（削除保護有効）

### 5. デプロイ結果の確認

```bash
# リソースグループの確認
az group show --name rg-staticwebsite-dev

# Storage Accountの確認（日付部分は実際のデプロイ日に置き換えてください）
az storage account show \
  --name stwebdev20251002 \
  --resource-group rg-staticwebsite-dev
```

## Static Website 検証フロー

> **注意**: ARM テンプレートでは Static Website 機能を直接有効化できないため、デプロイ後に Azure CLI で別途設定する必要があります。

1. **Static Website の有効化**
   ```bash
   # Storage Account名を環境変数に設定（デプロイ出力から取得）
   STORAGE_ACCOUNT_NAME=$(az deployment group show \
     --resource-group rg-staticwebsite-dev \
     --name storage-account \
     --query "properties.outputs.storageAccountName.value" -o tsv)

   az storage blob service-properties update \
     --account-name $STORAGE_ACCOUNT_NAME \
     --static-website \
     --index-document index.html \
     --404-document 404.html
   ```

   このコマンドにより、`$web` という特別なコンテナが自動的に作成されます。

2. **有効化結果の確認**
   ```bash
   az storage blob service-properties show \
     --account-name $STORAGE_ACCOUNT_NAME \
     --query "staticWebsite"
   ```

   出力例：
   ```json
   {
     "enabled": true,
     "errorDocument404Path": "404.html",
     "indexDocument": "index.html"
   }
   ```

3. **ウェブエンドポイントの確認**
   ```bash
   az storage account show \
     --name $STORAGE_ACCOUNT_NAME \
     --resource-group rg-staticwebsite-dev \
     --query "primaryEndpoints.web" \
     --output tsv
   ```

   出力されるURLにアクセスすると、静的Webサイトを確認できます（例: `https://stwebdev20251002.z11.web.core.windows.net/`）。

4. **サンプルコンテンツのアップロード（テスト用）**
   ```bash
   # index.htmlの作成
   echo '<h1>Hello, Azure Static Website!</h1>' > index.html
   echo '<h1>404 - Page Not Found</h1>' > 404.html

   # $webコンテナへアップロード
   az storage blob upload-batch \
     --account-name $STORAGE_ACCOUNT_NAME \
     --source . \
     --destination '$web' \
     --pattern "*.html"
   ```

5. **動作確認**

   ブラウザで手順3で取得したURLにアクセスし、「Hello, Azure Static Website!」が表示されることを確認します。

## Dev Container の利用方法

1. VS Code でこのリポジトリを開きます。
2. Dev Containers 拡張機能 (または GitHub Codespaces) を使い、`Dev Containers: Reopen in Container` を実行します。
3. 初回起動時に Azure CLI、Claude Code、Codex CLI および推奨ツールが自動的にインストールされます。

詳細は `.devcontainer/devcontainer.json` を参照してください。

## Claude Code / Codex CLI のセットアップ

### 1. Bedrock API の設定

Dev Container 内で以下のコマンドを実行し、Amazon Bedrock の API キーを設定します：

```bash
source scripts/configure-bedrock.sh
```

プロンプトに従って Bedrock API キーを入力してください。設定は `~/.claude/bedrock_env` に永続化され、次回以降は自動的に読み込まれます。

**設定される環境変数：**
- `AWS_BEARER_TOKEN_BEDROCK` - Bedrock API キー
- `AWS_REGION` - AWS リージョン (デフォルト: us-east-1)
- `CLAUDE_CODE_USE_BEDROCK` - Bedrock 使用フラグ
- `ANTHROPIC_MODEL` - プライマリモデル (デフォルト: us.anthropic.claude-sonnet-4-5-20250929-v1:0)
- `ANTHROPIC_SMALL_FAST_MODEL` - 高速モデル
- `CLAUDE_CODE_MAX_OUTPUT_TOKENS` - 最大出力トークン数 (デフォルト: 4096)
- `MAX_THINKING_TOKENS` - 最大思考トークン数 (デフォルト: 1024)

### 2. Codex CLI 設定のコピー (任意)

Codex CLI の設定テンプレートを使用する場合は、以下のコマンドを実行します：

```bash
bash scripts/copy-codex-config.sh
```

設定ファイルは `~/.codex/config.toml` にコピーされます。

### 3. Claude Code / Codex CLI の起動

セットアップ完了後、以下のコマンドが使用可能になります：

```bash
# Claude Code の起動
claude-code

# Codex CLI の起動
codex
```

## テンプレートの機能

このARMテンプレート（リソースグループレベル）には、以下のセキュリティとベストプラクティスが組み込まれています：

### 自動命名
- **日付の自動付与**: Storage Account名にデプロイ日付（yyyyMMdd形式）が自動的に追加されます
- **一意性の確保**: 毎日異なる名前が生成されるため、グローバルな一意性が向上します
- **例**: プレフィックス `stwebdev` → 実際の名前 `stwebdev20251002`

### セキュリティ設定
- **HTTPS通信のみ許可**: `supportsHttpsTrafficOnly: true`
- **TLS 1.2以上**: `minimumTlsVersion: TLS1_2`
- **暗号化**: Blob/File Serviceの暗号化が有効
- **アクセス層**: Hot tier（Static Websiteに最適）

### データ保護
- **Blob削除保護**: 7日間の保持期間
- **コンテナ削除保護**: 7日間の保持期間

### タグ管理
- **リソースグループ**: Azure CLIで作成時にタグを指定
  - `environment`: デプロイ環境（development/staging/production）
  - `project`: プロジェクト名（static-website）
- **Storage Account**: ARMテンプレートで以下のタグが自動的に付与
  - `environment`: デプロイ環境
  - `project`: プロジェクト名（static-website）
  - `managedBy`: 管理方法（ARM-Template）
  - `purpose`: 用途（Static-Website-Hosting）

### 出力値
ARMテンプレートのデプロイ後、以下の値が出力されます：
- `storageAccountName`: Storage Account名
- `storageAccountId`: Storage AccountのリソースID
- `primaryEndpoints`: プライマリエンドポイント（web含む）

## よく利用する追加コマンド

- **What-Ifデプロイ（変更内容の事前確認）**:
  ```bash
  az deployment group what-if \
    --resource-group rg-staticwebsite-dev \
    --template-file templates/storage-account.json \
    --parameters @templates/storage-account.parameters.json \
    --debug
  ```

- **Bicep との連携**:
  ```bash
  az bicep install
  az bicep upgrade
  ```

- **静的コンテンツのアップロード**:
  ```bash
  # Storage Account名を取得（デプロイ名は自動的にテンプレートファイル名から生成されます）
  STORAGE_ACCOUNT_NAME=$(az deployment group show \
    --resource-group rg-staticwebsite-dev \
    --name storage-account \
    --query "properties.outputs.storageAccountName.value" -o tsv)

  az storage blob upload-batch \
    --account-name $STORAGE_ACCOUNT_NAME \
    --destination '$web' \
    --source ./dist
  ```

- **削除保護の確認**:
  ```bash
  az storage blob service-properties show \
    --account-name $STORAGE_ACCOUNT_NAME \
    --query "{deleteRetention: deleteRetentionPolicy, containerDelete: containerDeleteRetentionPolicy}"
  ```

## トラブルシューティング

### Azure 関連

- **Storage Account 名が重複しているエラー**
  - Storage Account名はグローバルに一意である必要があります
  - `templates/storage-account.parameters.json` の `storageAccountPrefix` を変更してください
  - 日付が自動的に付与されるため、通常は重複しません
  - 推奨形式: `st<プロジェクト名><環境>` （例: `stwebdev` → 実際は `stwebdev20251002`）

- **Storage Account 名の長さエラー**
  - Storage Account名は3-24文字以内である必要があります
  - プレフィックス（最大16文字）+ 日付（8文字）= 最大24文字
  - エラーが発生した場合は、`storageAccountPrefix` を短くしてください
  - 例: `stwebdev`（7文字）は問題なし、`verylongprefix123`（17文字）はエラー

- **Static Website が有効化できない**
  - Storage Account の `kind` が `StorageV2` であることを確認してください（このテンプレートでは自動設定）
  - `allowBlobPublicAccess` が `true` であることを確認してください

- **削除保護が機能しない**
  - 削除されたBlobは7日間保持されます
  - 復元する場合は、以下のコマンドを使用：
    ```bash
    # Storage Account名を指定（または環境変数から取得）
    STORAGE_ACCOUNT_NAME=stwebdev20251002

    # 削除されたBlobを確認
    az storage blob list --account-name $STORAGE_ACCOUNT_NAME --container-name '$web' --include d

    # Blobを復元
    az storage blob undelete --account-name $STORAGE_ACCOUNT_NAME --container-name '$web' --name <blob-name>
    ```

### Claude Code / Codex CLI 関連

- **Bedrock API キーが認識されない場合**
  - `source scripts/configure-bedrock.sh` を再実行して設定を確認してください
  - `~/.claude/bedrock_env` ファイルが存在し、正しい内容が書き込まれているか確認してください

- **npm コマンドが見つからない場合**
  - Dev Container が正しく起動しているか確認してください
  - `.devcontainer/devcontainer.json` で Node.js feature が有効になっているか確認してください

## ライセンス

このリポジトリのコードとドキュメントは、特に指定がない限り MIT ライセンスを想定しています。必要に応じて修正してください。
