# Requirements Document

## Introduction

このドキュメントは、Dify on Azureデプロイメントに不足している重要なコンテナ（sandbox、ssrf_proxy、plugin_daemon、worker_beat）を追加する機能の要件を定義します。これらのコンテナは、Difyの完全な機能（コード実行、セキュリティ、プラグインシステム、定期タスク）を提供するために必要です。

## Glossary

- **System**: Dify on Azure Infrastructure（Azure Container Apps上で動作するDifyプラットフォーム）
- **Sandbox**: コード実行を安全に行うための隔離された環境を提供するコンテナ
- **SSRF Proxy**: Server-Side Request Forgery攻撃を防ぐためのプロキシサーバー
- **Plugin Daemon**: Difyプラグインの管理と実行を担当するデーモンプロセス
- **Worker Beat**: Celery Beatスケジューラーで定期タスクを実行するコンテナ
- **Container App**: Azure Container Appsで実行されるコンテナアプリケーション
- **Internal Network**: Container Apps Environment内の内部ネットワーク

## Requirements

### Requirement 1: Sandbox Container Deployment

**User Story:** インフラ管理者として、ユーザーがワークフロー内でPythonコードを安全に実行できるように、Sandboxコンテナをデプロイしたい

#### Acceptance Criteria

1. THE System SHALL deploy a Container App named `dify-{environment}-sandbox` using the image `langgenius/dify-sandbox:0.2.12`
2. THE System SHALL configure the Sandbox Container App to expose port 8194 for internal communication
3. THE System SHALL set the environment variable `API_KEY` with a secure value for Sandbox authentication
4. THE System SHALL set the environment variable `ENABLE_NETWORK` to `true` to allow network access from sandbox
5. THE System SHALL configure the Sandbox Container App to use the SSRF Proxy for HTTP and HTTPS requests via environment variables `HTTP_PROXY` and `HTTPS_PROXY`

### Requirement 2: SSRF Proxy Container Deployment

**User Story:** セキュリティ管理者として、SSRF攻撃を防ぐために、すべての外部HTTPリクエストをフィルタリングするSSRF Proxyをデプロイしたい

#### Acceptance Criteria

1. THE System SHALL deploy a Container App named `dify-{environment}-ssrf-proxy` using the image `ubuntu/squid:latest`
2. THE System SHALL configure the SSRF Proxy Container App to expose port 3128 for internal proxy communication
3. THE System SHALL mount a custom Squid configuration file to `/etc/squid/squid.conf` in the SSRF Proxy container
4. THE System SHALL configure the SSRF Proxy to allow connections from Sandbox and API containers
5. WHEN reverse proxying to Sandbox is required, THE System SHALL set the environment variable `REVERSE_PROXY_PORT` to `8194`; otherwise the reverse proxy block SHALL be disabled while keeping the forward-proxy ACLs active

### Requirement 3: Plugin Daemon Container Deployment

**User Story:** プラットフォーム管理者として、ユーザーがDifyプラグインをインストールして使用できるように、Plugin Daemonコンテナをデプロイしたい

#### Acceptance Criteria

1. THE System SHALL deploy a Container App named `dify-{environment}-plugin-daemon` using the image `langgenius/dify-plugin-daemon:0.4.0`
2. THE System SHALL configure the Plugin Daemon Container App to expose port 5002 for API communication
3. THE System SHALL configure the Plugin Daemon Container App to expose port 5003 for remote debugging
4. THE System SHALL set the environment variable `SERVER_KEY` with a secure authentication key
5. THE System SHALL configure the Plugin Daemon to connect to the same PostgreSQL database with a separate database name `dify_plugin`
6. THE System SHALL set the environment variable `DIFY_INNER_API_URL` to point to the API Container App internal FQDN
7. THE System SHALL configure the Plugin Daemon to use Azure Blob Storage for plugin storage via environment variables

### Requirement 4: Worker Beat Container Deployment

**User Story:** システム管理者として、定期的なメンテナンスタスク（ログクリーンアップ、データベースバックアップなど）を自動実行するために、Worker Beatコンテナをデプロイしたい

#### Acceptance Criteria

1. THE System SHALL deploy a Container App named `dify-{environment}-worker-beat` using the same image as the API container
2. THE System SHALL set the environment variable `MODE` to `beat` to start Celery Beat scheduler
3. THE System SHALL configure the Worker Beat Container App with the same database and Redis connection settings as the API and Worker containers
4. THE System SHALL configure the Worker Beat Container App to not expose any ingress ports
5. THE System SHALL set minimum replicas to 1 to ensure the scheduler is always running

