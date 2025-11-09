# Design Document

## Overview

このドキュメントは、Dify on Azureインフラストラクチャに不足している4つの重要なコンテナ（Sandbox、SSRF Proxy、Plugin Daemon、Worker Beat）を追加するための設計を定義します。これらのコンテナは、Difyの完全な機能セット（コード実行、セキュリティ、プラグインシステム、定期タスク）を提供するために必要です。

## Architecture

### High-Level Architecture

```
                        Internet / Users
                              │
                              ▼
                   ┌──────────────────────┐
                   │ Application Gateway  │
                   │  (WAF, SSL, LB)      │
                   └──────────┬───────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────────┐
│                     Azure Container Apps Environment                      │
│                                                                            │
│                   ┌──────────────────────┐                                │
│                   │       nginx          │                                │
│                   │  (Reverse Proxy)     │                                │
│                   └────┬────────────┬────┘                                │
│                        │            │                                     │
│              ┌─────────▼──┐    ┌───▼─────────┐                           │
│              │  Dify Web  │    │  Dify API   │───┐                       │
│              │ (Frontend) │    │  (Backend)  │   │                       │
│              └────────────┘    └───┬─────────┘   │                       │
│                                    │             │                       │
│              ┌─────────────────────┼─────────────┼───────┐               │
│              │                     │             │       │               │
│              │                     ▼             │       │               │
│              │            ┌─────────────────┐    │       │               │
│              │            │     Worker      │────┤       │               │
│              │            │  (Celery Tasks) │    │       │               │
│              │            └─────────────────┘    │       │               │
│              │                                   │       │               │
│  ┌───────────▼───────────────────────────────────▼───────▼──────────┐   │
│  │                    New Containers (Added)                        │   │
│  │                                                                   │   │
│  │  ┌──────────────────────────────────────────────┐               │   │
│  │  │         Worker Beat (Scheduler)              │───┐           │   │
│  │  │  - Celery Beat for periodic tasks            │   │           │   │
│  │  │  - Connects to Redis for task queue          │   │           │   │
│  │  └──────────────────────────────────────────────┘   │           │   │
│  │                                                      │           │   │
│  │  ┌──────────────────────────────────────────────┐   │           │   │
│  │  │         Plugin Daemon                        │───┼───┐       │   │
│  │  │  - Plugin management & execution             │◄──┼───┼───────┼───┤
│  │  │  - Connects to dify_plugin DB                │   │   │ API   │   │
│  │  │  - Stores plugins in Azure Blob              │   │   │       │   │
│  │  └──────────────────────────────────────────────┘   │   │       │   │
│  │                                                      │   │       │   │
│  │  ┌──────────────────────────────────────────────┐   │   │       │   │
│  │  │         Sandbox (Code Execution)             │◄──┼───┼───────┼───┤
│  │  │  - Executes Python code safely               │   │   │ API   │   │
│  │  │  - Isolated environment                      │   │   │       │   │
│  │  └────────────────┬─────────────────────────────┘   │   │       │   │
│  │                   │                                  │   │       │   │
│  │                   │ All external HTTP/HTTPS requests │   │       │   │
│  │                   ▼                                  │   │       │   │
│  │  ┌──────────────────────────────────────────────┐   │   │       │   │
│  │  │         SSRF Proxy (Security Layer)          │   │   │       │   │
│  │  │  - Squid proxy for request filtering         │   │   │       │   │
│  │  │  - Blocks private IP ranges (SSRF protection)│   │   │       │   │
│  │  │  - Allows only safe external API access      │   │   │       │   │
│  │  └────────────────┬─────────────────────────────┘   │   │       │   │
│  │                   │                                  │   │       │   │
│  └───────────────────┼──────────────────────────────────┼───┼───────┘   │
│                      │                                  │   │           │
└──────────────────────┼──────────────────────────────────┼───┼───────────┘
                       │                                  │   │
                       ▼                                  │   │
              External APIs                               │   │
              (GitHub, OpenAI, etc.)                      │   │
                                                          │   │
┌─────────────────────────────────────────────────────────┼───┼───────────┐
│                    Data Layer (Private Endpoints)       │   │           │
│                                                          │   │           │
│  ┌──────────────────────────────────────────────┐       │   │           │
│  │         PostgreSQL Flexible Server           │◄──────┼───┼───────────┤
│  │  - dify database (API, Worker, Worker Beat)  │       │   │           │
│  │  - dify_plugin database (Plugin Daemon)      │       │   │           │
│  └──────────────────────────────────────────────┘       │   │           │
│                                                          │   │           │
│  ┌──────────────────────────────────────────────┐       │   │           │
│  │         Azure Cache for Redis                │◄──────┼───┘           │
│  │  - Session store                             │       │               │
│  │  - Celery message queue                      │       │               │
│  │  - Cache layer                               │       │               │
│  └──────────────────────────────────────────────┘       │               │
│                                                          │               │
│  ┌──────────────────────────────────────────────┐       │               │
│  │         Azure Blob Storage                   │◄──────┘               │
│  │  - dify-app-storage (files, documents)       │                       │
│  │  - dify-plugins (plugin packages)            │                       │
│  └──────────────────────────────────────────────┘                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key Points**:
- **nginx**: Application Gatewayからのリクエストを受け、以下にルーティング
  - `/` → Web (3000)
  - `/console/api`, `/api`, `/v1`, `/files`, `/mcp` → API (5001)
  - `/e/` → Plugin Daemon (5002) - プラグインフックエンドポイント
  - `/explore` → Web (3000)
- **API/Worker/Worker Beat**: PostgreSQL、Redis、Blob Storageに接続
- **API/Worker**: Sandbox、Plugin Daemon（内部API）、SSRF Proxyを利用
- **Sandbox**: コード実行時、すべての外部リクエストはSSRF Proxy経由
- **Plugin Daemon**: 
  - nginxから`/e/`パスで直接アクセス可能（プラグインフック用）
  - APIと内部API通信でプラグイン管理
  - 専用のdify_plugin DBに接続
  - プラグインパッケージをBlob Storageに保存
- **Worker Beat**: Redisに接続して定期タスクをスケジュール
- **SSRF Proxy**: Sandboxからの外部リクエストをフィルタリング
- **Data Layer**: すべてPrivate Endpoint経由で安全に接続


### Container Communication Flow

```
API/Worker Container
    │
    ├─→ CODE_EXECUTION_ENDPOINT → Sandbox (port 8194)
    │                                  │
    │                                  └─→ HTTP_PROXY → SSRF Proxy (port 3128)
    │                                                        │
    │                                                        └─→ External APIs
    │
    ├─→ PLUGIN_DAEMON_URL → Plugin Daemon (port 5002)
    │                              │
    │                              └─→ DIFY_INNER_API_URL → API Container
    │
    └─→ SSRF_PROXY_HTTP_URL → SSRF Proxy (port 3128)

