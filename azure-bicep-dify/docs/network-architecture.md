# Dify on Azure - ネットワークアーキテクチャ

## 概要

このドキュメントは、Dify on AzureのVirtual Network構成、サブネット設計、Private Endpoint配置、セキュリティルールの詳細を示します。

## ネットワーク構成図

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Internet (HTTPS/443)                            │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                       ┌─────────────▼─────────────┐
                       │  Public IP Address        │
                       │  dify-appgateway-pip      │
                       │  (Standard SKU, Static)   │
                       └─────────────┬─────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                    Azure Virtual Network: dify-vnet                          │
│                         Address Space: 10.0.0.0/16                           │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Subnet: appgateway-subnet (10.0.0.0/24)                             │   │
│  │  - Available IPs: ~251                                               │   │
│  │  - NSG: dify-appgateway-nsg                                          │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  Azure Application Gateway (Standard_v2 / WAF_v2)          │    │   │
│  │  │  - dify-appgateway                                           │    │   │
│  │  │  - 開発: Standard_v2 / 本番: WAF_v2 (OWASP 3.2)            │    │   │
│  │  │  - SSL/TLS Termination                                      │    │   │
│  │  │  - SSL Cert from Key Vault (via Managed Identity)          │    │   │
│  │  │  - Health Probe → Container Apps                           │    │   │
│  │  │                                                              │    │   │
│  │  │  10.0.0.x                                                    │    │   │
│  │  └──────────────────────────┬───────────────────────────────────┘    │   │
│  └───────────────────────────────┼────────────────────────────────────────┘
│                                  │ HTTP/HTTPS (VNet Internal)
│                                  │
│  ┌───────────────────────────────▼────────────────────────────────────────┐
│  │  Subnet: containerapps-subnet (10.0.1.0/24)                          │   │
│  │  - Available IPs: ~251                                               │   │
│  │  - NSG: dify-containerapps-nsg                                       │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  Container Apps Environment: dify-containerenv              │    │   │
│  │  │                                                              │    │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │    │   │
│  │  │  │  dify-web   │  │  dify-api   │  │ dify-worker │        │    │   │
│  │  │  │  (Replicas) │  │  (Replicas) │  │  (Replicas) │        │    │   │
│  │  │  │             │  │             │  │             │        │    │   │
│  │  │  │ 10.0.1.x    │  │ 10.0.1.y    │  │ 10.0.1.z    │        │    │   │
│  │  │  └─────┬───────┘  └─────┬───────┘  └─────┬───────┘        │    │   │
│  │  │        │                 │                 │                │    │   │
│  │  │        └─────────────────┼─────────────────┘                │    │   │
│  │  │                          │                                  │    │   │
│  │  │   Ingress Controller (Internal - VNet Only)                │    │   │
│  │  │                          │                                  │    │   │
│  │  └──────────────────────────┼──────────────────────────────────┘    │   │
│  └───────────────────────────────┼────────────────────────────────────────┘
│                                  │
│                                  │ Private Connection
│                                  │
│  ┌───────────────────────────────▼────────────────────────────────────────┐
│  │  Subnet: privateendpoint-subnet (10.0.2.0/24)                          │
│  │  - Available IPs: ~251                                                 │
│  │  - NSG: dify-privateendpoint-nsg                                       │
│  │                                                                         │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │  │  Private         │  │  Private         │  │  Private         │    │
│  │  │  Endpoint        │  │  Endpoint        │  │  Endpoint        │    │
│  │  │  (PostgreSQL)    │  │  (Redis)         │  │  (Blob Storage)  │    │
│  │  │                  │  │                  │  │                  │    │
│  │  │  NIC: 10.0.2.4   │  │  NIC: 10.0.2.5   │  │  NIC: 10.0.2.6   │    │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘    │
│  └───────────┼──────────────────────┼──────────────────────┼──────────────┘
│              │                      │                      │
│              │ Private Link         │ Private Link         │ Private Link
│              │                      │                      │
└──────────────┼──────────────────────┼──────────────────────┼───────────────┘
               │                      │                      │
      ┌────────▼────────┐    ┌───────▼────────┐    ┌───────▼────────┐
      │  Azure Database │    │  Azure Cache   │    │  Azure Blob    │
      │  for PostgreSQL │    │  for Redis     │    │  Storage       │
      │  Flexible Server│    │                │    │                │
      │                 │    │  Private VNet  │    │  Public Access │
      │  Private VNet   │    │  Integration   │    │  Disabled      │
      │  Integration    │    │  Enabled       │    │                │
      └─────────────────┘    └────────────────┘    └────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                        Private DNS Zones                                     │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  privatelink.postgres.database.azure.com                               │ │