### Requirement 5: Network Configuration

**User Story:** ネットワーク管理者として、新しいコンテナが既存のコンテナと安全に通信できるように、内部ネットワーク設定を構成したい

#### Acceptance Criteria

1. WHEN deploying new containers, THE System SHALL configure all containers with internal-only ingress
2. THE System SHALL configure API and Worker containers to use the Sandbox internal FQDN via environment variable `CODE_EXECUTION_ENDPOINT`
3. THE System SHALL configure API and Worker containers to use the SSRF Proxy via environment variables `SSRF_PROXY_HTTP_URL` and `SSRF_PROXY_HTTPS_URL`
4. THE System SHALL configure API and Worker containers to use the Plugin Daemon via environment variable `PLUGIN_DAEMON_URL`
5. THE System SHALL ensure all internal communication uses the Container Apps Environment default domain

### Requirement 6: Security Configuration

**User Story:** セキュリティ管理者として、新しいコンテナが安全に動作し、機密情報が適切に保護されるように、セキュリティ設定を構成したい

#### Acceptance Criteria

1. THE System SHALL store all sensitive keys (Sandbox API key, Plugin Daemon server key) as secrets in Container Apps
2. THE System SHALL configure the Sandbox Container App to use a unique API key that matches the API container configuration
3. THE System SHALL configure the Plugin Daemon to use a unique server key for authentication
4. THE System SHALL configure the Plugin Daemon to use a separate inner API key for communication with the API container
5. THE System SHALL ensure all secrets are referenced via `secretRef` in environment variables

### Requirement 7: Resource Allocation

**User Story:** コスト管理者として、新しいコンテナが適切なリソースを使用し、環境に応じてスケーリングできるように、リソース設定を構成したい

#### Acceptance Criteria

1. THE System SHALL allocate 0.5 CPU and 1.0Gi memory to the Sandbox Container App
2. THE System SHALL allocate 0.25 CPU and 0.5Gi memory to the SSRF Proxy Container App
3. THE System SHALL allocate 1.0 CPU and 2.0Gi memory to the Plugin Daemon Container App
4. THE System SHALL allocate 0.5 CPU and 1.0Gi memory to the Worker Beat Container App
5. WHEN environment is `dev`, THE System SHALL set minimum replicas to 0 for Sandbox, SSRF Proxy, and Plugin Daemon to reduce costs
6. WHEN environment is `prod`, THE System SHALL set minimum replicas to 1 for all new containers to ensure availability

### Requirement 8: Bicep Module Structure

**User Story:** 開発者として、新しいコンテナを既存のBicepテンプレートに統合し、保守性を維持したい

#### Acceptance Criteria

1. THE System SHALL create reusable Bicep modules for each new container type in `bicep/main/modules/` directory
2. THE System SHALL update the main orchestration file `bicep/main/main.bicep` to deploy all new containers
3. THE System SHALL add new container image parameters to the parameter files (`dev.bicepparam`, `prod.bicepparam`)
4. THE System SHALL ensure all new modules follow the existing naming convention and structure
5. THE System SHALL add outputs for new container FQDNs to the main Bicep file

### Requirement 9: Documentation Updates

**User Story:** ドキュメント管理者として、新しいコンテナの追加に関する情報をドキュメントに反映したい

#### Acceptance Criteria

1. THE System SHALL update `docs/architecture-overview.md` to include the new containers in the architecture diagram
2. THE System SHALL update `docs/deployment-guide.md` to include deployment instructions for the new containers
3. THE System SHALL update `README.md` to reflect the complete container list
4. THE System SHALL document the purpose and configuration of each new container
5. THE System SHALL provide troubleshooting guidance for common issues with the new containers

### Requirement 10: Backward Compatibility

**User Story:** 既存ユーザーとして、新しいコンテナの追加が既存のデプロイメントに影響を与えないようにしたい

#### Acceptance Criteria

1. THE System SHALL ensure existing Container Apps (web, api, worker, nginx) continue to function without modification
2. THE System SHALL provide default values for all new parameters to maintain backward compatibility
3. THE System SHALL update existing API and Worker containers to use new services only after they are successfully deployed
4. THE System SHALL ensure the deployment script handles the new containers gracefully
5. THE System SHALL provide a migration guide for existing deployments
