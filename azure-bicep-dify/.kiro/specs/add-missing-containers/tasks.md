# 実装計画

- [x] 1. インフラストラクチャと設定ファイルの準備

  - SSRF Proxy Squid設定ファイルの作成
  - プラグイン用の新しいBlobストレージコンテナの作成
  - Plugin Daemon用の新しいPostgreSQLデータベースの作成
  - 新しいコンテナ用のセキュリティキーの生成
  - _要件: 2.3, 2.4, 3.5, 6.1, 6.2, 6.3_

- [x] 1.1 SSRF Proxy Squid設定の作成



  - SSRF保護用のACLルールを含む`docker/ssrf_proxy/squid.conf.template`を作成
  - プライベートIPレンジ（10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8）へのアクセスをブロックするフォワードプロキシを設定
  - サンドボックスをリバース公開したい場合にのみ、ポート8194でSandboxへのリバースプロキシを有効化し、不要な環境では無効化手順を文書化
  - _要件: 2.3, 2.4_

- [x] 1.2 Plugin Daemonルーティング用のnginx設定の更新



  - `docker/nginx/default.conf.template` を公式テンプレートに合わせて更新し、`/e/` を `proxy_pass http://plugin_daemon:5002;` でルーティングする
  - `Dify-Hook-Url` ヘッダーなど既定のヘッダー設定を維持する
  - `proxy_params` を通じて SSE 対応タイムアウトを確保する
  - _要件: 3.2, 5.4_

- [x] 1.3 ストレージコンテナとデータベースの作成


  - storageモジュールに`dify-plugins` Blobコンテナ作成を追加
  - PostgreSQLデータベースの手動作成を文書化: `CREATE DATABASE dify_plugin;`
  - _要件: 3.5_

- [x] 1.4 セキュリティキーの生成と文書化

  - sandbox-api-keyを生成するコマンドを文書化: `openssl rand -base64 32`
  - plugin-daemon-keyを生成するコマンドを文書化: `openssl rand -base64 42`
  - plugin-inner-api-keyを生成するコマンドを文書化: `openssl rand -base64 42`
  - _要件: 6.1, 6.2, 6.3_


- [x] 2. 新しいコンテナ用のBicepモジュールの作成

  - Sandbox、SSRF Proxy、Plugin Daemon用の再利用可能なBicepモジュールを作成
  - 適切なリソース割り当てでコンテナ設定を実装
  - 環境変数とシークレットを設定
  - _要件: 1.1-1.5, 2.1-2.5, 3.1-3.7, 7.1-7.6, 8.1-8.4_

- [x] 2.1 Sandbox Container Appモジュールの作成


  - `bicep/main/modules/sandboxContainerApp.bicep`を作成
  - イメージを設定: `langgenius/dify-sandbox:0.2.12`、ポート8194
  - CPU: 0.5、メモリ: 1.0Giを設定
  - 環境変数を追加: API_KEY, GIN_MODE, WORKER_TIMEOUT, ENABLE_NETWORK, HTTP_PROXY, HTTPS_PROXY, SANDBOX_PORT
  - 内部専用ingressを設定
  - 最小レプリカ: 0 (dev) / 1 (prod)、最大レプリカ: 5 (dev) / 10 (prod)を設定
  - _要件: 1.1-1.5, 7.1_

- [x] 2.2 SSRF Proxy Container Appモジュールの作成


  - `bicep/main/modules/ssrfProxyContainerApp.bicep`を作成
  - イメージを設定: `ubuntu/squid:latest`、ポート3128
  - CPU: 0.25、メモリ: 0.5Giを設定
  - 環境変数を追加: HTTP_PORT, COREDUMP_DIR, REVERSE_PROXY_PORT, SANDBOX_HOST, SANDBOX_PORT
  - 内部専用ingressを設定
  - 最小レプリカ: 0 (dev) / 1 (prod)、最大レプリカ: 3 (dev) / 5 (prod)を設定
  - _要件: 2.1-2.5, 7.2_

- [x] 2.3 Plugin Daemon Container Appモジュールの作成


  - `bicep/main/modules/pluginDaemonContainerApp.bicep`を作成
  - イメージを設定: `langgenius/dify-plugin-daemon:0.4.0`、ポート5002, 5003
  - CPU: 1.0、メモリ: 2.0Giを設定
  - `dify_plugin`データベース用のデータベース環境変数を追加
  - Redis環境変数を追加（API/Workerと同じ）
  - Plugin Daemon固有の変数を追加: SERVER_PORT, SERVER_KEY, DIFY_INNER_API_URL, DIFY_INNER_API_KEY
  - プラグインストレージ用のAzure Blob Storage変数を追加
  - ポート5002で内部専用ingressを設定
  - 最小レプリカ: 0 (dev) / 1 (prod)、最大レプリカ: 5 (dev) / 10 (prod)を設定
  - _要件: 3.1-3.7, 7.3_