Worker Beat Container
    │
    └─→ Redis → Celery Beat Scheduler → Periodic Tasks
```

## Components and Interfaces

### nginx Container App更新

- 公式 `docker/nginx/default.conf.template` と同じルーティングルールを維持し、Container Apps の内部サービス名で直接プロキシする。
- 追加の `DIFY_PLUGIN_DAEMON_HOST` などの環境変数は不要。`plugin_daemon:5002` へ直接転送する。

```nginx
server {
    listen 80;
    server_name _;

    location /console/api {
        proxy_pass http://api:5001;
        include /etc/nginx/proxy_params;
    }

    location /api {
        proxy_pass http://api:5001;
        include /etc/nginx/proxy_params;
    }

    location /v1 {
        proxy_pass http://api:5001;
        include /etc/nginx/proxy_params;
    }

    location /files {
        proxy_pass http://api:5001;
        include /etc/nginx/proxy_params;
    }

    location /mcp {
        proxy_pass http://api:5001;
        include /etc/nginx/proxy_params;
    }

    location /e/ {
        proxy_pass http://plugin_daemon:5002;
        proxy_set_header Dify-Hook-Url $scheme://$host$request_uri;
        include /etc/nginx/proxy_params;
    }

    location /explore {
        proxy_pass http://web:3000;
        include /etc/nginx/proxy_params;
    }

    location / {
        proxy_pass http://web:3000;
        include /etc/nginx/proxy_params;
    }
}
```

### 1. Sandbox Container App

**Purpose**: 安全なコード実行環境を提供

**Bicep Module**: `bicep/main/modules/sandboxContainerApp.bicep`

**Configuration**:
- Image: `langgenius/dify-sandbox:0.2.12`
- Port: 8194 (internal)
- CPU: 0.5
- Memory: 1.0Gi
- Min Replicas: 0 (dev) / 1 (prod)
- Max Replicas: 5 (dev) / 10 (prod)

**Environment Variables**:
```bicep
[
  { name: 'API_KEY', secretRef: 'sandbox-api-key' }
  { name: 'GIN_MODE', value: 'release' }
  { name: 'WORKER_TIMEOUT', value: '15' }
  { name: 'ENABLE_NETWORK', value: 'true' }
  { name: 'HTTP_PROXY', value: 'http://dify-{env}-ssrf-proxy.internal.{domain}:3128' }
  { name: 'HTTPS_PROXY', value: 'http://dify-{env}-ssrf-proxy.internal.{domain}:3128' }
  { name: 'SANDBOX_PORT', value: '8194' }
]
```

**Secrets**:
- `sandbox-api-key`: Unique API key for authentication (generated or provided)

**Health Check**:
- Endpoint: `http://localhost:8194/health`
- Interval: 30s


