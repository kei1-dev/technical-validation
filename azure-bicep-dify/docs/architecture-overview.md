# Dify on Azure - システムアーキテクチャ全体図

## 概要

このドキュメントは、Dify（オープンソースLLMアプリケーション開発プラットフォーム）をAzure上に展開するための全体アーキテクチャを示します。

## アーキテクチャ全体図

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Internet / Users                                │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTPS/443
                                   │
                     ┌─────────────▼─────────────┐
                     │  Public IP Address        │
                     │  (Standard SKU, Static)   │
                     └─────────────┬─────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                        Azure Resource Group                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │             Azure Virtual Network (VNet)                              │  │
│  │                   Address Space: 10.0.0.0/16                          │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────┐    │  │
│  │  │  Application Gateway Subnet (10.0.0.0/24)                    │    │  │
│  │  │  ┌────────────────────────────────────────────────────────┐  │    │  │
│  │  │  │  Azure Application Gateway (WAF_v2)                    │  │    │  │
│  │  │  │                                                         │  │    │  │
│  │  │  │  - WAF Policy (OWASP 3.2)                              │  │    │  │
│  │  │  │  - SSL/TLS Termination                                 │  │    │  │
│  │  │  │  - SSL Cert from Key Vault (Managed Identity)          │  │    │  │
│  │  │  │  - Backend Pool: Container Apps Ingress (Internal)     │  │    │  │
│  │  │  │                                                         │  │    │  │
│  │  │  │  10.0.0.x                                               │  │    │  │
│  │  │  └────────────────────┬────────────────────────────────────┘  │    │  │
│  │  └───────────────────────┼───────────────────────────────────────┘    │  │
│  │                          │ HTTP/HTTPS (VNet Internal)                 │  │
│  │                          │                                             │  │
│  │  ┌───────────────────────▼───────────────────────────────────────┐    │  │
│  │  │  Container Apps Subnet (10.0.1.0/24)                          │    │  │
│  │  │  ┌────────────────────────────────────────────────────────┐  │    │  │
│  │  │  │  Azure Container Apps Environment                      │  │    │  │
│  │  │  │                                                         │  │    │  │
│  │  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │    │  │
│  │  │  │  │   Dify Web   │  │   Dify API   │  │ Dify Worker  │ │  │    │  │
│  │  │  │  │  (Frontend)  │  │   (Backend)  │  │  (Celery)    │ │  │    │  │
│  │  │  │  │              │  │              │  │              │ │  │    │  │
│  │  │  │  │  Port: 3000  │  │  Port: 5001  │  │  Background  │ │  │    │  │
│  │  │  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │  │    │  │
│  │  │  │         │                  │                  │         │  │    │  │
│  │  │  │         └──────────────────┼──────────────────┘         │  │    │  │
│  │  │  │                            │                            │  │    │  │
│  │  │  │   Ingress Controller (Internal - VNet Only)            │  │    │  │
│  │  │  │                            │                            │  │    │  │
│  │  │  └────────────────────────────┼────────────────────────────┘  │    │  │
│  │  └───────────────────────────────┼───────────────────────────────┘    │  │
│  │                                  │                                     │  │
│  │  ┌───────────────────────────────┼──────────────────────────────────┐ │ │
│  │  │  Private Endpoint Subnet (10.0.2.0/24)                           │ │ │
│  │  │                               │                                  │ │ │
│  │  │  ┌─────────────┐  ┌──────────▼──────┐  ┌─────────────┐         │ │ │
│  │  │  │   PE for    │  │   PE for Redis  │  │  PE for     │         │ │ │
│  │  │  │  PostgreSQL │  │                 │  │  Blob Store │         │ │ │
│  │  │  └──────┬──────┘  └──────┬──────────┘  └──────┬──────┘         │ │ │
│  │  └─────────┼─────────────────┼─────────────────────┼────────────────┘ │ │
│  └────────────┼─────────────────┼─────────────────────┼──────────────────┘ │
│               │                 │                     │                    │
│  ┌────────────▼─────────────────▼─────────────────────▼──────────────────┐ │
│  │                        Private DNS Zones                               │ │
│  │  - privatelink.postgres.database.azure.com                             │ │
│  │  - privatelink.redis.cache.windows.net                                 │ │
│  │  - privatelink.blob.core.windows.net                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────┐        ┌──────────────────────────┐            │
│  │  Azure Database for     │        │  Azure Cache for Redis   │            │
│  │  PostgreSQL Flexible    │        │                          │            │
│  │  Server                 │        │  - Session Store         │            │
│  │                         │        │  - Cache Layer           │            │
│  │  - Database: dify       │        │  - Message Queue         │            │
│  │  - Private Access Only  │        │  - Private Access Only   │            │
│  └─────────────────────────┘        └──────────────────────────┘            │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Azure Blob Storage Account                                           │  │
│  │                                                                        │  │
│  │  Containers:                                                          │  │
│  │  - dify-app-storage    (Application files)                           │  │
│  │  - dify-dataset        (Datasets, documents)                         │  │
│  │  - dify-tools          (Tool assets)                                 │  │
│  │  - Private Access Only (via Private Endpoint)                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Azure Key Vault                                                      │  │
│  │                                                                        │  │
│  │  Secrets:                                                             │  │
│  │  - PostgreSQL connection string                                      │  │
│  │  - Redis connection string                                           │  │
│  │  - Storage account keys                                              │  │
│  │  - Dify secret key                                                   │  │
│  │  - LLM API keys (OpenAI, Azure OpenAI, etc.)                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Monitoring & Logging                                                 │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────┐  ┌──────────────────────────────────┐  │  │
│  │  │  Log Analytics Workspace │  │  Application Insights            │  │  │
│  │  │                          │  │                                  │  │  │
│  │  │  - Container logs        │  │  - Performance monitoring        │  │  │
│  │  │  - Activity logs         │  │  - Request tracing              │  │  │
│  │  │  - Diagnostic logs       │  │  - Dependency tracking          │  │  │
│  │  └──────────────────────────┘  │  - Custom metrics               │  │  │
│  │                                 └──────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Azure Container Registry (Optional)                                  │  │
│  │  - Store custom Dify container images                                │  │
│  │  - Private registry for security                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## リソースグループ配下の全リソース一覧