│  │  - A Record: dify-postgres → 10.0.2.4                                  │ │
│  │  - VNet Link: dify-vnet                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  privatelink.redis.cache.windows.net                                   │ │
│  │  - A Record: dify-redis → 10.0.2.5                                     │ │
│  │  - VNet Link: dify-vnet                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  privatelink.blob.core.windows.net                                     │ │
│  │  - A Record: difystorageXXXX → 10.0.2.6                               │ │
│  │  - VNet Link: dify-vnet                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## サブネット設計

### 1. Application Gateway Subnet (10.0.0.0/24)

| 項目 | 値 |
|-----|-----|
| **サブネット名** | `appgateway-subnet` |
| **アドレス範囲** | `10.0.0.0/24` |
| **利用可能IP数** | 251 (Azure予約5個を除く) |
| **用途** | Azure Application Gateway専用 |
| **委任** | なし |
| **NSG** | `dify-appgateway-nsg` |
| **ルートテーブル** | デフォルト |

#### 特記事項

- Application Gatewayは専用サブネットが必要（他のリソースと共有不可）
- 推奨最小サイズ: `/27` (32アドレス)、将来のスケールを考慮して `/24` を使用
- サブネットにはApplication Gateway以外のリソースを配置できない
- Public IPはサブネット外に配置されるがサブネットに関連付けられる

### 2. Container Apps Subnet (10.0.1.0/24)

| 項目 | 値 |
|-----|-----|
| **サブネット名** | `containerapps-subnet` |
| **アドレス範囲** | `10.0.1.0/24` |
| **利用可能IP数** | 251 (Azure予約5個を除く) |
| **用途** | Azure Container Apps Environment |
| **委任** | `Microsoft.App/environments` |
| **NSG** | `dify-containerapps-nsg` |
| **ルートテーブル** | デフォルト（必要に応じてカスタム） |

#### 特記事項

- Container Apps Environmentはサブネットの委任が必要
- 推奨最小サイズ: `/23` (512アドレス)、小規模環境では `/24` (256アドレス)で可
- 将来的なスケールアウトを考慮したサイジングが重要

### 3. Private Endpoint Subnet (10.0.2.0/24)

| 項目 | 値 |
|-----|-----|
| **サブネット名** | `privateendpoint-subnet` |
| **アドレス範囲** | `10.0.2.0/24` |
| **利用可能IP数** | 251 (Azure予約5個を除く) |
| **用途** | Private Endpoint配置 |
| **委任** | なし |
| **NSG** | `dify-privateendpoint-nsg` |
| **Private Endpoint Network Policy** | `Disabled` (必須) |

#### Private Endpoint一覧

| リソース | Private Endpoint名 | プライベートIP | FQDN |
|---------|-------------------|---------------|------|
| PostgreSQL | `dify-postgres-pe` | 10.0.2.4 | `dify-postgres.privatelink.postgres.database.azure.com` |
| Redis | `dify-redis-pe` | 10.0.2.5 | `dify-redis.privatelink.redis.cache.windows.net` |
| Blob Storage | `dify-storage-pe` | 10.0.2.6 | `difystorage{unique}.privatelink.blob.core.windows.net` |
| Key Vault | `dify-keyvault-pe` | 10.0.2.7 | `dify-keyvault-{unique}.privatelink.vaultcore.azure.net` |

## Network Security Groups (NSG)

### NSG: dify-appgateway-nsg

Application Gateway Subnetに適用されるセキュリティルール。

#### インバウンドルール

| 優先度 | 名前 | ソース | ソースポート | 宛先 | 宛先ポート | プロトコル | アクション |
|-------|------|--------|------------|------|----------|-----------|----------|
| 100 | AllowHttpsInbound | Internet | * | * | 443 | TCP | Allow |
| 110 | AllowGatewayManager | GatewayManager | * | * | 65200-65535 | TCP | Allow |
| 120 | AllowAzureLoadBalancer | AzureLoadBalancer | * | * | * | * | Allow |
| 65000 | DenyAllInbound | * | * | * | * | * | Deny |

