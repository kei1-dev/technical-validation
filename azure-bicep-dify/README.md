# Dify on Azure with Bicep

Azure Container AppsとBicepを使用してDifyをデプロイするためのInfrastructure as Codeプロジェクトです。

## 概要

このプロジェクトは、オープンソースのLLMアプリケーション開発プラットフォームである[Dify](https://github.com/langgenius/dify)を、Azure上にBicepを使ってデプロイするための環境を提供します。

### 想定アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Dify Web │  │ Dify API │  │  Worker  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐  ┌──────▼─────┐  ┌────────▼────────┐
│   PostgreSQL   │  │   Redis    │  │  Blob Storage   │
│ Flexible Server│  │   Cache    │  │                 │
└────────────────┘  └────────────┘  └─────────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Virtual Network    │
                └─────────────────────┘
```

### 使用するAzureリソース

- **Azure Container Apps**: Difyのコンテナ実行環境
  - Web UI
  - API Server
  - Worker (バックグラウンドジョブ処理)
- **Azure Database for PostgreSQL Flexible Server**: メインデータベース
- **Azure Cache for Redis**: キャッシュ層、セッション管理
- **Azure Blob Storage**: ファイル、ドキュメント保存
- **Azure Virtual Network**: ネットワーク分離
- **Azure Application Insights**: 監視・ログ分析
- **Azure Log Analytics Workspace**: ログ集約

## 前提条件

### 必須ツール

- [Visual Studio Code](https://code.visualstudio.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)（DevContainer内で使用可能）
- [Git](https://git-scm.com/)

### Azureサブスクリプション

- 有効なAzureサブスクリプション
- リソースを作成する権限（Contributor以上）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd azure-bicep-dify
```

### 2. DevContainerで開く

1. VS Codeでプロジェクトフォルダを開く
2. コマンドパレット（`Ctrl+Shift+P` / `Cmd+Shift+P`）を開く
3. `Dev Containers: Reopen in Container` を選択
4. コンテナのビルドと起動を待つ（初回は数分かかります）

### 3. Azure CLIでログイン

DevContainer内で以下を実行：

```bash
az login
az account set --subscription <your-subscription-id>
```

### 4. Bicepの確認

```bash
az bicep version
```

## デプロイ手順

このプロジェクトは3フェーズのデプロイプロセスを使用します：

1. **フェーズ1**: Azure Container Registry (ACR) のデプロイ
2. **フェーズ2**: カスタムnginxコンテナのビルドとACRへのプッシュ
3. **フェーズ3**: メインインフラストラクチャのデプロイ

### パラメータファイルの準備

デプロイ前に、環境に応じたパラメータファイルを更新してください：

**開発環境** (`bicep/main/parameters/dev.bicepparam`):
```bicep
param postgresqlAdminPassword = 'YOUR_STRONG_PASSWORD'
param keyVaultAdminObjectId = 'YOUR_AZURE_AD_OBJECT_ID'
param difySecretKey = 'YOUR_64_CHAR_HEX_STRING'
```

**本番環境** (`bicep/main/parameters/prod.bicepparam`):
```bicep
param postgresqlAdminPassword = 'YOUR_VERY_STRONG_PASSWORD'
param keyVaultAdminObjectId = 'YOUR_AZURE_AD_OBJECT_ID'
param difySecretKey = 'YOUR_64_CHAR_HEX_STRING'
param sslCertificateSecretId = 'YOUR_KEYVAULT_CERT_ID'  // HTTPS用
```

### デプロイの実行

#### 開発環境へのデプロイ

```bash
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --location japaneast
```

#### 本番環境へのデプロイ

```bash
bash scripts/deploy.sh \
  --environment prod \
  --resource-group dify-prod-rg \
  --location japaneast
```

#### What-If分析（変更内容の確認）

```bash
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --what-if
```

### デプロイフローの詳細

#### フェーズ1: ACRデプロイ
- `bicep/acr-only/main.bicep` を使用してACRをデプロイ
- ACR名とログインサーバーURLを取得

#### フェーズ2: nginxコンテナビルド
- `docker/nginx/` からカスタムnginxイメージをビルド
- ACRにログインしてイメージをプッシュ
- イメージURL: `<acr-login-server>/dify-nginx:latest`

#### フェーズ3: メインインフラデプロイ
- `bicep/main/main.bicep` を使用してすべてのリソースをデプロイ
- ACR情報とnginxイメージURLをパラメータとして渡す
- 以下のリソースがデプロイされます：
  - Virtual Network
  - PostgreSQL Flexible Server
  - Redis Cache
  - Blob Storage
  - Container Apps Environment
  - Container Apps (Web, API, Worker, nginx)
  - Application Gateway
  - Key Vault
  - Log Analytics & Application Insights

### デプロイ時間

- フェーズ1 (ACR): 約2-3分
- フェーズ2 (nginxビルド): 約3-5分
- フェーズ3 (メインインフラ): 約20-30分
- **合計**: 約25-38分

### トラブルシューティング

#### フェーズ2で失敗した場合

nginxコンテナのビルド/プッシュのみを再実行：

```bash
bash scripts/build-and-push-nginx.sh \
  --resource-group dify-dev-rg \
  --acr-name <acr-name>
```

#### フェーズ3で失敗した場合

ACRとnginxイメージは既に利用可能なので、パラメータを修正して再デプロイ可能です。

## プロジェクト構造

```
azure-bicep-dify/
├── .devcontainer/          # DevContainer設定
│   ├── devcontainer.json
│   ├── Dockerfile
│   └── scripts/
│       └── post-create.sh
├── bicep/                  # Bicepテンプレート
│   ├── acr-only/          # ACR専用デプロイ
│   │   ├── main.bicep
│   │   ├── modules/
│   │   │   └── acr.bicep
│   │   └── parameters/
│   │       ├── dev.bicepparam
│   │       └── prod.bicepparam
│   └── main/              # メインインフラデプロイ
│       ├── main.bicep
│       ├── modules/
│       │   ├── containerApp.bicep
│       │   ├── containerAppsEnv.bicep
│       │   ├── postgresql.bicep
│       │   ├── redis.bicep
│       │   ├── storage.bicep
│       │   ├── network.bicep
│       │   ├── monitoring.bicep
│       │   ├── keyvault.bicep
│       │   ├── applicationGateway.bicep
│       │   ├── nginxContainerApp.bicep
│       │   ├── privateEndpoint.bicep
│       │   ├── privateDnsZone.bicep
│       │   └── privateDnsRecord.bicep
│       └── parameters/
│           ├── dev.bicepparam
│           └── prod.bicepparam
├── scripts/                # デプロイ・管理スクリプト
│   ├── deploy.sh          # 3フェーズデプロイスクリプト
│   ├── build-and-push-nginx.sh
│   └── validate-prerequisites.sh
├── docker/                 # カスタムDockerイメージ
│   └── nginx/
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── default.conf.template
│       └── proxy_params
└── README.md
```

## 開発環境

このプロジェクトはDevContainerを使用しており、以下のツールが含まれています：

- Azure CLI
- Bicep CLI
- AWS CLI（マルチクラウド対応）
- Docker & Docker Compose
- Python 3.12 + pipenv
- Node.js (LTS)
- Claude Code / Codex CLI（AI支援開発ツール）
- VS Code拡張機能
  - Azure Account
  - Azure Resources
  - Bicep
  - Docker
  - Python

## 今後の実装予定

### フェーズ1: Infrastructure as Code
- [ ] Bicepモジュールの作成
  - [ ] ネットワーク構成
  - [ ] データベース・キャッシュ
  - [ ] ストレージ
  - [ ] Container Apps環境
  - [ ] 監視・ログ
- [ ] パラメータファイルの作成（dev/prod）
- [ ] デプロイスクリプトの作成

### フェーズ2: Dify統合
- [ ] Difyコンテナイメージのビルド設定
- [ ] 環境変数設定の整備
- [ ] シークレット管理（Azure Key Vault統合）
- [ ] CI/CDパイプライン（GitHub Actions）

### フェーズ3: ローカル開発環境
- [ ] Docker Composeでのローカル実行環境
- [ ] 開発用データベースシード
- [ ] ホットリロード設定

## 参考リンク

- [Dify公式ドキュメント](https://docs.dify.ai/)
- [Dify GitHub](https://github.com/langgenius/dify)
- [Azure Container Apps ドキュメント](https://learn.microsoft.com/azure/container-apps/)
- [Azure Bicep ドキュメント](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)

## ライセンス

このプロジェクトのライセンスについては、LICENSEファイルを参照してください。
Dify自体のライセンスについては、[Difyのリポジトリ](https://github.com/langgenius/dify)を参照してください。

## 貢献

イシューやプルリクエストを歓迎します。

---

**Note**: このプロジェクトは開発中です。実装が完了次第、ドキュメントも更新されます。