### 1. コンピューティング層

| リソース種別 | リソース名 | 用途 | SKU/規模 |
|------------|----------|------|---------|
| Container Apps Environment | `dify-containerenv` | コンテナアプリの実行環境 | Consumption または Dedicated |
| Container App | `dify-web` | Dify Webフロントエンド | CPU: 0.5-1.0, Memory: 1-2Gi |
| Container App | `dify-api` | Dify APIバックエンド | CPU: 1.0-2.0, Memory: 2-4Gi |
| Container App | `dify-worker` | バックグラウンドジョブ処理 | CPU: 0.5-1.0, Memory: 1-2Gi |

### 2. データベース層

| リソース種別 | リソース名 | 用途 | SKU/規模 |
|------------|----------|------|---------|
| Azure Database for PostgreSQL Flexible Server | `dify-postgres` | メインデータベース | Burstable B1ms / GP_Standard_D2s_v3 |
| PostgreSQL Database | `dify` | アプリケーションDB | - |
| Azure Cache for Redis | `dify-redis` | キャッシュ・セッション・メッセージキュー | Basic C1 / Standard C2 |

### 3. ストレージ層

| リソース種別 | リソース名 | 用途 | SKU/規模 |
|------------|----------|------|---------|
| Storage Account | `difystorage{unique}` | ファイル・ドキュメント保存 | Standard LRS / ZRS |
| Blob Container | `dify-app-storage` | アプリケーションファイル | - |
| Blob Container | `dify-dataset` | データセット・ドキュメント | - |
| Blob Container | `dify-tools` | ツールアセット | - |

### 4. ネットワーク層

| リソース種別 | リソース名 | 用途 | 規模 |
|------------|----------|------|------|
| Virtual Network | `dify-vnet` | 仮想ネットワーク | 10.0.0.0/16 |
| Subnet | `appgateway-subnet` | Application Gateway用 | 10.0.0.0/24 |
| Subnet | `containerapps-subnet` | Container Apps用 | 10.0.1.0/24 |
| Subnet | `privateendpoint-subnet` | Private Endpoint用 | 10.0.2.0/24 |
| Application Gateway | `dify-appgateway` | ロードバランサー、SSL終端 | Standard_v2 (開発) / WAF_v2 (本番) |
| Public IP Address | `dify-appgateway-pip` | Application Gateway用パブリックIP | Standard, Static |
| WAF Policy | `dify-waf-policy` | Web Application Firewallポリシー（本番のみ） | OWASP 3.2 |
| Network Security Group | `dify-appgateway-nsg` | Application Gateway用NSG | - |
| Network Security Group | `dify-containerapps-nsg` | Container Apps用NSG | - |
| Network Security Group | `dify-privateendpoint-nsg` | Private Endpoint用NSG | - |
| Private Endpoint | `dify-postgres-pe` | PostgreSQL接続 | - |
| Private Endpoint | `dify-redis-pe` | Redis接続 | - |
| Private Endpoint | `dify-storage-pe` | Blob Storage接続 | - |
| Private Endpoint | `dify-keyvault-pe` | Key Vault接続（証明書取得用） | - |
| Private DNS Zone | `privatelink.postgres.database.azure.com` | PostgreSQL名前解決 | - |
| Private DNS Zone | `privatelink.redis.cache.windows.net` | Redis名前解決 | - |
| Private DNS Zone | `privatelink.blob.core.windows.net` | Blob Storage名前解決 | - |
| Private DNS Zone | `privatelink.vaultcore.azure.net` | Key Vault名前解決 | - |

