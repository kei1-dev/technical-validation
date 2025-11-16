# SSRF Proxy Container

このディレクトリには、Dify on AzureのSSRF（Server-Side Request Forgery）保護用のSquidプロキシコンテナの設定が含まれています。

## 概要

SSRF Proxyは、Sandboxコンテナからの外部HTTPリクエストをフィルタリングし、プライベートIPアドレスやクラウドメタデータエンドポイントへのアクセスをブロックします。

## 機能

### フォワードプロキシ（デフォルト）
- すべての外部HTTP/HTTPSリクエストをプロキシ
- プライベートIPレンジへのアクセスをブロック（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8）
- クラウドメタデータエンドポイントへのアクセスをブロック（169.254.169.254）
- 安全なポート（80, 443）のみ許可

### リバースプロキシ（オプション）
- Sandboxコンテナへのリバースプロキシ機能
- 通常は不要（Sandboxは内部FQDNで直接アクセス可能）
- 特定のユースケースでのみ有効化

## 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `HTTP_PORT` | `3128` | フォワードプロキシのポート |
| `COREDUMP_DIR` | `/var/spool/squid` | コアダンプディレクトリ |
| `REVERSE_PROXY_PORT` | `""` | リバースプロキシポート（空の場合は無効） |
| `SANDBOX_HOST` | `""` | Sandboxの内部FQDN |
| `SANDBOX_PORT` | `8194` | Sandboxのポート |

## ビルドとデプロイ

### ローカルでのビルド

```bash
# イメージをビルド
docker build -t ssrf-proxy:latest docker/ssrf_proxy/

# ローカルで実行
docker run -d \
  -p 3128:3128 \
  -e HTTP_PORT=3128 \
  -e COREDUMP_DIR=/var/spool/squid \
  --name ssrf-proxy \
  ssrf-proxy:latest
```

### Azure Container Registryへのプッシュ

```bash
# ACRにログイン
az acr login --name <your-acr-name>

# イメージにタグ付け
docker tag ssrf-proxy:latest <your-acr-name>.azurecr.io/ssrf-proxy:latest

# プッシュ
docker push <your-acr-name>.azurecr.io/ssrf-proxy:latest
```

### Azure Container Appsでのデプロイ

Bicepテンプレート（`bicep/main/modules/ssrfProxyContainerApp.bicep`）を使用して自動的にデプロイされます。

## 設定

### フォワードプロキシのみ使用（推奨）

デフォルト設定では、フォワードプロキシのみが有効です。`REVERSE_PROXY_PORT`を設定しないでください。

```bicep
environment: [
  { name: 'HTTP_PORT', value: '3128' }
  { name: 'COREDUMP_DIR', value: '/var/spool/squid' }
]
```

### リバースプロキシを有効化（特殊なケースのみ）

リバースプロキシが必要な場合は、以下の環境変数を設定します：

```bicep
environment: [
  { name: 'HTTP_PORT', value: '3128' }
  { name: 'COREDUMP_DIR', value: '/var/spool/squid' }
  { name: 'REVERSE_PROXY_PORT', value: '8194' }
  { name: 'SANDBOX_HOST', value: 'dify-dev-sandbox.internal.example.com' }
  { name: 'SANDBOX_PORT', value: '8194' }
]
```

## テスト

### フォワードプロキシのテスト

```bash
# 正常なリクエスト（許可されるべき）
curl -x http://localhost:3128 https://api.github.com

# プライベートIPへのリクエスト（ブロックされるべき）
curl -x http://localhost:3128 http://10.0.0.1

# メタデータエンドポイントへのリクエスト（ブロックされるべき）
curl -x http://localhost:3128 http://169.254.169.254/metadata
```

### ログの確認

```bash
# Squidアクセスログ
docker exec ssrf-proxy tail -f /var/log/squid/access.log

# Squidキャッシュログ
docker exec ssrf-proxy tail -f /var/log/squid/cache.log
```

## トラブルシューティング

### 問題: 正当なリクエストがブロックされる

**原因**: ACLルールが厳しすぎる

**解決策**: `squid.conf.template`のACLルールを確認し、必要に応じて調整

### 問題: プライベートIPへのアクセスが許可される

**原因**: ACLルールが正しく適用されていない

**解決策**: 
1. `private_ips` ACLが正しく定義されているか確認
2. `http_access deny private_ips`が`http_access allow localnet`より前にあるか確認

### 問題: コンテナが起動しない

**原因**: 環境変数の置換エラー

**解決策**:
1. すべての必須環境変数が設定されているか確認
2. コンテナログを確認: `docker logs ssrf-proxy`

## セキュリティ考慮事項

- **プライベートIPブロック**: すべてのRFC1918プライベートIPレンジをブロック
- **メタデータブロック**: クラウドメタデータエンドポイント（AWS、Azure、GCP）をブロック
- **ポート制限**: HTTP（80）とHTTPS（443）のみ許可
- **ローカルネットワーク**: Container Apps Environment内の通信は許可

## 参考資料

- [Squid Configuration Directive](http://www.squid-cache.org/Doc/config/)
- [SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Azure Container Apps Networking](https://learn.microsoft.com/azure/container-apps/networking)