### 2. SSRF Proxy Container App

**Purpose**: SSRF攻撃を防ぐためのプロキシサーバー

**Bicep Module**: `bicep/main/modules/ssrfProxyContainerApp.bicep`

**Configuration**:
- Image: `ubuntu/squid:latest`
- Port: 3128 (internal)
- CPU: 0.25
- Memory: 0.5Gi
- Min Replicas: 0 (dev) / 1 (prod)
- Max Replicas: 3 (dev) / 5 (prod)

**Environment Variables**:
```bicep
[
  { name: 'HTTP_PORT', value: '3128' }
  { name: 'COREDUMP_DIR', value: '/var/spool/squid' }
  { name: 'REVERSE_PROXY_PORT', value: '8194' }
  { name: 'SANDBOX_HOST', value: 'dify-{env}-sandbox.internal.{domain}' }
  { name: 'SANDBOX_PORT', value: '8194' }
]
```

**Custom Configuration**:
- Squid configuration file will be created in `docker/ssrf_proxy/squid.conf.template`
- Configuration will be mounted as a volume or baked into a custom image

**Squid Configuration Template**:
```conf
# Basic Squid configuration for SSRF protection
http_port 3128

# ACL definitions
acl localnet src 10.0.0.0/8
acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 443
acl CONNECT method CONNECT

# Deny access to private IP ranges (SSRF protection)
acl private_ips dst 10.0.0.0/8
acl private_ips dst 172.16.0.0/12
acl private_ips dst 192.168.0.0/16
acl private_ips dst 127.0.0.0/8
acl private_ips dst fc00::/7
acl private_ips dst fe80::/10

# Allow local network
http_access allow localnet

# Deny access to private IPs
http_access deny private_ips

# Allow safe ports
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports

# Default deny
http_access deny all

# Reverse proxy to sandbox
http_port 8194 accel defaultsite=${SANDBOX_HOST}
cache_peer ${SANDBOX_HOST} parent ${SANDBOX_PORT} 0 no-query originserver
```

**運用ノート**:
- 既定フローは Sandbox から外部宛の HTTP/S をフォワードプロキシ経由で中継し、リバースプロキシ (`http_port 8194 accel ...`) は Sandbox を呼び出す必要があるシナリオでのみ有効化する。
- `REVERSE_PROXY_PORT` を利用しない場合は該当ブロックを無効化し、SSRF 保護 ACL を維持したままフォワードプロキシとして運用する。


### 3. Plugin Daemon Container App

**Purpose**: Difyプラグインの管理と実行

**Bicep Module**: `bicep/main/modules/pluginDaemonContainerApp.bicep`