### 5. セキュリティ層

| リソース種別 | リソース名 | 用途 |
|------------|----------|------|
| Key Vault | `dify-keyvault-{unique}` | シークレット・SSL証明書管理 |
| Managed Identity | `dify-appgateway-identity` | Application Gateway用マネージドID |
| Managed Identity | `dify-containerapps-identity` | Container Apps用マネージドID |

### 6. 監視・ログ層

| リソース種別 | リソース名 | 用途 |
|------------|----------|------|
| Log Analytics Workspace | `dify-logs` | ログ集約・分析 |
| Application Insights | `dify-insights` | アプリケーション監視 |

### 7. オプション

| リソース種別 | リソース名 | 用途 |
|------------|----------|------|
| Container Registry | `difyacr{unique}` | カスタムコンテナイメージ管理 |

## コンポーネント説明

### Application Gateway (Standard_v2 / WAF_v2)

- **役割**: SSL/TLS終端、ロードバランサー、インテリジェントルーティング
- **SKU**:
  - **開発環境**: Standard_v2（オートスケール対応、コスト最適化）
  - **本番環境**: WAF_v2（Web Application Firewall機能付き）
- **主要機能**:
  - **SSL/TLS終端**: HTTPS接続の暗号化/復号化
    - 証明書はKey Vaultから取得（Managed Identity経由）
    - TLS 1.2以上を強制
  - **パスベースルーティング**: URLパスに応じた効率的なトラフィック振り分け
    - `/` → Dify Web（Container Apps）
    - `/api/*` → Dify API（Container Apps、直接ルーティング）
    - `/console/*` → Dify Web（Container Apps）
  - **ヘルスプローブ**: バックエンドの正常性監視
  - **WAF保護**（本番環境のみ）: OWASP Core Rule Set 3.2による攻撃防御
    - SQLインジェクション、XSS、RCE等の脅威をブロック
    - カスタムルール設定可能
- **パブリックIP**: Standard SKU、Static割り当て
- **バックエンドプール**:
  - `dify-web-pool`: Dify Web Container Appを指定
  - `dify-api-pool`: Dify API Container Appを指定
- **監視**: Application GatewayアクセスログをLog Analyticsへ送信（本番環境はWAFログも含む）

#### ルーティング詳細

| パス | バックエンドプール | ターゲット | 用途 |
|-----|----------------|-----------|------|
| `/` | dify-web-pool | Dify Web (10.0.1.x:3000) | Webインターフェース |
| `/console/*` | dify-web-pool | Dify Web (10.0.1.x:3000) | 管理コンソール |
| `/api/*` | dify-api-pool | Dify API (10.0.1.y:5001) | RESTful API |
| `/v1/*` | dify-api-pool | Dify API (10.0.1.y:5001) | API v1エンドポイント |

**メリット**:
- API呼び出しのレイテンシー削減（直接ルーティング）
- Container Apps Ingress経由と比較して1ホップ削減
- バックエンドプールの独立したヘルスチェック

### Dify Web (フロントエンド)

- **役割**: ユーザー向けWebインターフェース
- **コンテナイメージ**: `langgenius/dify-web:latest`
- **公開ポート**: 3000
- **依存関係**: Dify API
- **環境変数**:
  - `CONSOLE_API_URL`: APIサーバーのURL
  - `APP_API_URL`: アプリケーションAPIのURL

### Dify API (バックエンド)

