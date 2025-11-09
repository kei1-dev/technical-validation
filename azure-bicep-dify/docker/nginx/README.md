# Nginx Reverse Proxy Container

このディレクトリには、Dify on AzureのリバースプロキシとしてのNginx設定が含まれています。

## 概要

Nginxは、Application Gatewayからのリクエストを受け取り、適切なバックエンドサービス（Web、API、Plugin Daemon）にルーティングします。

## ルーティング設定

### エンドポイントマッピング

| パス | バックエンド | ポート | 説明 |
|------|-------------|--------|------|
| `/console/api` | API | 5001 | 管理コンソールAPI |
| `/api` | API | 5001 | 公開API |
| `/v1` | API | 5001 | V1 API |
| `/files` | API | 5001 | ファイルアップロード/ダウンロード |
| `/mcp` | API | 5001 | Model Context Protocol |
| `/e/` | Plugin Daemon | 5002 | プラグインフックエンドポイント |
| `/explore` | Web | 3000 | 探索インターフェース |
| `/` | Web | 3000 | メインWebUI |
| `/health` | nginx | - | ヘルスチェック |

### Plugin Daemonルーティング

Plugin Daemonは`/e/`パスでアクセス可能で、外部サービスからのプラグインフック呼び出しを処理します。

**特別なヘッダー**:
- `Dify-Hook-Url`: 元のリクエストURLを保持（プラグインが呼び出し元を識別するため）

**設定例**:
```nginx
location /e/ {
    proxy_pass http://plugin_daemon;
    proxy_set_header Host ${DIFY_PLUGIN_DAEMON_HOST};
    proxy_set_header Dify-Hook-Url $scheme://$host$request_uri;
    include /etc/nginx/proxy_params;
}
```

## 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `DIFY_WEB_HOST` | `web` | Webコンテナのホスト名 |
| `DIFY_WEB_PORT` | `3000` | Webコンテナのポート |
| `DIFY_API_HOST` | `api` | APIコンテナのホスト名 |
| `DIFY_API_PORT` | `5001` | APIコンテナのポート |
| `DIFY_PLUGIN_DAEMON_HOST` | `plugin_daemon` | Plugin Daemonコンテナのホスト名 |
| `DIFY_PLUGIN_DAEMON_PORT` | `5002` | Plugin Daemonコンテナのポート |

### Azure Container Appsでの設定

Container Apps環境では、サービス名で直接アクセスできます：

```bicep
environment: [
  { name: 'DIFY_WEB_HOST', value: 'web' }
  { name: 'DIFY_WEB_PORT', value: '3000' }
  { name: 'DIFY_API_HOST', value: 'api' }
  { name: 'DIFY_API_PORT', value: '5001' }
  { name: 'DIFY_PLUGIN_DAEMON_HOST', value: 'plugin_daemon' }
  { name: 'DIFY_PLUGIN_DAEMON_PORT', value: '5002' }
]
```

## プロキシ設定（proxy_params）

### SSE/ストリーミングサポート

```nginx
proxy_buffering off;
```

LLMのストリーミングレスポンス（Server-Sent Events）をサポートするため、バッファリングを無効化しています。

### タイムアウト設定

```nginx
proxy_read_timeout 300s;
proxy_send_timeout 300s;
proxy_connect_timeout 60s;
```

以下のユースケースに対応するため、長めのタイムアウトを設定：
- LLM APIコール（数分かかる場合がある）
- プラグイン実行（処理時間が必要）
- Sandboxでのコード実行（時間がかかる場合がある）

### ヘッダー転送

```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Port $server_port;
```

クライアント情報をバックエンドに正しく伝達します。

## ビルドとデプロイ

### ローカルでのビルド

```bash
# イメージをビルド
docker build -t dify-nginx:latest docker/nginx/

# ローカルで実行
docker run -d \
  -p 80:80 \
  -e DIFY_WEB_HOST=web \
  -e DIFY_WEB_PORT=3000 \
  -e DIFY_API_HOST=api \
  -e DIFY_API_PORT=5001 \
  -e DIFY_PLUGIN_DAEMON_HOST=plugin_daemon \
  -e DIFY_PLUGIN_DAEMON_PORT=5002 \
  --name dify-nginx \
  dify-nginx:latest
```

### Azure Container Registryへのプッシュ

```bash
# ACRにログイン
az acr login --name <your-acr-name>

# イメージにタグ付け
docker tag dify-nginx:latest <your-acr-name>.azurecr.io/dify-nginx:latest

# プッシュ
docker push <your-acr-name>.azurecr.io/dify-nginx:latest
```

## テスト

### ルーティングのテスト

```bash
# ヘルスチェック
curl http://localhost/health

# Web UIへのアクセス
curl http://localhost/

# API エンドポイント
curl http://localhost/api/version

# Plugin Daemon エンドポイント
curl http://localhost/e/health
```

### ログの確認

```bash
# アクセスログ
docker exec dify-nginx tail -f /var/log/nginx/access.log

# エラーログ
docker exec dify-nginx tail -f /var/log/nginx/error.log
```

## トラブルシューティング

### 問題: 502 Bad Gateway

**原因**: バックエンドサービスが起動していない、または到達不可能

**解決策**:
1. バックエンドコンテナが実行中か確認
2. ホスト名とポートが正しいか確認
3. Container Apps Environment内の内部ネットワーク接続を確認

### 問題: 504 Gateway Timeout

**原因**: バックエンドの応答が遅い、またはタイムアウト設定が短すぎる

**解決策**:
1. `proxy_read_timeout`を増やす
2. バックエンドのパフォーマンスを確認
3. LLMリクエストの場合は正常（長時間かかる場合がある）

### 問題: Plugin Daemonへのルーティングが機能しない

**原因**: Plugin Daemonが起動していない、または環境変数が正しくない

**解決策**:
1. Plugin Daemonコンテナが実行中か確認
2. `DIFY_PLUGIN_DAEMON_HOST`と`DIFY_PLUGIN_DAEMON_PORT`が正しいか確認
3. `/e/`パスでアクセスしているか確認（末尾のスラッシュが重要）

### 問題: SSEストリーミングが機能しない

**原因**: プロキシバッファリングが有効になっている

**解決策**:
1. `proxy_buffering off;`が設定されているか確認
2. `proxy_params`が正しくインクルードされているか確認

## セキュリティ考慮事項

- **内部通信のみ**: nginxはContainer Apps Environment内でのみアクセス可能
- **Application Gateway統合**: 外部からのアクセスはApplication Gateway経由のみ
- **ヘッダー検証**: 必要なヘッダーのみを転送
- **タイムアウト制限**: DoS攻撃を防ぐための適切なタイムアウト設定

## パフォーマンス最適化

### 接続の再利用

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
```

HTTP/1.1とKeep-Aliveを使用して、バックエンドへの接続を再利用します。

### バッファリング

通常のリクエストではバッファリングを有効にすることでパフォーマンスが向上しますが、SSEサポートのため無効化しています。

## 参考資料

- [Nginx Reverse Proxy Documentation](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Azure Container Apps Networking](https://learn.microsoft.com/azure/container-apps/networking)
- [Dify Plugin System](https://docs.dify.ai/plugins)