**Configuration**:
- Image: `langgenius/dify-plugin-daemon:0.4.0`
- Ports: 5002 (API), 5003 (debugging)
- CPU: 1.0
- Memory: 2.0Gi
- Min Replicas: 0 (dev) / 1 (prod)
- Max Replicas: 5 (dev) / 10 (prod)

**Environment Variables**:
```bicep
[
  // Database configuration (separate database)
  { name: 'DB_HOST', value: '{postgres-fqdn}' }
  { name: 'DB_PORT', value: '5432' }
  { name: 'DB_USERNAME', value: '{username}' }
  { name: 'DB_PASSWORD', secretRef: 'db-password' }
  { name: 'DB_DATABASE', value: 'dify_plugin' }
  
  // Redis configuration
  { name: 'REDIS_HOST', value: '{redis-hostname}' }
  { name: 'REDIS_PORT', value: '{redis-port}' }
  { name: 'REDIS_PASSWORD', secretRef: 'redis-password' }
  { name: 'REDIS_USE_SSL', value: 'true' }
  
  // Plugin Daemon configuration
  { name: 'SERVER_PORT', value: '5002' }
  { name: 'SERVER_KEY', secretRef: 'plugin-daemon-key' }
  { name: 'MAX_PLUGIN_PACKAGE_SIZE', value: '52428800' }
  { name: 'PPROF_ENABLED', value: 'false' }
  
  // Dify API integration
  { name: 'DIFY_INNER_API_URL', value: 'http://dify-{env}-api.internal.{domain}' }
  { name: 'DIFY_INNER_API_KEY', secretRef: 'plugin-inner-api-key' }
  
  // Remote debugging
  { name: 'PLUGIN_REMOTE_INSTALLING_HOST', value: '0.0.0.0' }
  { name: 'PLUGIN_REMOTE_INSTALLING_PORT', value: '5003' }
  
  // Plugin storage (Azure Blob)
  { name: 'PLUGIN_STORAGE_TYPE', value: 'azure_blob' }
  { name: 'AZURE_BLOB_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection-string' }
  { name: 'AZURE_BLOB_STORAGE_CONTAINER_NAME', value: 'dify-plugins' }
  
  // Plugin execution
  { name: 'PLUGIN_WORKING_PATH', value: '/app/storage/cwd' }
  { name: 'FORCE_VERIFYING_SIGNATURE', value: 'true' }
  { name: 'PYTHON_ENV_INIT_TIMEOUT', value: '120' }
  { name: 'PLUGIN_MAX_EXECUTION_TIMEOUT', value: '600' }
]
```

**Secrets**:
- `plugin-daemon-key`: Server authentication key
- `plugin-inner-api-key`: API key for communication with Dify API
- `db-password`: PostgreSQL password (shared)
- `redis-password`: Redis password (shared)
- `storage-connection-string`: Azure Blob Storage connection string

**Database Setup**:
- A separate database `dify_plugin` will be created in the same PostgreSQL server
- Plugin Daemon will manage its own schema


### 4. Worker Beat Container App

**Purpose**: Celery Beatスケジューラーで定期タスクを実行

**Bicep Module**: 既存の `containerApp.bicep` を再利用

**Configuration**:
- Image: `langgenius/dify-api:latest` (same as API/Worker)
- Port: None (no ingress)
- CPU: 0.5
- Memory: 1.0Gi
- Min Replicas: 1 (always running)
- Max Replicas: 1 (single instance only)