- **役割**: RESTful APIサーバー、ビジネスロジック処理
- **コンテナイメージ**: `langgenius/dify-api:latest`
- **公開ポート**: 5001
- **依存関係**: PostgreSQL, Redis, Blob Storage
- **主要環境変数**:
  - `DB_*`: PostgreSQL接続情報
  - `REDIS_*`: Redis接続情報
  - `STORAGE_TYPE`: `azure-blob`
  - `AZURE_BLOB_*`: Blob Storage接続情報
  - `SECRET_KEY`: アプリケーション暗号化キー

### Dify Worker (バックグラウンド処理)

- **役割**: 非同期ジョブ処理（Celery Worker）
- **コンテナイメージ**: `langgenius/dify-api:latest` (異なるエントリーポイント)
- **依存関係**: PostgreSQL, Redis, Blob Storage
- **処理内容**:
  - ドキュメント解析
  - ベクトル化処理
  - 長時間実行タスク

### Container Appsの自動スケーリング（開発環境）

**コスト最適化のための自動スケールダウン:**

開発環境では、Container Appsを最小レプリカ0に設定することで、使用しない時間帯のコストを削減できます。

#### 動作の仕組み

```
[アイドル状態]
Application Gateway（常時稼働） → Container Apps（停止中、コスト0）

[リクエスト受信]
1. Application Gatewayがリクエストを受け付け
2. Container Appsが自動起動（コールドスタート: 5-30秒）
3. リクエストを処理

[稼働中]
Application Gateway → Container Apps（稼働中）

[アイドル検出]
一定時間アクセスがない → Container Appsが自動停止
```

#### 自動スケールダウンの設定

| 項目 | 開発環境 | 本番環境 |
|-----|---------|---------|
| **最小レプリカ数** | 0（自動停止可能） | 2-3（常時稼働） |
| **最大レプリカ数** | 3-5 | 10-30 |
| **スケールアウト条件** | HTTPリクエスト受信時 | HTTPリクエスト数、CPU使用率 |
| **スケールイン条件** | 5分間アクセスなし | 負荷低下時（最小レプリカまで） |
| **コールドスタート時間** | 5-30秒 | N/A（常時稼働） |

#### コールドスタートの特性

**コールドスタート時間:**
- **初回起動**: 20-30秒（イメージpull + 起動）
- **2回目以降**: 5-10秒（キャッシュ済みイメージ使用）

**ユーザー体験:**
- アイドル後の初回アクセス: 5-30秒の待ち時間
- 稼働中のアクセス: 通常の応答時間

**推奨用途:**
- ✅ 開発環境（夜間・週末は停止してコスト削減）
- ✅ 検証環境（使用時のみ起動）
- ❌ 本番環境（常時即座に応答が必要）

#### コスト削減効果

- **従来**: 12時間/日稼働 = ¥12,140/月
- **最適化**: 平均7時間/日稼働（実アクセス時のみ）= ¥7,082/月
- **削減額**: 約¥5,000/月（-42%）

#### 時間ベーススケーリング（Azure Automation）**さらに最適化**

開発環境でさらなるコスト削減と運用効率化のため、Azure Automationを使用した時間ベースのスケーリングを実装できます。

**スケジュール設定:**
- **日中（9:00-18:00 JST）**: 最小レプリカ = 1
  - 業務時間中は常時稼働（コールドスタートなし）
  - 即座にリクエストに応答可能
- **夜間（18:00-9:00 JST）**: 最小レプリカ = 0
  - 自動停止でコスト削減
  - アクセスがあれば5-30秒で自動起動

**実装方法:**

1. **Azure Automationアカウント**を作成
2. **Runbook**（PowerShellまたはPython）を作成し、以下の処理を実装:
   ```powershell
   # 最小レプリカを1に設定（9:00実行）
   az containerapp update --name dify-web --resource-group <rg> --min-replicas 1
   az containerapp update --name dify-api --resource-group <rg> --min-replicas 1
   az containerapp update --name dify-worker --resource-group <rg> --min-replicas 1

   # 最小レプリカを0に設定（18:00実行）
   az containerapp update --name dify-web --resource-group <rg> --min-replicas 0
   az containerapp update --name dify-api --resource-group <rg> --min-replicas 0
   az containerapp update --name dify-worker --resource-group <rg> --min-replicas 0
   ```
3. **スケジュール設定**:
   - Runbook 1: 毎日 9:00 JST実行（最小レプリカ→1）
   - Runbook 2: 毎日 18:00 JST実行（最小レプリカ→0）