**重要**: Application Gatewayには以下のポートが必須
- **65200-65535**: Azure Gatewayインフラストラクチャ通信用
- **443**: インターネットからのHTTPS受信

#### アウトバウンドルール

| 優先度 | 名前 | ソース | ソースポート | 宛先 | 宛先ポート | プロトコル | アクション |
|-------|------|--------|------------|------|----------|-----------|----------|
| 100 | AllowContainerAppsOutbound | * | * | 10.0.1.0/24 | 80,443 | TCP | Allow |
| 110 | AllowKeyVaultOutbound | * | * | 10.0.2.7/32 | 443 | TCP | Allow |
| 120 | AllowInternetOutbound | * | * | Internet | * | * | Allow |
| 65000 | DenyAllOutbound | * | * | * | * | * | Deny |

### NSG: dify-containerapps-nsg

Container Apps Subnetに適用されるセキュリティルール。

#### インバウンドルール

| 優先度 | 名前 | ソース | ソースポート | 宛先 | 宛先ポート | プロトコル | アクション |
|-------|------|--------|------------|------|----------|-----------|----------|
| 100 | AllowAppGatewayInbound | 10.0.0.0/24 | * | VirtualNetwork | 80,443 | TCP | Allow |
| 110 | AllowHealthProbes | AzureLoadBalancer | * | VirtualNetwork | * | * | Allow |
| 200 | AllowVNetInbound | VirtualNetwork | * | VirtualNetwork | * | * | Allow |
| 65000 | DenyAllInbound | * | * | * | * | * | Deny |

**変更点**: Application Gateway使用時はインターネットから直接アクセスできないようInternalモードに設定。Application Gatewayサブネットからのトラフィックのみ許可。

#### アウトバウンドルール

| 優先度 | 名前 | ソース | ソースポート | 宛先 | 宛先ポート | プロトコル | アクション |
|-------|------|--------|------------|------|----------|-----------|----------|
| 100 | AllowPrivateEndpointOutbound | VirtualNetwork | * | 10.0.2.0/24 | 5432,6380,443 | TCP | Allow |
| 110 | AllowInternetOutbound | VirtualNetwork | * | Internet | 443 | TCP | Allow |
| 120 | AllowVNetOutbound | VirtualNetwork | * | VirtualNetwork | * | * | Allow |
| 65000 | DenyAllOutbound | * | * | * | * | * | Deny |

### NSG: dify-privateendpoint-nsg

Private Endpoint Subnetに適用されるセキュリティルール。

#### インバウンドルール

| 優先度 | 名前 | ソース | ソースポート | 宛先 | 宛先ポート | プロトコル | アクション |
|-------|------|--------|------------|------|----------|-----------|----------|
| 100 | AllowContainerAppsPostgres | 10.0.1.0/24 | * | 10.0.2.4/32 | 5432 | TCP | Allow |
| 110 | AllowContainerAppsRedis | 10.0.1.0/24 | * | 10.0.2.5/32 | 6380 | TCP | Allow |
| 120 | AllowContainerAppsBlob | 10.0.1.0/24 | * | 10.0.2.6/32 | 443 | TCP | Allow |
| 130 | AllowContainerAppsKeyVault | 10.0.1.0/24 | * | 10.0.2.7/32 | 443 | TCP | Allow |
| 140 | AllowAppGatewayKeyVault | 10.0.0.0/24 | * | 10.0.2.7/32 | 443 | TCP | Allow |
| 65000 | DenyAllInbound | * | * | * | * | * | Deny |

#### アウトバウンドルール

| 優先度 | 名前 | ソース | ソースポート | 宛先 | 宛先ポート | プロトコル | アクション |
|-------|------|--------|------------|------|----------|-----------|----------|
| 100 | AllowAzureServices | VirtualNetwork | * | AzureCloud | * | * | Allow |
| 65000 | DenyAllOutbound | * | * | * | * | * | Deny |

## Private DNS Zone設定

### 1. privatelink.postgres.database.azure.com