- [x] 3. メインBicepオーケストレーションファイルの更新

  - 新しいコンテナをデプロイするために`bicep/main/main.bicep`を更新
  - 新しいコンテナイメージと設定用のパラメータを追加
  - デプロイメント依存関係を設定
  - 新しいコンテナFQDN用の出力を追加
  - _要件: 4.1-4.5, 5.1-5.5, 8.1-8.5_

- [x] 3.1 新しいコンテナ用のパラメータを追加


  - デフォルト`langgenius/dify-sandbox:0.2.12`で`sandboxImage`パラメータを追加
  - デフォルト`ubuntu/squid:latest`で`ssrfProxyImage`パラメータを追加
  - デフォルト`langgenius/dify-plugin-daemon:0.4.0`で`pluginDaemonImage`パラメータを追加
  - `sandboxApiKey`、`pluginDaemonKey`、`pluginInnerApiKey`のセキュアパラメータを追加
  - _要件: 8.3_

- [x] 3.2 既存のcontainerAppモジュールを使用してWorker Beatコンテナをデプロイ


  - `modules/containerApp.bicep`を使用してWorker Beatデプロイメントを追加
  - MODE環境変数を`beat`に設定
  - API/Workerと同じデータベース、Redis、ストレージ設定を構成
  - 最小レプリカ: 1、最大レプリカ: 1（単一インスタンス）を設定
  - ingressを無効化（外部アクセス不要）
  - _要件: 4.1-4.5, 7.4_

- [x] 3.3 Sandboxコンテナのデプロイ


  - SSRF Proxyへの依存関係を持つSandboxモジュールデプロイメントを追加
  - HTTP_PROXYとHTTPS_PROXY用にSSRF Proxy内部FQDNを渡す
  - sandbox-api-keyシークレットを設定
  - _要件: 1.1-1.5, 5.2_

- [x] 3.4 SSRF Proxyコンテナのデプロイ

  - SSRF Proxyモジュールデプロイメントを追加
  - リバースプロキシ設定用にSandbox内部FQDNを渡す
  - _要件: 2.1-2.5_

- [x] 3.5 Plugin Daemonコンテナのデプロイ

  - PostgreSQLとStorageへの依存関係を持つPlugin Daemonモジュールデプロイメントを追加
  - DIFY_INNER_API_URL用にAPI内部FQDNを渡す
  - plugin-daemon-keyとplugin-inner-api-keyシークレットを設定
  - プラグインストレージ用のAzure Blob Storage接続を設定
  - _要件: 3.1-3.7, 5.4_

- [x] 3.6 新しいコンテナ用の出力を追加


  - `sandboxFqdn`出力を追加
  - `ssrfProxyFqdn`出力を追加
  - `pluginDaemonFqdn`出力を追加
  - `workerBeatName`出力を追加
  - _要件: 8.5_


- [x] 4. 新しいサービスを使用するように既存のコンテナを更新

  - 新しい環境変数でAPIとWorkerコンテナを更新
  - Plugin Daemonルーティングでnginxコンテナを更新
  - 適切な依存関係管理を確保
  - _要件: 5.1-5.5, 10.1-10.3_

- [x] 4.1 APIコンテナの環境変数を更新


  - Sandbox内部FQDNを指す`CODE_EXECUTION_ENDPOINT`を追加（http://dify-{env}-sandbox.internal.{domain}:8194）
  - sandbox-api-keyへのシークレット参照`CODE_EXECUTION_API_KEY`を追加
  - SSRF Proxyを指す`SSRF_PROXY_HTTP_URL`を追加（http://dify-{env}-ssrf-proxy.internal.{domain}:3128）
  - SSRF Proxyを指す`SSRF_PROXY_HTTPS_URL`を追加（http://dify-{env}-ssrf-proxy.internal.{domain}:3128）
  - Plugin Daemonを指す`PLUGIN_DAEMON_URL`を追加（http://dify-{env}-plugin-daemon.internal.{domain}:5002）
  - plugin-inner-api-keyへのシークレット参照`INNER_API_KEY_FOR_PLUGIN`を追加
  - _要件: 5.2, 5.3, 5.4_

- [x] 4.2 Workerコンテナの環境変数を更新


  - Sandbox、SSRF Proxy、Plugin Daemon用にAPIコンテナと同じ環境変数を追加
  - API設定との一貫性を確保
  - _要件: 5.2, 5.3, 5.4_

- [x] 4.3 nginxコンテナ設定の更新

  - `docker/nginx/default.conf.template` を公式テンプレートと同等に保ち、`plugin_daemon:5002` などサービス名で直接ルーティングする
  - `proxy_params` のタイムアウトやヘッダー設定が Azure Container Apps の要件と一致しているか確認
  - _要件: 5.4_

- [x] 4.4 デプロイメント依存関係を更新


  - APIとWorkerがSandboxとSSRF Proxyのデプロイメントに依存することを確保
  - nginxがPlugin Daemonのデプロイメントに依存することを確保
  - 適切な起動順序を確保
  - _要件: 10.3_