4. **Managed Identity**: Runbookに適切な権限を付与（Container Appsへの書き込み権限）

**追加コスト（Azure Automation）:**
- Automationアカウント: 最初の500分/月は無料
- Runbook実行時間: ~1分/日 × 2回 × 30日 = 60分/月（無料枠内）
- **追加コスト**: ¥0

**コスト削減効果（時間ベース）:**
- **平日9時間稼働**: 2 vCPU × 9時間/日 × 22営業日 = 約¥5,500-6,000/月
- **削減額**: 約¥6,000/月（最適化構成比で-85%、標準構成比で-50%）

**メリット:**
- ✅ 日中はコールドスタートなし（即座に応答）
- ✅ 夜間・週末は完全停止でコスト0
- ✅ 自動化により運用負荷なし
- ✅ 最大のコスト削減効果

### Azure Database for PostgreSQL Flexible Server

- **役割**: メインデータベース
- **データ**: ユーザー、アプリケーション設定、会話履歴など
- **接続方式**: Private Endpoint経由のみ（パブリックアクセス無効）
- **バックアップ**: 自動バックアップ有効（保持期間7-35日）

### Azure Cache for Redis

- **役割**:
  - セッションストア
  - キャッシュレイヤー
  - Celeryメッセージブローカー
- **接続方式**: Private Endpoint経由のみ
- **永続化**: RDB/AOF設定可能

### Azure Blob Storage

- **役割**: ファイルストレージ
- **データ**: アップロードファイル、データセット、生成されたアセット
- **接続方式**: Private Endpoint経由のみ
- **冗長性**: LRS（開発）/ ZRS（本番）

### Azure Key Vault

- **役割**: シークレット・証明書管理
- **管理対象**:
  - **SSL/TLS証明書**: Application Gateway用HTTPS証明書
  - データベース接続文字列
  - APIキー（OpenAI、Azure OpenAI等）
  - ストレージアカウントキー
  - アプリケーション暗号化キー
- **アクセス制御**: Managed Identityによるアクセス
  - Application Gateway Identity: 証明書の読み取り
  - Container Apps Identity: シークレットの読み取り
- **証明書更新**:
  - 手動アップロード、または
  - Let's Encryptとの連携（Azure Automationなど）

### Managed Identity

**Application Gateway Identity:**
- **役割**: Application GatewayがKey Vaultから証明書を取得
- **アクセス許可**:
  - Key Vault: Certificates Get, Secrets Get

**Container Apps Identity:**
- **役割**: Container Appsがシークレットレスで他Azureサービスにアクセス
- **アクセス許可**:
  - Key Vault: Secrets Get/List
  - Storage Account: Blob Data Contributor
  - Container Registry: Pull (オプション)

## データフロー

### 1. ユーザーリクエスト

#### Web UIアクセス (/, /console/*)

```
User → HTTPS/443 → Application Gateway (Public IP, SSL終端)
                          │ パス: / または /console/*
                          ↓ HTTP/HTTPS (VNet Internal)
                          ↓ dify-web-pool
                   Dify Web (10.0.1.x:3000)
                          │
                          └→ Dify API (10.0.1.y:5001) へのAPI呼び出し
```

#### API直接アクセス (/api/*, /v1/*)

```
User → HTTPS/443 → Application Gateway (Public IP, SSL終端)
                          │ パス: /api/* または /v1/*
                          ↓ HTTP/HTTPS (VNet Internal)
                          ↓ dify-api-pool (直接ルーティング)
                   Dify API (10.0.1.y:5001)
                          │
                          ├→ PostgreSQL (10.0.2.4:5432) データ読み書き
                          ├→ Redis (10.0.2.5:6380) キャッシュ/セッション
                          └→ Blob Storage (10.0.2.6:443) ファイル操作
```

**ルーティングの利点**:
- APIクライアントはApplication Gateway経由で直接APIにアクセス可能
- レイテンシー削減（Container Apps Ingress経由より1ホップ少ない）
- バックエンドの独立したスケーリングとモニタリング

### 2. バックグラウンドジョブ

```
Dify API → Redis Queue → Dify Worker → PostgreSQL (結果保存)
                              │
                              └→ Blob Storage (処理済みファイル)
```

### 3. 監視・ログ

```
All Resources → Diagnostic Settings → Log Analytics Workspace
Container Apps → Application Insights → Performance Metrics
```

## セキュリティ対策

### ネットワークセキュリティ