```
Zone: privatelink.postgres.database.azure.com
Virtual Network Links: dify-vnet (Auto Registration: Disabled)

DNS Records:
- Type: A
  Name: dify-postgres
  IP: 10.0.2.4
  TTL: 300
```

**用途**: PostgreSQL Flexible ServerへのPrivate Endpoint名前解決

### 2. privatelink.redis.cache.windows.net

```
Zone: privatelink.redis.cache.windows.net
Virtual Network Links: dify-vnet (Auto Registration: Disabled)

DNS Records:
- Type: A
  Name: dify-redis
  IP: 10.0.2.5
  TTL: 300
```

**用途**: Azure Cache for RedisへのPrivate Endpoint名前解決

### 3. privatelink.blob.core.windows.net

```
Zone: privatelink.blob.core.windows.net
Virtual Network Links: dify-vnet (Auto Registration: Disabled)

DNS Records:
- Type: A
  Name: difystorage{unique}
  IP: 10.0.2.6
  TTL: 300
```

**用途**: Blob StorageへのPrivate Endpoint名前解決

### 4. privatelink.vaultcore.azure.net

```
Zone: privatelink.vaultcore.azure.net
Virtual Network Links: dify-vnet (Auto Registration: Disabled)

DNS Records:
- Type: A
  Name: dify-keyvault-{unique}
  IP: 10.0.2.7
  TTL: 300
```

**用途**: Key VaultへのPrivate Endpoint名前解決（Application GatewayがSSL証明書を取得するために使用）

## Application Gateway詳細設定

### リスナー設定

| リスナー名 | プロトコル | ポート | ホスト名 | SSL証明書 |
|-----------|----------|-------|---------|---------|
| `https-listener` | HTTPS | 443 | * (全て) | Key Vault統合 |

### バックエンドプール設定

| プール名 | ターゲットタイプ | ターゲット | ポート |
|---------|--------------|-----------|-------|
| `dify-web-pool` | IP Address | Dify Web Container App (10.0.1.x) | 3000 |
| `dify-api-pool` | IP Address | Dify API Container App (10.0.1.y) | 5001 |

**注**: Container AppsのFQDNまたはプライベートIPアドレスを指定。Container Apps環境のVNet統合により、プライベートIPで直接アクセス可能。

### パスベースルール設定

| ルール名 | 優先度 | リスナー | パスパターン | バックエンドプール | バックエンドHTTP設定 |
|---------|-------|---------|------------|----------------|-----------------|
| `rule-web-root` | 100 | https-listener | `/` | dify-web-pool | http-settings-web |
| `rule-web-console` | 90 | https-listener | `/console/*` | dify-web-pool | http-settings-web |
| `rule-api-v1` | 80 | https-listener | `/v1/*` | dify-api-pool | http-settings-api |
| `rule-api` | 70 | https-listener | `/api/*` | dify-api-pool | http-settings-api |

**優先度**: 数値が小さいほど高優先度。より具体的なパスを高優先度に設定。

### バックエンドHTTP設定

| 設定名 | プロトコル | ポート | タイムアウト | クッキーベースアフィニティ | 接続ドレイン |
|-------|----------|-------|----------|---------------------|-----------|
| `http-settings-web` | HTTP | 3000 | 30秒 | 無効 | 有効 (120秒) |
| `http-settings-api` | HTTP | 5001 | 60秒 | 無効 | 有効 (120秒) |

**注**: バックエンド通信はVNet内部のため、HTTPで可（セキュアなプライベートネットワーク）。必要に応じてHTTPSに変更可能。

### ヘルスプローブ設定

| プローブ名 | プロトコル | パス | 間隔 | タイムアウト | 異常しきい値 |
|----------|----------|-----|------|------------|------------|
| `health-probe-web` | HTTP | `/` | 30秒 | 30秒 | 3回 |
| `health-probe-api` | HTTP | `/health` | 30秒 | 30秒 | 3回 |

**ヘルスプローブ動作**:
- Application Gatewayが定期的にバックエンドの正常性をチェック
- 異常しきい値に達したバックエンドはプールから除外
- 正常に戻ると自動的にプールに復帰

### WAF設定（本番環境のみ）

**注**: 開発環境ではStandard_v2 SKUを使用するため、WAF機能は利用できません。本番環境でWAF_v2 SKUを使用する場合の設定です。