**Environment Variables**:
```bicep
[
  // Mode
  { name: 'MODE', value: 'beat' }
  
  // Database configuration (same as API/Worker)
  { name: 'DB_HOST', value: '{postgres-fqdn}' }
  { name: 'DB_PORT', value: '5432' }
  { name: 'DB_USERNAME', value: '{username}' }
  { name: 'DB_PASSWORD', secretRef: 'db-password' }
  { name: 'DB_DATABASE', value: 'dify' }
  
  // Redis configuration (same as API/Worker)
  { name: 'REDIS_HOST', value: '{redis-hostname}' }
  { name: 'REDIS_PORT', value: '{redis-port}' }
  { name: 'REDIS_PASSWORD', secretRef: 'redis-password' }
  { name: 'REDIS_USE_SSL', value: 'true' }
  
  // Storage configuration (same as API/Worker)
  { name: 'STORAGE_TYPE', value: 'azure-blob' }
  { name: 'AZURE_BLOB_ACCOUNT_NAME', value: '{storage-account-name}' }
  { name: 'AZURE_BLOB_ACCOUNT_KEY', secretRef: 'storage-key' }
  { name: 'AZURE_BLOB_CONTAINER_NAME', value: 'dify-app-storage' }
  { name: 'AZURE_BLOB_ACCOUNT_URL', value: 'https://{storage-account-name}.blob.core.windows.net' }
  
  // Secret key (same as API/Worker)
  { name: 'SECRET_KEY', secretRef: 'secret-key' }
  
  // Log level
  { name: 'LOG_LEVEL', value: 'INFO' }
]
```

**Notes**:
- Worker Beat must run as a single instance to avoid duplicate scheduled tasks
- No ingress is required as it only communicates with Redis

## Data Models

### New Secrets in Key Vault

```typescript
interface NewSecrets {
  'sandbox-api-key': string;           // Sandbox authentication key
  'plugin-daemon-key': string;         // Plugin Daemon server key
  'plugin-inner-api-key': string;      // Plugin Daemon <-> API communication key
}
```

### New Blob Storage Container

```typescript
interface NewBlobContainers {
  'dify-plugins': {
    purpose: 'Plugin package storage';
    access: 'Private';
    lifecycle: 'Retain';
  }
}
```

### New PostgreSQL Database

```typescript
interface NewDatabases {
  'dify_plugin': {
    purpose: 'Plugin metadata and configuration';
    owner: 'plugin_daemon';
    schema: 'Managed by Plugin Daemon';
  }
}
```


## Error Handling

### Sandbox Container Errors

**Error**: Sandbox container fails to start
- **Cause**: Invalid API key or network configuration
- **Solution**: Verify `sandbox-api-key` secret and SSRF Proxy connectivity
- **Logging**: Check Container App logs for authentication errors

**Error**: Code execution timeout
- **Cause**: `WORKER_TIMEOUT` too low or code execution taking too long
- **Solution**: Increase `WORKER_TIMEOUT` or optimize code
- **Logging**: Sandbox logs will show timeout errors

### SSRF Proxy Errors

**Error**: SSRF Proxy denies legitimate requests
- **Cause**: Overly restrictive Squid ACL configuration
- **Solution**: Review and adjust `squid.conf` ACL rules
- **Logging**: Squid access logs will show denied requests

**Error**: Sandbox cannot reach external APIs
- **Cause**: SSRF Proxy not running or misconfigured
- **Solution**: Verify SSRF Proxy container status and configuration
- **Logging**: Check Sandbox logs for proxy connection errors

### Plugin Daemon Errors

**Error**: Plugin Daemon cannot connect to API
- **Cause**: Invalid `DIFY_INNER_API_KEY` or incorrect API URL
- **Solution**: Verify `plugin-inner-api-key` secret and API FQDN
- **Logging**: Plugin Daemon logs will show API connection errors

**Error**: Plugin installation fails
- **Cause**: Storage configuration error or insufficient permissions
- **Solution**: Verify Azure Blob Storage connection string and container exists
- **Logging**: Plugin Daemon logs will show storage errors

**Error**: Plugin database migration fails
- **Cause**: `dify_plugin` database not created or insufficient permissions
- **Solution**: Manually create database or grant permissions
- **Logging**: Plugin Daemon startup logs will show migration errors

### Worker Beat Errors

**Error**: Scheduled tasks not executing
- **Cause**: Worker Beat container not running or Redis connection issue
- **Solution**: Verify Worker Beat container status and Redis connectivity
- **Logging**: Worker Beat logs will show scheduler errors

**Error**: Duplicate task execution
- **Cause**: Multiple Worker Beat instances running
- **Solution**: Ensure `minReplicas` and `maxReplicas` are both set to 1
- **Logging**: Check for multiple Worker Beat container instances


## Testing Strategy