- **多層防御**: Application Gateway → Container Apps (Internal) → Private Endpoints
- **WAF保護**（本番環境のみ）: Application Gateway WAF_v2によるOWASP攻撃防御
  - SQLインジェクション、XSS、RCE等をブロック
  - 異常トラフィックの検出とブロック
  - カスタムルールによる追加保護
- **開発環境**: Application Gateway Standard_v2（コスト最適化、WAFなし）
- **VNet統合**: すべてのリソースがVNet内に配置
- **Private Endpoint**: PaaSサービスへのプライベート接続
- **NSG**: サブネット間の通信制御
- **Container Apps Ingress**: Internal（VNet内部のみアクセス可能）
- **パブリックアクセス無効**: データベース、Redis、Storageはインターネットから隔離

### 認証・認可

- **Managed Identity**: パスワードレス認証
- **Key Vault**: シークレット一元管理
- **RBAC**: Azure役割ベースのアクセス制御

### データ保護

- **転送時の暗号化**:
  - インターネット → Application Gateway: TLS 1.2以上（強制）
  - Application Gateway → Container Apps: HTTP/HTTPS（VNet内部）
  - Container Apps → PaaSサービス: SSL/TLS接続
- **保存時の暗号化**: すべてのストレージで有効
- **バックアップ**: PostgreSQLの自動バックアップ
- **証明書管理**: Key Vault統合、自動更新対応

## スケーリング戦略

### Application Gateway

- **オートスケール**: リクエスト数、スループットベース
- **最小キャパシティ**: 1-2ユニット（コスト最適化）
- **最大キャパシティ**: 10ユニット（高負荷対応）
- **ゾーン冗長**: 可用性ゾーン対応リージョンで有効化推奨

### Container Apps

- **水平スケーリング**: HTTPリクエスト数、CPU使用率ベース
- **最小レプリカ数**:
  - **Dev: 0（推奨）** - 使用しない時間帯は自動停止、コスト0
    - コールドスタート: 5-30秒
    - 月間コスト削減: 約¥5,000（実稼働時間に応じて）
  - **Prod: 2-3** - 常時稼働、即座に応答
- **最大レプリカ数**:
  - Dev: 3-5
  - Prod: 10-30（負荷に応じて）
- **スケールアウトトリガー**:
  - HTTPリクエスト受信（最小レプリカ0の場合）
  - 同時リクエスト数 > 10/レプリカ
  - CPU使用率 > 70%
- **スケールインポリシー**:
  - Dev: 5分間アクセスなし → レプリカ0へ
  - Prod: 負荷低下時、最小レプリカ数まで縮小

### データベース

- **PostgreSQL**: Flexible Serverの垂直スケーリング（手動/スケジュール）
- **Redis**: Standard/Premium tierへのアップグレード（ダウンタイムあり）

### ストレージ

- **Blob Storage**: 自動スケーリング（無制限）

## 高可用性

- **Application Gateway**: ゾーン冗長構成（複数の可用性ゾーンに配置）
- **Container Apps**: 複数レプリカ配置（Zone Redundancy対応リージョンで推奨）
- **PostgreSQL**: Zone-Redundant HA構成（オプション）
- **Redis**: Standard/Premium tier（レプリケーション有効）
- **Storage**: ZRS/GRS冗長性（本番環境推奨）

## コスト最適化

### 開発環境

- Application Gateway: **Standard_v2**、最小キャパシティ1、最大2（必要時のみスケール、WAFなし）
- Container Apps: Consumption plan、**最小レプリカ0**（自動停止でコスト削減）
  - ✅ 使用しない時間帯は自動停止（コスト0）
  - ✅ リクエスト受信時に5-30秒で自動起動
  - ✅ 月間約¥5,000削減（実稼働時間による）
- PostgreSQL: Burstable tier (B1ms)
- Redis: Basic C0/C1
- Storage: Standard LRS

### 本番環境

- Application Gateway: **WAF_v2**、最小キャパシティ2、最大10、ゾーン冗長有効
- Container Apps: Dedicated/Consumption、最小レプリカ2+
- PostgreSQL: General Purpose (GP_Standard_D2s_v3+)、HA有効
- Redis: Standard C2+、永続化有効
- Storage: Standard ZRS/GRS

## 次のステップ

1. [ネットワーク構成図](./network-architecture.md)を確認
2. Bicepモジュールの実装開始
3. パラメータファイルの作成（dev/prod環境）
4. デプロイスクリプトの作成