| 項目 | 設定値 |
|-----|-------|
| **WAFモード** | Prevention（防止）/ Detection（検出）を選択可能 |
| **ルールセット** | OWASP 3.2 |
| **除外ルール** | 必要に応じてカスタム除外を設定 |
| **カスタムルール** | 特定IPの許可/拒否、レート制限等 |

**推奨設定**:
- 本番環境: Preventionモード（攻撃を自動ブロック）
- ステージング環境: Detectionモード（ログのみ、ブロックしない）

## 通信フロー詳細

### 1. ユーザーからDify Web UIへのアクセス（/, /console/*）

```
┌──────┐                              ┌──────────────────────────┐
│ User │─── HTTPS/443 (Internet) ────▶│ Application Gateway      │
└──────┘       パス: /                │ (Public IP)              │
           または /console/*            │ - SSL/TLS終端            │
                                      │ - パス判定               │
                                      │ - WAF検査(本番のみ)      │
                                      │ 10.0.0.x                 │
                                      └──────────┬───────────────┘
                                                 │ HTTP/HTTPS (VNet Internal)
                                                 │ dify-web-pool
                                      ┌──────────▼───────────┐
                                      │ dify-web             │
                                      │ (10.0.1.x:3000)      │
                                      └──────────────────────┘
```

- **SSL/TLS終端**: Application Gateway（証明書はKey Vaultから取得）
- **SKU**: 開発環境はStandard_v2、本番環境はWAF_v2
- **WAF保護**（本番のみ）: OWASP 3.2、SQLインジェクション/XSS等を防御
- **パスルール**: `/` または `/console/*` → dify-web-pool
- **バックエンド通信**: HTTP/HTTPSでApplication Gateway → Dify Web（直接）

### 2. ユーザーからDify APIへの直接アクセス（/api/*, /v1/*）

```
┌──────┐                              ┌──────────────────────────┐
│ User │─── HTTPS/443 (Internet) ────▶│ Application Gateway      │
└──────┘   パス: /api/* または /v1/*   │ (Public IP)              │
                                      │ - SSL/TLS終端            │
                                      │ - パス判定               │
                                      │ - WAF検査(本番のみ)      │
                                      │ 10.0.0.x                 │
                                      └──────────┬───────────────┘
                                                 │ HTTP/HTTPS (VNet Internal)
                                                 │ dify-api-pool
                                      ┌──────────▼───────────┐
                                      │ dify-api             │
                                      │ (10.0.1.y:5001)      │
                                      └──────────┬───────────┘
                                                 │
                                     ┌───────────┼───────────┐
                                     │           │           │
                                     ▼           ▼           ▼
                              PostgreSQL    Redis      Blob Storage
                              10.0.2.4     10.0.2.5    10.0.2.6
```

- **パスルール**: `/api/*` または `/v1/*` → dify-api-pool
- **直接ルーティング**: Container Apps Ingressを経由せずDify APIへ直接
- **レイテンシー削減**: 1ホップ削減により応答速度向上
- **独立したヘルスプローブ**: APIバックエンドの健全性を個別監視
- **WAF保護**（本番のみ）: API呼び出しもWAFで保護

### 3. Dify Web → Dify API (内部通信)

```
┌──────────┐            ┌──────────┐
│ dify-web │──── HTTP ──▶│ dify-api │
│10.0.1.x  │  (Internal) │10.0.1.y  │
└──────────┘            └──────────┘
```

- VNet内部通信（暗号化不要、高速）
- Service Discovery: Container Apps Environment内の自動DNS解決

### 4. Dify API → PostgreSQL

```
┌──────────┐   TCP/5432   ┌────────────────┐   Private Link   ┌────────────┐
│ dify-api │──────────────▶│ Private        │──────────────────▶│ PostgreSQL │
│10.0.1.y  │  (VNet内)     │ Endpoint       │                  │ (PaaS)     │
└──────────┘              │ 10.0.2.4       │                  └────────────┘
                          └────────────────┘
```

- DNS解決: `dify-postgres.postgres.database.azure.com` → `10.0.2.4` (Private DNS Zone)
- SSL接続: `sslmode=require` (必須)
- 認証: PostgreSQL User/Password または Managed Identity (AAD)