- [x] 5. dev環境とprod環境用のパラメータファイルを更新

  - `bicep/main/parameters/dev.bicepparam`に新しいパラメータを追加
  - `bicep/main/parameters/prod.bicepparam`に新しいパラメータを追加
  - 適切なデフォルト値と環境固有の設定を設定
  - _要件: 8.3, 10.2_

- [x] 5.1 dev.bicepparamを更新


  - sandboxImage、ssrfProxyImage、pluginDaemonImageパラメータを追加
  - sandboxApiKey、pluginDaemonKey、pluginInnerApiKey用のプレースホルダーコメントを追加（生成予定）
  - コスト最適化のためcontainerAppMinReplicasを0に設定
  - _要件: 7.5, 8.3_

- [x] 5.2 prod.bicepparamを更新


  - 特定のバージョンでsandboxImage、ssrfProxyImage、pluginDaemonImageパラメータを追加
  - sandboxApiKey、pluginDaemonKey、pluginInnerApiKey用のプレースホルダーコメントを追加（生成予定）
  - 高可用性のためcontainerAppMinReplicasを1に設定
  - _要件: 7.6, 8.3_

- [x] 6. プラグインコンテナを作成するためにstorageモジュールを更新

  - `dify-plugins` Blobコンテナを作成するために`bicep/main/modules/storage.bicep`を変更
  - 適切なアクセスレベル（プライベート）を設定
  - _要件: 3.5_

- [x] 6.1 dify-pluginsコンテナ作成を追加

  - `dify-plugins`用のBlobコンテナリソースを追加
  - publicAccessを'None'に設定
  - storageモジュールの出力に追加
  - _要件: 3.5_


- [x] 7. ドキュメントの更新

  - 新しいコンテナでアーキテクチャ概要を更新
  - 新しいセットアップ手順でデプロイメントガイドを更新
  - 完全なコンテナリストでREADMEを更新
  - 新しいコンテナ用のトラブルシューティングセクションを追加
  - _要件: 9.1-9.5_

- [x] 7.1 docs/architecture-overview.mdを更新

  - アーキテクチャ図にSandbox、SSRF Proxy、Plugin Daemon、Worker Beatを追加
  - 各新しいコンテナの目的と設定を文書化
  - 新しいコンテナでリソースリストテーブルを更新
  - データフロー図を更新
  - _要件: 9.1, 9.4_

- [x] 7.2 docs/deployment-guide.mdを更新

  - dify_pluginデータベース作成用のデプロイ前手順を追加
  - セキュリティキー生成手順を追加
  - 新しいコンテナ用のデプロイ後検証手順を追加
  - 一般的な問題用のトラブルシューティングセクションを追加
  - _要件: 9.2, 9.5_

- [x] 7.3 README.mdを更新


  - 新しいコンテナを含むようにアーキテクチャ図を更新
  - プロジェクト構造のコンテナリストを更新
  - デプロイ時間の見積もりを更新
  - _要件: 9.3_

- [x] 7.4 既存デプロイメント用のマイグレーションガイドを作成

  - バックアップ手順を文書化
  - ステップバイステップのマイグレーションプロセスを文書化
  - ロールバック手順を文書化
  - _要件: 10.4, 10.5_


- [x] 8. nginx Container Appモジュールの確認

  - 既存モジュールで `DIFY_WEB_HOST` / `DIFY_API_HOST` のみを利用し、Plugin Daemon 用の追加環境変数が不要であることを確認
  - 外部ポート 80 経由で `plugin_daemon:5002` にリクエストが到達できることをテストで保証
  - _要件: 5.4_

- [x] 9. デプロイメントの検証とテスト


  - Bicepテンプレートを検証
  - 開発環境でデプロイメントをテスト
  - コンテナ接続を確認
  - 統合テストを実行
  - _要件: 10.1-10.5_

- [x] 9.1 Bicepテンプレートを検証

  - すべての新しいモジュールで`az bicep build`を実行
  - main.bicepで`az deployment group validate`を実行
  - 検証エラーを修正
  - _要件: 10.1_

- [x] 9.2 開発環境にデプロイ

  - devパラメータでデプロイメントスクリプトを実行
  - デプロイメントの進行状況を監視
  - エラーを確認
  - _要件: 10.1_

- [x] 9.3 コンテナステータスを確認

  - すべてのコンテナがRunning状態であることを確認
  - 内部FQDNが正しく設定されていることを確認
  - 環境変数が正しく設定されていることを確認
  - _要件: 10.1_

- [x] 9.4 コンテナ接続をテスト

  - APIコンテナからSandbox接続をテスト
  - SandboxからSSRF Proxy接続をテスト
  - APIコンテナからPlugin Daemon接続をテスト
  - Worker BeatからRedis接続をテスト
  - _要件: 10.1_

- [x] 9.5 機能テストを実行

  - ワークフローでコード実行をテスト（Sandbox）
  - SSRF保護をテスト（SSRF Proxy）
  - プラグインインストールをテスト（Plugin Daemon）
  - スケジュールされたタスク実行をテスト（Worker Beat）
  - _要件: 10.1_
