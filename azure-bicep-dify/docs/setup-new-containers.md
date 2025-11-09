# 新しいコンテナのセットアップガイド

このドキュメントは、Sandbox、SSRF Proxy、Plugin Daemon、Worker Beatコンテナをデプロイする前に必要な手動セットアップ手順を説明します。

## 前提条件

- Azure CLIがインストールされている
- PostgreSQL Flexible Serverが既にデプロイされている
- Storage Accountが既にデプロイされている（Bicepで自動作成）
- 適切な権限（Contributor以上）がある

## 1. PostgreSQL データベースの作成

Plugin Daemon用に専用のデータベース `dify_plugin` を作成します。

### Azure Portal経由

1. Azure Portalにログイン
2. PostgreSQL Flexible Serverリソースに移動
3. 左メニューから「データベース」を選択
4. 「+ 追加」をクリック
5. データベース名: `dify_plugin`
6. 文字セット: `UTF8`
7. 照合順序: `en_US.utf8`
8. 「保存」をクリック

### Azure CLI経由

```bash
# 環境変数を設定
RESOURCE_GROUP="dify-dev-rg"
POSTGRES_SERVER="dify-dev-postgres"
DATABASE_NAME="dify_plugin"

# データベースを作成
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $POSTGRES_SERVER \
  --database-name $DATABASE_NAME
```

### psql経由

```bash
# PostgreSQLに接続
psql "host=<your-postgres-server>.postgres.database.azure.com port=5432 dbname=postgres user=<admin-user> password=<password> sslmode=require"

# データベースを作成
CREATE DATABASE dify_plugin;

# 確認
\l
```

## 2. セキュリティキーの生成

新しいコンテナ用に3つのセキュリティキーを生成します。

### Sandbox API Key

Sandboxコンテナの認証に使用されます。

```bash
# 32バイトのランダムキーを生成
openssl rand -base64 32

# 出力例: 
# xK8vN2mP9qR4sT6uV7wX8yZ0aB1cD2eF3gH4iJ5kL6m=
```

生成されたキーを保存してください。後でBicepパラメータファイルに追加します。

### Plugin Daemon Server Key

Plugin Daemonの認証に使用されます。

```bash
# 42バイトのランダムキーを生成
openssl rand -base64 42

# 出力例:
# pQ9rS8tU7vW6xY5zA4bC3dE2fG1hI0jK9lM8nO7pQ6rS5tU4vW3xY2zA1bC0dE=
```

生成されたキーを保存してください。

### Plugin Inner API Key

Plugin DaemonとAPIコンテナ間の通信に使用されます。

```bash
# 42バイトのランダムキーを生成
openssl rand -base64 42

# 出力例:
# aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aB4cD5eF6gH7iJ8kL9mN0oP=
```

生成されたキーを保存してください。

### キーの保存

生成したキーを安全な場所に保存します：

```bash
# キーをファイルに保存（例）
echo "SANDBOX_API_KEY=<generated-key>" >> .env.secrets
echo "PLUGIN_DAEMON_KEY=<generated-key>" >> .env.secrets
echo "PLUGIN_INNER_API_KEY=<generated-key>" >> .env.secrets

# ファイルのパーミッションを制限
chmod 600 .env.secrets
```

**重要**: これらのキーは機密情報です。Gitにコミットしないでください。

## 3. Bicepパラメータファイルの更新

生成したキーをBicepパラメータファイルに追加します。

### dev環境（bicep/main/parameters/dev.bicepparam）

```bicep
// 新しいコンテナイメージ
param sandboxImage = 'langgenius/dify-sandbox:0.2.12'
param ssrfProxyImage = 'ubuntu/squid:latest'
param pluginDaemonImage = 'langgenius/dify-plugin-daemon:0.4.0'

// セキュリティキー（生成した値に置き換えてください）
param sandboxApiKey = '<SANDBOX_API_KEY>'
param pluginDaemonKey = '<PLUGIN_DAEMON_KEY>'
param pluginInnerApiKey = '<PLUGIN_INNER_API_KEY>'
```

### prod環境（bicep/main/parameters/prod.bicepparam）

```bicep
// 新しいコンテナイメージ（特定のバージョンを使用）
param sandboxImage = 'langgenius/dify-sandbox:0.2.12'
param ssrfProxyImage = 'ubuntu/squid:latest'
param pluginDaemonImage = 'langgenius/dify-plugin-daemon:0.4.0'

// セキュリティキー（生成した値に置き換えてください）
param sandboxApiKey = '<SANDBOX_API_KEY>'
param pluginDaemonKey = '<PLUGIN_DAEMON_KEY>'
param pluginInnerApiKey = '<PLUGIN_INNER_API_KEY>'
```