### 5. Dify API → Redis

```
┌──────────┐   TCP/6380   ┌────────────────┐   Private Link   ┌────────┐
│ dify-api │──────────────▶│ Private        │──────────────────▶│ Redis  │
│10.0.1.y  │  (VNet内)     │ Endpoint       │                  │ (PaaS) │
└──────────┘              │ 10.0.2.5       │                  └────────┘
                          └────────────────┘
```

- DNS解決: `dify-redis.redis.cache.windows.net` → `10.0.2.5` (Private DNS Zone)
- SSL接続: Port 6380 (SSL有効)
- 認証: Access Key または AAD Token

### 6. Dify API/Worker → Blob Storage

```
┌──────────┐   HTTPS/443  ┌────────────────┐   Private Link   ┌──────────┐
│ dify-api │──────────────▶│ Private        │──────────────────▶│ Blob     │
│10.0.1.y  │  (VNet内)     │ Endpoint       │                  │ Storage  │
└──────────┘              │ 10.0.2.6       │                  │ (PaaS)   │
                          └────────────────┘                  └──────────┘
```

- DNS解決: `difystorageXXXX.blob.core.windows.net` → `10.0.2.6` (Private DNS Zone)
- 認証: Access Key, SAS Token, または Managed Identity

### 7. Dify API ⇄ Dify Worker (Celery)

```
┌──────────┐                                    ┌─────────────┐
│ dify-api │──── Enqueue Task (via Redis) ─────▶│ dify-worker │
│10.0.1.y  │                                    │ 10.0.1.z    │
└──────────┘◀─── Return Result (via Redis) ─────└─────────────┘
                           │
                           ▼
                   ┌────────────────┐
                   │ Redis Queue    │
                   │ (10.0.2.5)     │
                   └────────────────┘
```

- Celery Broker: Redis
- Task Queue: Celeryがキューイング
- Result Backend: Redis

## セキュリティベストプラクティス

### 1. ネットワーク分離

- **多層防御**: Application Gateway → Container Apps (Internal) → Private Endpoints
- **WAF保護**（本番のみ）: OWASP攻撃からの防御（SQLi、XSS、RCE等）
- **開発環境**: Standard_v2でコスト最適化、NSGとPrivate Endpointで保護
- **Container Apps Internal**: インターネットから直接アクセス不可、Application Gateway経由のみ
- **PaaSサービス**: すべてPrivate Endpoint経由でアクセス
- **パブリックアクセス無効化**: PostgreSQL、Redis、Storage、Key VaultのFirewall設定
- **サブネット分離**:
  - Application Gateway専用サブネット
  - Container Apps専用サブネット
  - Private Endpoint専用サブネット

### 2. 最小権限の原則

- **NSG**: 必要最小限のポートのみ許可
- **Private Endpoint Network Policy**: 無効化（Private Endpoint要件）
- **Service Endpoint**: 使用せず、Private Endpointのみ使用

### 3. 暗号化

- **転送時の暗号化**:
  - インターネット → Application Gateway: TLS 1.2以上（強制）
  - Application Gateway → Container Apps: HTTP/HTTPS（VNet内部、セキュアなネットワーク）
  - Container Apps → Private Endpoints: SSL/TLS接続
- **保存時**: Azure標準の暗号化（自動有効）
- **証明書管理**: Key Vault統合、Application GatewayがManaged Identityで取得

### 4. 監視

- **Application Gateway診断ログ**:
  - アクセスログ（全リクエスト/レスポンス）
  - WAFログ（ブロックされた攻撃、本番のみ）
  - パフォーマンスログ
- **NSG Flow Logs**: 有効化（Log Analytics Workspace送信）
- **Diagnostic Settings**: すべてのネットワークリソースで有効化
- **メトリクス監視**:
  - Application Gateway: スループット、応答時間、異常ホスト数
  - WAF（本番のみ）: ブロックされたリクエスト数、ルールトリガー数

## スケーリング時の考慮事項

### Application Gatewayのスケール

- **IPアドレス消費**: Application Gatewayインスタンスごとに1つのプライベートIP
- **オートスケール設定**:
  - 最小キャパシティ: 1-2ユニット
  - 最大キャパシティ: 10ユニット