### Unit Testing

**Bicep Template Validation**:
```bash
# Validate Bicep templates
az bicep build --file bicep/main/modules/sandboxContainerApp.bicep
az bicep build --file bicep/main/modules/ssrfProxyContainerApp.bicep
az bicep build --file bicep/main/modules/pluginDaemonContainerApp.bicep
az bicep build --file bicep/main/main.bicep
```

**Parameter Validation**:
```bash
# Validate parameter files
az deployment group validate \
  --resource-group dify-dev-rg \
  --template-file bicep/main/main.bicep \
  --parameters bicep/main/parameters/dev.bicepparam
```

### Integration Testing

**Container Connectivity Tests**:
```bash
# Test Sandbox connectivity from API container
az containerapp exec \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --command "curl -f http://dify-dev-sandbox.internal.{domain}:8194/health"

# Test SSRF Proxy connectivity from Sandbox
az containerapp exec \
  --name dify-dev-sandbox \
  --resource-group dify-dev-rg \
  --command "curl -x http://dify-dev-ssrf-proxy.internal.{domain}:3128 https://api.github.com"

# Test Plugin Daemon connectivity from API container
az containerapp exec \
  --name dify-dev-api \
  --resource-group dify-dev-rg \
  --command "curl -f http://dify-dev-plugin-daemon.internal.{domain}:5002/health"
```

**Database Connectivity Tests**:
```bash
# Verify Plugin Daemon database
az postgres flexible-server db show \
  --resource-group dify-dev-rg \
  --server-name {postgres-server} \
  --database-name dify_plugin
```

**Storage Tests**:
```bash
# Verify plugin storage container
az storage container show \
  --name dify-plugins \
  --account-name {storage-account}
```

### Functional Testing

**Sandbox Code Execution Test**:
1. Create a workflow with a code execution node
2. Execute Python code: `print("Hello from Sandbox")`
3. Verify output in workflow execution logs
4. Expected: Code executes successfully without errors

**SSRF Protection Test**:
1. Create a workflow with HTTP request node
2. Attempt to access private IP: `http://169.254.169.254/metadata`
3. Verify request is blocked by SSRF Proxy
4. Expected: Request denied with SSRF protection error

**Plugin Installation Test**:
1. Access Dify plugin marketplace
2. Install a sample plugin
3. Verify plugin appears in installed plugins list
4. Expected: Plugin installs successfully and is usable

**Scheduled Task Test**:
1. Enable a scheduled task (e.g., log cleanup)
2. Wait for scheduled execution time
3. Verify task executes via Worker Beat logs
4. Expected: Task executes on schedule without errors

### Performance Testing

**Sandbox Load Test**:
- Concurrent code executions: 10-50
- Expected response time: < 5 seconds
- Expected success rate: > 99%

**SSRF Proxy Load Test**:
- Concurrent proxy requests: 100-500
- Expected response time: < 1 second
- Expected success rate: > 99.9%

**Plugin Daemon Load Test**:
- Concurrent plugin operations: 5-20
- Expected response time: < 10 seconds
- Expected success rate: > 95%


## Deployment Strategy

### Phase 1: Infrastructure Preparation

1. **Create SSRF Proxy Configuration**
   - Create `docker/ssrf_proxy/squid.conf.template`
   - Create `docker/ssrf_proxy/Dockerfile` (if custom image needed)
   - Build and push to ACR (if custom image)

2. **Update Storage Account**
   - Create new blob container: `dify-plugins`
   - Set appropriate access policies

3. **Update PostgreSQL**
   - Create new database: `dify_plugin`
   - Grant permissions to admin user

4. **Generate Secrets**
   - Generate `sandbox-api-key`: `openssl rand -base64 32`
   - Generate `plugin-daemon-key`: `openssl rand -base64 42`
   - Generate `plugin-inner-api-key`: `openssl rand -base64 42`

### Phase 2: Bicep Module Development

1. **Create Sandbox Module**
   - File: `bicep/main/modules/sandboxContainerApp.bicep`
   - Implement container configuration
   - Add health check configuration