## 4. Blob Storageコンテナの確認

`dify-plugins` Blobコンテナは、Bicepデプロイメント時に自動的に作成されます。手動作成は不要です。

確認方法：

```bash
# Storage Accountを取得
STORAGE_ACCOUNT=$(az storage account list \
  --resource-group $RESOURCE_GROUP \
  --query "[?contains(name, 'dify')].name" -o tsv)

# コンテナを確認
az storage container list \
  --account-name $STORAGE_ACCOUNT \
  --auth-mode login \
  --query "[].name" -o table
```

期待される出力：
```
Name
------------------
dify-app-storage
dify-dataset
dify-tools
dify-plugins
```

## 5. デプロイメント前のチェックリスト

デプロイを実行する前に、以下を確認してください：

- [ ] PostgreSQL データベース `dify_plugin` が作成されている
- [ ] Sandbox API Keyが生成され、パラメータファイルに追加されている
- [ ] Plugin Daemon Keyが生成され、パラメータファイルに追加されている
- [ ] Plugin Inner API Keyが生成され、パラメータファイルに追加されている
- [ ] パラメータファイルが正しい環境（dev/prod）に対応している
- [ ] 生成したキーが安全に保存されている
- [ ] `.env.secrets` ファイルが `.gitignore` に含まれている

## 6. デプロイメントの実行

すべての準備が完了したら、デプロイメントを実行します：

```bash
# dev環境へのデプロイ
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --location japaneast

# prod環境へのデプロイ
bash scripts/deploy.sh \
  --environment prod \
  --resource-group dify-prod-rg \
  --location japaneast
```

## 7. デプロイメント後の検証

デプロイメントが完了したら、以下を確認します：

### コンテナの状態確認

```bash
# すべてのContainer Appsを確認
az containerapp list \
  --resource-group $RESOURCE_GROUP \
  --query "[].{Name:name, Status:properties.runningStatus, Replicas:properties.template.scale.minReplicas}" \
  --output table
```

期待される出力：
```
Name                    Status    Replicas
----------------------  --------  --------
dify-dev-web            Running   1
dify-dev-api            Running   1
dify-dev-worker         Running   1
dify-dev-nginx          Running   1
dify-dev-sandbox        Running   0/1
dify-dev-ssrf-proxy     Running   0/1
dify-dev-plugin-daemon  Running   0/1
dify-dev-worker-beat    Running   1
```

### データベース接続の確認

```bash
# Plugin Daemonのログを確認
az containerapp logs show \
  --name dify-dev-plugin-daemon \
  --resource-group $RESOURCE_GROUP \
  --follow

# データベース接続成功のメッセージを探す
# 例: "Successfully connected to database dify_plugin"
```

### Blob Storageの確認

```bash
# dify-pluginsコンテナが存在することを確認
az storage container show \
  --name dify-plugins \
  --account-name $STORAGE_ACCOUNT \
  --auth-mode login
```

## トラブルシューティング

### 問題: データベース作成に失敗する

**エラー**: `ERROR: permission denied to create database`

**解決策**: 
- 管理者ユーザーで接続していることを確認
- PostgreSQL Flexible Serverの接続文字列が正しいか確認

### 問題: キー生成コマンドが見つからない

**エラー**: `openssl: command not found`

**解決策**:
- Windows: Git Bashを使用するか、WSLをインストール
- macOS: opensslは標準でインストールされています
- Linux: `sudo apt-get install openssl` または `sudo yum install openssl`

### 問題: Bicepデプロイメントでシークレットエラー

**エラー**: `The parameter 'sandboxApiKey' is required but was not provided`

**解決策**:
- パラメータファイルにすべてのキーが追加されているか確認
- キーの値がプレースホルダー（`<SANDBOX_API_KEY>`）のままになっていないか確認

## セキュリティのベストプラクティス

1. **キーのローテーション**: 90日ごとにセキュリティキーをローテーションすることを推奨
2. **キーの保存**: Azure Key Vaultの使用を検討（将来の拡張）
3. **アクセス制御**: 最小権限の原則に従う
4. **監査ログ**: すべてのキー使用を監査ログで追跡
5. **環境分離**: dev/prod環境で異なるキーを使用

## 参考資料

- [Azure PostgreSQL Flexible Server Documentation](https://learn.microsoft.com/azure/postgresql/flexible-server/)
- [Azure Blob Storage Documentation](https://learn.microsoft.com/azure/storage/blobs/)
- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Dify Plugin System](https://docs.dify.ai/plugins)