- **サブネットサイズ**: `/24` (256アドレス)で十分（最大125インスタンスまで）
- **ゾーン冗長**: 可用性ゾーン対応リージョンで有効化推奨

### Container Apps Environmentのスケール

- **IPアドレス消費**: 各レプリカが1つのプライベートIPを消費
- **最大レプリカ数**: サブネットサイズに依存
  - `/24` (256アドレス): 約240レプリカ（Azure予約IPを考慮）
  - `/23` (512アドレス): 約500レプリカ
- **推奨**: 将来のスケール計画に基づきサブネットサイズを決定

### Private Endpointの追加

- **現在の構成**: PostgreSQL、Redis、Blob Storage、Key Vault
- **追加候補**:
  - Container Registry Private Endpoint（カスタムイメージ使用時）
  - Application Insights Private Endpoint（セキュリティ強化時）
- **追加IP必要数**: Private Endpointあたり1つのプライベートIP

## トラブルシューティング

### 接続問題の診断手順

1. **Application Gateway正常性確認**
   ```bash
   # バックエンドヘルスの確認
   az network application-gateway show-backend-health --resource-group <rg> --name dify-appgateway

   # Application Gatewayステータス確認
   az network application-gateway show --resource-group <rg> --name dify-appgateway --query provisioningState
   ```

2. **NSGルール確認**
   ```bash
   # Application Gateway NSG
   az network nsg rule list --resource-group <rg> --nsg-name dify-appgateway-nsg --output table

   # Container Apps NSG
   az network nsg rule list --resource-group <rg> --nsg-name dify-containerapps-nsg --output table
   ```

3. **Private DNS解決確認**
   ```bash
   # Container App内から実行
   nslookup dify-postgres.postgres.database.azure.com
   # 結果: 10.0.2.4 が返ることを確認

   # Application Gateway用（Key Vault証明書取得確認）
   nslookup dify-keyvault-{unique}.vault.azure.net
   # 結果: 10.0.2.7 が返ることを確認
   ```

4. **接続テスト**
   ```bash
   # Application Gateway経由のHTTPS接続テスト
   curl -v https://<your-domain>/

   # PostgreSQL接続テスト（Container App内から）
   psql "host=dify-postgres.postgres.database.azure.com port=5432 dbname=dify user=difyuser sslmode=require"

   # Redis接続テスト（Container App内から）
   redis-cli -h dify-redis.redis.cache.windows.net -p 6380 --tls
   ```

5. **Application Gateway診断ログ確認**
   ```bash
   # アクセスログ確認（Log Analytics）
   az monitor log-analytics query \
     --workspace <workspace-id> \
     --analytics-query "AzureDiagnostics | where ResourceType == 'APPLICATIONGATEWAYS' | order by TimeGenerated desc"
   ```

6. **NSG Flow Logs確認**
   - Log Analytics Workspaceで通信ログ分析
   - Blocked通信の特定

### よくある問題

| 問題 | 原因 | 解決方法 |
|-----|------|---------|
| Application Gateway 502エラー | バックエンドが異常 | Container Apps Ingressの正常性確認、NSGルール確認 |
| Application Gateway 証明書エラー | Key Vault接続失敗 | Managed Identity設定確認、Key Vault Private Endpoint確認 |
| WAFでリクエストがブロック | WAFルールにマッチ | WAFログ確認、除外ルール設定またはDetectionモード切替 |
| Container Appsに到達しない | NSGルールでブロック | dify-containerapps-nsgでApplication Gatewayサブネットからの通信を許可 |
| SSL証明書更新されない | Managed Identity権限不足 | Key Vaultアクセスポリシー確認、証明書読み取り権限付与 |
| PostgreSQL接続失敗 | Private DNS未設定 | Private DNS Zone作成、VNetリンク設定 |
| Redis接続タイムアウト | NSGでポート6380未許可 | NSGルール追加 |
| Blob Storage 403エラー | パブリックアクセス有効 | Storageのパブリックアクセス無効化 |
| Container Apps起動失敗 | サブネット委任なし | サブネットの委任設定追加 |

## 次のステップ

1. [システムアーキテクチャ全体図](./architecture-overview.md)を確認
2. Bicep `network.bicep` モジュールの実装
3. NSGルールのBicep定義
4. Private DNS Zone統合のBicep実装