2. **Create SSRF Proxy Module**
   - File: `bicep/main/modules/ssrfProxyContainerApp.bicep`
   - Implement container configuration
   - Add volume mount for Squid config (if needed)

3. **Create Plugin Daemon Module**
   - File: `bicep/main/modules/pluginDaemonContainerApp.bicep`
   - Implement container configuration
   - Add database and storage configuration

4. **Update Main Orchestration**
   - File: `bicep/main/main.bicep`
   - Add new module deployments
   - Add dependency management
   - Add outputs for new container FQDNs

### Phase 3: Update Existing Containers

1. **Update API Container**
   - Add `CODE_EXECUTION_ENDPOINT` environment variable
   - Add `SSRF_PROXY_HTTP_URL` and `SSRF_PROXY_HTTPS_URL`
   - Add `PLUGIN_DAEMON_URL` environment variable
   - Add `SANDBOX_API_KEY` secret reference

2. **Update Worker Container**
   - Add same environment variables as API container
   - Ensure consistency with API configuration

3. **Update Parameter Files**
   - Add new parameters to `dev.bicepparam`
   - Add new parameters to `prod.bicepparam`
   - Set appropriate default values

### Phase 4: Deployment Execution

1. **Deploy to Development Environment**
   ```bash
   bash scripts/deploy.sh \
     --environment dev \
     --resource-group dify-dev-rg \
     --location japaneast
   ```

2. **Verify Deployment**
   - Check all containers are running
   - Verify internal connectivity
   - Run integration tests

3. **Deploy to Production Environment**
   ```bash
   bash scripts/deploy.sh \
     --environment prod \
     --resource-group dify-prod-rg \
     --location japaneast
   ```

### Phase 5: Post-Deployment Validation

1. **Functional Validation**
   - Test code execution in workflows
   - Test plugin installation
   - Test scheduled tasks
   - Verify SSRF protection

2. **Performance Validation**
   - Monitor container resource usage
   - Check response times
   - Verify auto-scaling behavior

3. **Documentation Update**
   - Update architecture diagrams
   - Update deployment guide
   - Add troubleshooting section

## Rollback Strategy

### Rollback Triggers

- New containers fail to start
- Existing functionality breaks
- Performance degradation > 20%
- Critical errors in logs

### Rollback Procedure

1. **Immediate Rollback**
   ```bash
   # Revert to previous Bicep deployment
   az deployment group create \
     --name "rollback-$(date +%Y%m%d-%H%M%S)" \
     --resource-group dify-dev-rg \
     --template-file bicep/main/main.bicep \
     --parameters bicep/main/parameters/dev.bicepparam.backup
   ```

2. **Partial Rollback**
   - Scale new containers to 0 replicas
   - Remove environment variables from API/Worker
   - Keep infrastructure for future retry

3. **Complete Rollback**
   - Delete new Container Apps
   - Remove new blob container
   - Remove new database
   - Restore previous configuration

## Migration Path for Existing Deployments

### Step 1: Backup Current Configuration

```bash
# Export current deployment
az deployment group export \
  --resource-group dify-dev-rg \
  --name {current-deployment-name} \
  > backup-deployment.json

# Backup parameter file
cp bicep/main/parameters/dev.bicepparam \
   bicep/main/parameters/dev.bicepparam.backup
```

### Step 2: Update Bicep Templates

```bash
# Pull latest changes
git pull origin main

# Review changes
git diff HEAD~1 bicep/main/
```

### Step 3: Update Parameters

```bash
# Edit parameter file
nano bicep/main/parameters/dev.bicepparam

# Add new parameters:
# - sandboxImage
# - ssrfProxyImage
# - pluginDaemonImage
# - sandboxApiKey
# - pluginDaemonKey
# - pluginInnerApiKey
```

### Step 4: Deploy Updates

```bash
# Validate first
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --what-if

# Deploy
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-dev-rg \
  --location japaneast
```

### Step 5: Verify Migration

```bash
# Check all containers
az containerapp list \
  --resource-group dify-dev-rg \
  --query "[].{Name:name, Status:properties.runningStatus}" \
  --output table

# Test functionality
# (Run integration tests)
```

## Security Considerations

