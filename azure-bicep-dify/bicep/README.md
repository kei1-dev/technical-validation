# Dify on Azure - Bicep Templates

このディレクトリには、Dify（オープンソースLLMアプリケーション開発プラットフォーム）をAzureにデプロイするためのBicep IaC（Infrastructure as Code）テンプレートが含まれています。

## 📚 ドキュメント

- **[デプロイ手順書](../docs/deployment-guide.md)** - 詳細なデプロイ手順（必読）
- **[アーキテクチャ概要](../docs/architecture-overview.md)** - システムアーキテクチャの詳細
- **[ネットワークアーキテクチャ](../docs/network-architecture.md)** - ネットワーク設計の詳細
- **[コスト見積もり](../docs/cost-estimation.md)** - 環境別コスト概算

## 🚀 クイックスタート

### 前提条件

```bash
# 前提条件の確認
bash ../scripts/validate-prerequisites.sh
```

### デプロイ

```bash
# 1. パラメータファイルを編集（パスワードとObject IDを設定）
nano parameters/dev.bicepparam

# 2. デプロイを実行
bash ../scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --location japaneast
```

詳細な手順は **[デプロイ手順書](../docs/deployment-guide.md)** を参照してください。

## 📦 デプロイされるリソース

本インフラストラクチャには以下のAzureリソースが含まれます：

### コアサービス
- **Azure Container Apps**: Dify web、API、workerコンテナをホスト
- **Azure Database for PostgreSQL Flexible Server**: メインデータベース
- **Azure Cache for Redis**: セッションストア、キャッシュ、メッセージキュー
- **Azure Blob Storage**: ファイル・ドキュメントストレージ

### ネットワーク＆セキュリティ
- **Virtual Network (VNet)**: 3つのサブネットを持つ分離ネットワーク
- **Application Gateway**: ロードバランサー（SSL終端、WAF付き）
- **Private Endpoints**: PaaSサービスへのセキュアなプライベート接続
- **Network Security Groups (NSGs)**: サブネットレベルのセキュリティ
- **Azure Key Vault**: シークレット・証明書管理
- **Managed Identities**: パスワードレス認証

### 監視＆運用
- **Log Analytics Workspace**: 集中ログ管理
- **Application Insights**: アプリケーションパフォーマンス監視
- **Azure Automation** (開発環境のみ): 時間ベース自動スケーリング

## 📁 プロジェクト構造

```
bicep/
├── main.bicep                      # メインオーケストレーションテンプレート
├── modules/                        # モジュール化されたBicepテンプレート（12個）
│   ├── monitoring.bicep           # Log Analytics & App Insights
│   ├── network.bicep              # VNet + NSG + Subnets
│   ├── keyvault.bicep             # Key Vault & Managed Identities
│   ├── postgresql.bicep           # PostgreSQL Flexible Server
│   ├── redis.bicep                # Redis Cache
│   ├── storage.bicep              # Blob Storage
│   ├── privateDnsZone.bicep       # Private DNS Zone（再利用可能）
│   ├── privateEndpoint.bicep      # Private Endpoint（再利用可能）
│   ├── containerAppsEnv.bicep     # Container Apps Environment
│   ├── containerApp.bicep         # Container App（再利用可能）
│   ├── applicationGateway.bicep   # App Gateway + WAF + Public IP
│   └── automation.bicep           # Time-based Scaling
├── parameters/
│   ├── dev.bicepparam             # 開発環境パラメータ
│   └── prod.bicepparam            # 本番環境パラメータ
└── README.md                       # このファイル
```

## 🔧 モジュール設計

### 中粒度（機能単位）のモジュール構成

各モジュールは関連するAzureリソースをグループ化し、独立して再利用可能な設計になっています。

**再利用可能なコンポーネント**:
- `privateEndpoint.bicep` - 任意のPaaSサービス用
- `privateDnsZone.bicep` - 任意のPrivate DNS Zone用
- `containerApp.bicep` - 任意のContainer App用

**機能単位のモジュール**:
- 各データレイヤー（PostgreSQL、Redis、Storage）が独立したモジュール
- ネットワークレイヤーがVNet、NSG、Subnetsを統合管理
- Application Gatewayモジュールが Public IP、WAF Policyを統合管理

## ⚙️ パラメータの設定

### 必須パラメータ

デプロイ前に以下のパラメータを更新してください：

```bicep
// parameters/dev.bicepparam または parameters/prod.bicepparam

// PostgreSQL認証情報（強力なパスワードに変更）
param postgresqlAdminUsername = 'difydbadmin'
param postgresqlAdminPassword = 'CHANGE_ME_STRONG_PASSWORD!'

// Key Vault管理者のAzure AD Object ID
param keyVaultAdminObjectId = ''  // az ad signed-in-user show --query id -o tsv
```

### オプションパラメータ（本番環境）

```bicep
// SSL証明書のシークレットID（HTTPSを有効にする場合）
param sslCertificateSecretId = ''

// コンテナイメージバージョン（固定バージョン推奨）
param difyWebImage = 'langgenius/dify-web:0.6.13'
param difyApiImage = 'langgenius/dify-api:0.6.13'
```

詳細な設定方法は **[デプロイ手順書](../docs/deployment-guide.md)** を参照してください。

## 🔍 運用管理

### ログの確認

```bash
# Container Appsのログをリアルタイム表示
az containerapp logs show \
  --name dify-dev-web \
  --resource-group dify-dev-rg \
  --follow
```

### スケーリング

```bash
# スケールアップ
az containerapp update \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --min-replicas 2 \
  --max-replicas 10
```

詳細な運用手順とトラブルシューティングは **[デプロイ手順書](../docs/deployment-guide.md#トラブルシューティング)** を参照してください。

## 🗑️ リソースの削除

```bash
# 全リソースを削除
bash ../scripts/cleanup.sh --resource-group dify-dev-rg
```

**警告**: この操作は元に戻せません。Key VaultのPurge Protection有効時は90日間ソフト削除されます。

## 💰 コスト概算

| 環境 | 月額コスト | 主な特徴 |
|------|----------|---------|
| **開発** | ¥33,000 - ¥34,000 | Scale-to-zero、Burstable PostgreSQL、WAFなし |
| **本番** | ¥218,000 - ¥280,000 | HA構成、Zone冗長、WAF保護、常時稼働 |

詳細な内訳は **[コスト見積もり](../docs/cost-estimation.md)** を参照してください。

## 🔒 セキュリティ

本テンプレートには以下のセキュリティ機能が組み込まれています：

- ✅ Private Endpoints（全PaaSサービス）
- ✅ WAF保護（本番環境）
- ✅ Managed Identity認証
- ✅ NSGによるサブネットレベル保護
- ✅ Key Vault統合
- ✅ SSL/TLS暗号化

追加の推奨事項：
- シークレットの定期ローテーション（90日ごと）
- Azure Defenderの有効化
- 診断設定による監査ログ記録
- データベースのバックアップ戦略実装

## 📚 参考リンク

- [Difyドキュメント](https://docs.dify.ai/)
- [Azure Bicepドキュメント](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Container Appsドキュメント](https://learn.microsoft.com/azure/container-apps/)
- [Azure Well-Architected Framework](https://learn.microsoft.com/azure/architecture/framework/)

## 📄 ライセンス

- **Dify**: Apache License 2.0
- **Azure Bicep**: MIT License
