# Dify on Azure - デプロイ手順書

このドキュメントでは、Dify on AzureインフラストラクチャをBicepテンプレートを使用してデプロイする詳細な手順を説明します。

## 目次

- [前提条件](#前提条件)
- [事前準備](#事前準備)
- [デプロイ手順](#デプロイ手順)
- [デプロイ後の設定](#デプロイ後の設定)
- [検証手順](#検証手順)
- [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 必要なツール

以下のツールがインストールされていることを確認してください：

#### 1. Azure CLI (バージョン 2.40.0以上)

```bash
# インストール確認
az --version

# インストール（未インストールの場合）
# macOS
brew install azure-cli

# Windows
# https://aka.ms/installazurecliwindows からインストーラーをダウンロード

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

#### 2. Bicep CLI

```bash
# インストール
az bicep install

# バージョン確認
az bicep version

# アップグレード
az bicep upgrade
```

#### 3. jq (JSON処理ツール - 推奨)

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Windows
# https://stedolan.github.io/jq/download/ からダウンロード
```

#### 4. Git

```bash
# インストール確認
git --version

# インストール（未インストールの場合）
# macOS
brew install git

# Ubuntu/Debian
sudo apt-get install git
```

### Azureアカウントとサブスクリプション

1. **Azureサブスクリプション**
   - アクティブなAzureサブスクリプションが必要
   - 無料試用版でも可能（一部制限あり）

2. **必要な権限**
   - **最低限**: サブスクリプションまたはリソースグループに対する`共同作成者`ロール
   - **推奨**: `所有者`または`ユーザーアクセス管理者`ロール（ロール割り当てが必要なため）

3. **リソースプロバイダーの登録**

以下のリソースプロバイダーが登録されている必要があります：

```bash
# 一括登録スクリプト
az provider register --namespace Microsoft.Network
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Cache
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.Automation
az provider register --namespace Microsoft.ManagedIdentity

# 登録状態の確認
az provider show --namespace Microsoft.App --query "registrationState"
```

> **注意**: プロバイダーの登録には数分かかる場合があります。

### 前提条件の自動チェック

前提条件チェックスクリプトを実行して、環境が整っているか確認できます：

```bash
bash scripts/validate-prerequisites.sh
```

---

## 事前準備

### 1. リポジトリのクローン

```bash
# リポジトリをクローン
git clone <repository-url>
cd azure-bicep-dify
```

### 2. Azureへのログイン

```bash
# Azureにログイン
az login

# サブスクリプションの一覧表示
az account list --output table

# 使用するサブスクリプションを設定
az account set --subscription "<subscription-id>"

# 現在のサブスクリプションを確認
az account show --output table
```

### 3. Azure AD Object IDの取得

Key Vaultへのアクセスに必要なAzure AD Object IDを取得します：

```bash
# 現在ログインしているユーザーのObject IDを取得
az ad signed-in-user show --query id -o tsv
```

この値をメモしておいてください。パラメータファイルで使用します。

### 4. パラメータファイルの編集

デプロイする環境に応じて、パラメータファイルを編集します。

#### 開発環境の場合

```bash
nano bicep/parameters/dev.bicepparam
```

以下のパラメータを更新：

```bicep
// データベース認証情報
param postgresqlAdminUsername = 'difydbadmin'  // 任意のユーザー名
param postgresqlAdminPassword = 'CHANGE_ME_STRONG_PASSWORD_123!'  // 強力なパスワードに変更

// Key Vault管理者
param keyVaultAdminObjectId = ''  // 手順3で取得したObject IDを設定
```

**パスワード要件**：
- 最低8文字
- 大文字、小文字、数字、記号を含む
- PostgreSQLの予約語を避ける

#### 本番環境の場合

```bash
nano bicep/parameters/prod.bicepparam
```

開発環境と同様のパラメータに加えて、以下も設定：

```bicep
// SSL証明書（後で設定する場合は空欄のまま）
param sslCertificateSecretId = ''

// コンテナイメージのバージョン（本番環境では固定バージョン推奨）
param difyWebImage = 'langgenius/dify-web:0.6.13'
param difyApiImage = 'langgenius/dify-api:0.6.13'
param difyWorkerImage = 'langgenius/dify-api:0.6.13'
```

---

## デプロイ手順

### 方法1: 自動デプロイスクリプトの使用（推奨）

最も簡単な方法です。全ての手順が自動化されています。

#### 開発環境のデプロイ

```bash
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --location japaneast
```

#### 本番環境のデプロイ

```bash
bash scripts/deploy.sh \
  --environment prod \
  --resource-group dify-prod-rg \
  --location japaneast
```

#### What-If分析（変更内容の事前確認）

```bash
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --what-if
```

デプロイには **20〜30分** かかります。

### 方法2: 手動デプロイ

より細かい制御が必要な場合は、手動でデプロイできます。

#### ステップ1: リソースグループの作成

```bash
# 開発環境
az group create \
  --name dify-dev-rg \
  --location japaneast \
  --tags Environment=Development Project=Dify

# 本番環境
az group create \
  --name dify-prod-rg \
  --location japaneast \
  --tags Environment=Production Project=Dify Criticality=High
```

#### ステップ2: Bicepテンプレートのビルド

```bash
cd bicep
az bicep build --file main.bicep
```

エラーがないことを確認してください。

#### ステップ3: デプロイの検証

実際にデプロイする前に、テンプレートを検証します：

```bash
# 開発環境
az deployment group validate \
  --resource-group dify-dev-rg \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam

# 本番環境
az deployment group validate \
  --resource-group dify-prod-rg \
  --template-file main.bicep \
  --parameters parameters/prod.bicepparam
```

#### ステップ4: What-If分析（オプション）

デプロイされるリソースと変更内容を事前確認：

```bash
az deployment group what-if \
  --resource-group dify-dev-rg \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

出力例：
```
Resource and property changes are indicated with these symbols:
  + Create
  ~ Modify
  - Delete

The deployment will update the following scope:

Scope: /subscriptions/xxx/resourceGroups/dify-dev-rg

  + Microsoft.Network/virtualNetworks/dify-dev-vnet
  + Microsoft.DBforPostgreSQL/flexibleServers/dify-dev-postgres-xxx
  ...
```

#### ステップ5: デプロイの実行

```bash
# デプロイ名を作成（タイムスタンプ付き）
DEPLOYMENT_NAME="dify-deployment-$(date +%Y%m%d-%H%M%S)"

# 開発環境
az deployment group create \
  --name $DEPLOYMENT_NAME \
  --resource-group dify-dev-rg \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam \
  --verbose

# 本番環境
az deployment group create \
  --name $DEPLOYMENT_NAME \
  --resource-group dify-prod-rg \
  --template-file main.bicep \
  --parameters parameters/prod.bicepparam \
  --verbose
```

デプロイ中は進行状況が表示されます。

#### ステップ6: デプロイ結果の確認

```bash
# デプロイステータスの確認
az deployment group show \
  --name $DEPLOYMENT_NAME \
  --resource-group dify-dev-rg \
  --query properties.provisioningState

# 出力値の取得
az deployment group show \
  --name $DEPLOYMENT_NAME \
  --resource-group dify-dev-rg \
  --query properties.outputs \
  --output json | jq .
```

重要な出力値：
- `applicationGatewayPublicIp`: Application GatewayのパブリックIP
- `applicationGatewayFqdn`: Application GatewayのFQDN
- `keyVaultName`: Key Vault名
- `postgresqlServerFqdn`: PostgreSQLサーバーFQDN
- `storageAccountName`: ストレージアカウント名

---

## デプロイ後の設定

デプロイが完了したら、以下の設定を行います。

### 1. シークレットの設定

#### 方法1: 自動設定スクリプトの使用（推奨）

```bash
# Key Vault名を取得
KEYVAULT_NAME=$(az keyvault list \
  --resource-group dify-dev-rg \
  --query "[0].name" -o tsv)

# シークレット設定スクリプトを実行
bash scripts/setup-secrets.sh \
  --resource-group dify-dev-rg \
  --keyvault $KEYVAULT_NAME
```

このスクリプトは以下を自動的に設定します：
- アプリケーション秘密鍵
- データベース接続情報
- Redis接続情報
- ストレージアカウント情報

#### 方法2: 手動設定

```bash
# PostgreSQLパスワードの設定（必須）
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name postgresql-password \
  --value '<your-strong-password>'

# アプリケーション秘密鍵の生成と設定
SECRET_KEY=$(openssl rand -base64 32)
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name dify-secret-key \
  --value "$SECRET_KEY"
```

### 2. Container Appsの環境変数更新（シークレット参照）

Container Appsでシークレットを使用するには、環境変数を更新します：

```bash
# Container Appsにシークレットを追加
az containerapp update \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --set-env-vars \
    "DB_PASSWORD=secretref:postgresql-password" \
    "REDIS_PASSWORD=secretref:redis-password" \
    "SECRET_KEY=secretref:dify-secret-key"
```

### 3. カスタムドメインの設定（本番環境）

#### ステップ1: パブリックIPの取得

```bash
PUBLIC_IP=$(az network public-ip show \
  --resource-group dify-prod-rg \
  --name dify-prod-appgateway-pip \
  --query ipAddress -o tsv)

echo "Application Gateway Public IP: $PUBLIC_IP"
```

#### ステップ2: DNS設定

DNSプロバイダーでAレコードを追加：

```
Type: A
Name: dify (または @)
Value: <PUBLIC_IP>
TTL: 3600
```

例：
```
dify.yourdomain.com → 20.XXX.XXX.XXX
```

#### ステップ3: SSL証明書のアップロード

```bash
# PFX形式の証明書をKey Vaultにアップロード
az keyvault certificate import \
  --vault-name $KEYVAULT_NAME \
  --name dify-ssl-cert \
  --file /path/to/certificate.pfx \
  --password '<cert-password>'

# 証明書のシークレットIDを取得
CERT_SECRET_ID=$(az keyvault certificate show \
  --vault-name $KEYVAULT_NAME \
  --name dify-ssl-cert \
  --query sid -o tsv)

echo "SSL Certificate Secret ID: $CERT_SECRET_ID"
```

#### ステップ4: パラメータファイルの更新と再デプロイ

```bash
# prod.bicepparam を編集
nano bicep/parameters/prod.bicepparam

# sslCertificateSecretId を上記で取得した値に更新
param sslCertificateSecretId = '<CERT_SECRET_ID>'

# Application Gatewayモジュールを再デプロイ
az deployment group create \
  --name "dify-ssl-update-$(date +%Y%m%d-%H%M%S)" \
  --resource-group dify-prod-rg \
  --template-file bicep/main.bicep \
  --parameters bicep/parameters/prod.bicepparam
```

### 4. Difyアプリケーションの初期設定

#### ステップ1: Dify Webインターフェースへのアクセス

```bash
# Application Gateway FQDNを取得
APP_FQDN=$(az network public-ip show \
  --resource-group dify-dev-rg \
  --name dify-dev-appgateway-pip \
  --query dnsSettings.fqdn -o tsv)

echo "Access Dify at: http://$APP_FQDN"
```

ブラウザで `http://<APP_FQDN>` にアクセスします。

#### ステップ2: 初期セットアップウィザード

1. **管理者アカウントの作成**
   - メールアドレス
   - パスワード
   - 名前

2. **LLM APIキーの設定**
   - OpenAI API Key
   - または Azure OpenAI エンドポイント
   - または他のLLMプロバイダー

3. **ワークスペースの作成**
   - ワークスペース名
   - 説明

---

## 検証手順

デプロイとセットアップが完了したら、以下を検証します。

### 1. インフラストラクチャの検証

#### リソースグループの確認

```bash
# デプロイされたリソースの一覧
az resource list \
  --resource-group dify-dev-rg \
  --output table

# リソース数の確認（約30リソース）
az resource list \
  --resource-group dify-dev-rg \
  --query "length([])"
```

#### Container Appsの状態確認

```bash
# 全Container Appsの状態
az containerapp list \
  --resource-group dify-dev-rg \
  --query "[].{Name:name, Status:properties.runningStatus}" \
  --output table

# 特定のContainer Appの詳細
az containerapp show \
  --name dify-dev-web \
  --resource-group dify-dev-rg \
  --query "{Name:name, FQDN:properties.configuration.ingress.fqdn, Replicas:properties.template.scale}"
```

期待される状態: `Running`

#### データベース接続の確認

```bash
# PostgreSQL接続テスト（VNet内から）
POSTGRES_FQDN=$(az postgres flexible-server show \
  --resource-group dify-dev-rg \
  --name $(az postgres flexible-server list --resource-group dify-dev-rg --query "[0].name" -o tsv) \
  --query fullyQualifiedDomainName -o tsv)

echo "PostgreSQL FQDN: $POSTGRES_FQDN"

# Private Endpointが正しく設定されているか確認
az network private-endpoint list \
  --resource-group dify-dev-rg \
  --query "[].{Name:name, ProvisioningState:provisioningState}" \
  --output table
```

#### Application Gatewayのヘルスチェック

```bash
# バックエンドヘルスステータス
az network application-gateway show-backend-health \
  --resource-group dify-dev-rg \
  --name dify-dev-appgateway \
  --query "backendAddressPools[].backendHttpSettingsCollection[].servers[].health" \
  --output table
```

期待される状態: `Healthy`

### 2. アプリケーションの検証

#### ヘルスチェックエンドポイント

```bash
# Application Gateway経由
curl http://$APP_FQDN/api/health

# 期待されるレスポンス
# {"status": "ok"}
```

#### Webインターフェースの確認

ブラウザで以下を確認：
1. `http://$APP_FQDN` → Difyホームページが表示される
2. ログインページが正常に表示される
3. 管理コンソール（`/console`）にアクセスできる

### 3. モニタリングの検証

#### Log Analytics

```bash
# Container Appsのログをクエリ
LAW_ID=$(az monitor log-analytics workspace show \
  --resource-group dify-dev-rg \
  --workspace-name $(az monitor log-analytics workspace list --resource-group dify-dev-rg --query "[0].name" -o tsv) \
  --query customerId -o tsv)

# 過去1時間のログ
az monitor log-analytics query \
  --workspace $LAW_ID \
  --analytics-query "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1h) | take 10" \
  --output table
```

#### Application Insights

Azure Portalで以下を確認：
1. Application Insights → ライブメトリック
2. リクエスト数、レスポンスタイム
3. エラー率

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. デプロイエラー

**問題**: `deployment failed with error: ...`

**解決方法**:

```bash
# エラーの詳細を確認
az deployment group show \
  --name $DEPLOYMENT_NAME \
  --resource-group dify-dev-rg \
  --query properties.error

# アクティビティログを確認
az monitor activity-log list \
  --resource-group dify-dev-rg \
  --offset 1h \
  --query "[?level=='Error']" \
  --output table
```

よくあるエラー：
- **リソースプロバイダー未登録**: 前提条件セクションを参照
- **クォータ不足**: サポートリクエストでクォータ増加を依頼
- **名前の重複**: パラメータファイルで`uniqueString()`が使用されているため、通常は発生しない

#### 2. Container Apps起動失敗

**問題**: Container Appsが`Running`状態にならない

**解決方法**:

```bash
# ログを確認
az containerapp logs show \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --follow

# リビジョンの状態確認
az containerapp revision list \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --output table
```

よくある原因：
- 環境変数の設定ミス
- データベース接続失敗
- イメージのプル失敗

#### 3. データベース接続エラー

**問題**: Container AppsからPostgreSQLに接続できない

**解決方法**:

```bash
# Private Endpointの状態確認
az network private-endpoint show \
  --name dify-dev-postgres-pe \
  --resource-group dify-dev-rg \
  --query "{ProvisioningState:provisioningState, ConnectionState:privateLinkServiceConnections[0].privateLinkServiceConnectionState.status}"

# DNS解決の確認（Container Apps内から）
az containerapp exec \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --command "nslookup <postgres-fqdn>"
```

チェックポイント：
- Private Endpointが`Approved`状態
- Private DNS Zoneが正しくリンクされている
- NSGルールが正しい

#### 4. Application Gatewayヘルスプローブ失敗

**問題**: バックエンドが`Unhealthy`

**解決方法**:

```bash
# ヘルスプローブの詳細
az network application-gateway show-backend-health \
  --resource-group dify-dev-rg \
  --name dify-dev-appgateway

# Container Appsのingressエンドポイント確認
az containerapp show \
  --name dify-dev-web \
  --resource-group dify-dev-rg \
  --query "properties.configuration.ingress.fqdn"
```

チェックポイント：
- Container Appsが起動している
- ヘルスプローブのパスが正しい（`/api/health`）
- タイムアウト設定が適切

#### 5. SSL証明書エラー

**問題**: HTTPS接続でエラー

**解決方法**:

```bash
# Key Vault証明書の確認
az keyvault certificate show \
  --vault-name $KEYVAULT_NAME \
  --name dify-ssl-cert \
  --query "{Status:attributes.enabled, Expires:attributes.expires}"

# Application Gatewayの証明書確認
az network application-gateway ssl-cert show \
  --resource-group dify-prod-rg \
  --gateway-name dify-prod-appgateway \
  --name appGatewaySslCert
```

チェックポイント：
- 証明書が期限切れでない
- Managed IdentityがKey Vaultへのアクセス権を持っている
- 証明書にプライベートキーが含まれている（PFX形式）

#### 6. コスト超過

**問題**: 予想以上のコストが発生

**解決方法**:

```bash
# 現在のコストを確認
az consumption usage list \
  --start-date $(date -d "30 days ago" +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?contains(instanceId, 'dify')]" \
  --output table

# Container Appsのレプリカ数を確認
az containerapp show \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --query "properties.template.scale.{Min:minReplicas, Max:maxReplicas, Current:currentReplicas}"
```

コスト削減策：
- 開発環境で時間ベーススケーリングを有効化
- Application Gatewayのインスタンス数を調整
- 未使用時はリソースを停止

---

## 参考資料

### ドキュメント
- [アーキテクチャ概要](./architecture-overview.md)
- [ネットワークアーキテクチャ](./network-architecture.md)
- [コスト見積もり](./cost-estimation.md)

### 外部リンク
- [Dify公式ドキュメント](https://docs.dify.ai/)
- [Azure Bicepドキュメント](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Container Appsドキュメント](https://learn.microsoft.com/azure/container-apps/)
- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/architecture/framework/)

### サポート

問題が解決しない場合：
1. [Azure Bicep GitHub Issues](https://github.com/Azure/bicep/issues)
2. [Dify GitHub Issues](https://github.com/langgenius/dify/issues)
3. Azureサポートチケットを作成

---

**最終更新**: 2025年1月