### Secret Management

- All sensitive keys stored in Container Apps secrets
- Secrets rotated regularly (recommended: every 90 days)
- No secrets in environment variables (use secretRef)
- Key Vault integration for centralized secret management (future enhancement)

### Network Security

- All new containers use internal-only ingress
- SSRF Proxy blocks access to private IP ranges
- Sandbox network access controlled via proxy
- No direct internet access from Sandbox

### Container Security

- Use official images from trusted sources
- Regular image updates for security patches
- Minimal container privileges
- Read-only file systems where possible

### Access Control

- Managed Identity for Azure resource access
- RBAC for Container Apps management
- API key authentication between containers
- No shared secrets between environments

## Monitoring and Observability

### Metrics to Monitor

**Sandbox**:
- Code execution count
- Execution duration (p50, p95, p99)
- Error rate
- Resource usage (CPU, memory)

**SSRF Proxy**:
- Request count
- Blocked request count
- Response time
- Cache hit rate

**Plugin Daemon**:
- Plugin installation count
- Plugin execution count
- Error rate
- Database connection pool usage

**Worker Beat**:
- Scheduled task execution count
- Task execution duration
- Missed schedule count
- Error rate

### Logging Strategy

**Log Aggregation**:
- All containers send logs to Log Analytics Workspace
- Structured logging with JSON format
- Correlation IDs for request tracing

**Log Retention**:
- Development: 30 days
- Production: 90 days

**Alert Rules**:
- Container restart count > 3 in 5 minutes
- Error rate > 5% for 5 minutes
- Response time > 10 seconds for 5 minutes
- Scheduled task missed > 2 consecutive times

### Dashboard

**Key Metrics Dashboard**:
- Container health status
- Request rate and latency
- Error rate trends
- Resource utilization
- Cost tracking

## Cost Optimization

### Development Environment

**Auto-scaling Configuration**:
- Sandbox: min 0, max 5
- SSRF Proxy: min 0, max 3
- Plugin Daemon: min 0, max 5
- Worker Beat: min 1, max 1 (always running)

**Estimated Monthly Cost**:
- Sandbox: ~$0-30 (usage-based)
- SSRF Proxy: ~$0-15 (usage-based)
- Plugin Daemon: ~$0-60 (usage-based)
- Worker Beat: ~$30-40 (always running)
- **Total**: ~$30-145/month

### Production Environment

**Auto-scaling Configuration**:
- Sandbox: min 1, max 10
- SSRF Proxy: min 1, max 5
- Plugin Daemon: min 1, max 10
- Worker Beat: min 1, max 1

**Estimated Monthly Cost**:
- Sandbox: ~$60-300
- SSRF Proxy: ~$30-75
- Plugin Daemon: ~$120-600
- Worker Beat: ~$30-40
- **Total**: ~$240-1,015/month

### Cost Reduction Strategies

1. **Use spot instances** (if available for Container Apps)
2. **Implement aggressive auto-scaling** in dev environment
3. **Use reserved capacity** for production (if available)
4. **Monitor and optimize resource allocation** based on actual usage
5. **Implement caching** to reduce compute requirements

## Future Enhancements

### Phase 2 Features

1. **Custom Sandbox Image**
   - Pre-installed Python packages
   - Optimized for faster startup
   - Reduced image size

2. **SSRF Proxy Enhancements**
   - Advanced filtering rules
   - Request logging and analytics
   - Rate limiting per source

3. **Plugin Daemon Improvements**
   - Plugin marketplace integration
   - Automatic plugin updates
   - Plugin performance monitoring

4. **Worker Beat Enhancements**
   - Dynamic task scheduling
   - Task priority management
   - Task execution history

### Phase 3 Features

1. **High Availability**
   - Multi-region deployment
   - Active-active configuration
   - Automatic failover

2. **Advanced Monitoring**
   - Distributed tracing
   - Custom metrics
   - Predictive alerting

3. **Security Enhancements**
   - Container image scanning
   - Runtime security monitoring
   - Automated vulnerability patching

4. **Performance Optimization**
   - Connection pooling
   - Request caching
   - Load balancing optimization
