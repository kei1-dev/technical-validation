# 設計ドキュメント

## 概要

このドキュメントは、ACRとnginxコンテナのデプロイをメインBicepテンプレートから分離するための設計を定義します。分離により、デプロイプロセスが3つの明確なフェーズに分かれます：

1. **フェーズ1**: ACRインフラストラクチャのデプロイ
2. **フェーズ2**: カスタムnginxコンテナのビルドとACRへのプッシュ
3. **フェーズ3**: メインインフラストラクチャのデプロイ（ACRとnginxイメージを参照）

この設計により、Container Appsがデプロイされる前にnginxコンテナがACRで利用可能になることが保証されます。

## アーキテクチャ

### 現在のアーキテクチャ

```
deploy.sh
  └─> main.bicep
       ├─> acr.bicep (ACRモジュール)
       ├─> nginxContainerApp.bicep (nginxイメージパラメータを使用)
       └─> その他のモジュール...

問題点：
- ACRとnginxコンテナアプリが同じテンプレート内にある
- nginxイメージがACRにプッシュされる前にContainer Appがデプロイされる可能性がある
- デプロイの順序制御が困難
```

### 新しいアーキテクチャ

```
deploy.sh (更新版)
  ├─> フェーズ1: acr-only.bicep
  │    └─> acr.bicep (ACRモジュール)
  │         └─> 出力: acrName, acrLoginServer
  │
  ├─> フェーズ2: build-and-push-nginx.sh
  │    └─> ACRにログイン
  │    └─> nginxイメージをビルド
  │    └─> ACRにプッシュ
  │    └─> 出力: nginxImageUrl
  │
  └─> フェーズ3: main.bicep (更新版)
       ├─> 入力: acrName (オプション), nginxImage (必須)
       ├─> nginxContainerApp.bicep (nginxImageを使用)
       └─> その他のモジュール...

利点：
- 明確な3段階のデプロイフロー
- nginxイメージがContainer Appデプロイ前に確実に利用可能
- 各フェーズでのエラーハンドリングが容易
- ACRとメインインフラの独立したライフサイクル管理
```

## コンポーネントと インターフェース

### 1. ACR専用Bicepテンプレート (`bicep/acr-only/main.bicep`)

**目的**: ACRリソースのみをデプロイする

**フォルダ構成**:
```
bicep/
├── acr-only/
│   ├── main.bicep           # ACRデプロイのメインテンプレート
│   ├── modules/
│   │   └── acr.bicep        # ACRモジュール（既存のものをコピー）
│   └── parameters/
│       ├── dev.bicepparam   # 開発環境パラメータ
│       └── prod.bicepparam  # 本番環境パラメータ
└── main/
    ├── main.bicep           # メインインフラのテンプレート（既存のmain.bicep）
    ├── modules/             # 既存のモジュール
    └── parameters/          # 既存のパラメータ
```

**入力パラメータ**:
```bicep
param environment string  // 'dev' または 'prod'
param location string     // Azureリージョン
param tags object         // リソースタグ
```

**出力**:
```bicep
output acrName string           // ACR名
output acrLoginServer string    // ACRログインサーバーURL
```

**実装詳細**:
- 既存の `bicep/modules/acr.bicep` を `bicep/acr-only/modules/acr.bicep` にコピー
- メインテンプレートと同じ命名規則を使用
- 管理者ユーザーを有効化（スクリプトからのプッシュ用）

### 2. メインインフラのBicepテンプレート (`bicep/main/main.bicep`)

**フォルダ移動**:
- 既存の `bicep/main.bicep` を `bicep/main/main.bicep` に移動
- 既存の `bicep/modules/` を `bicep/main/modules/` に移動
- 既存の `bicep/parameters/` を `bicep/main/parameters/` に移動

**変更点**:

**削除する内容**:
```bicep
// このモジュールデプロイを削除
module acr 'modules/acr.bicep' = {
  name: 'acr-deployment'
  params: { ... }
}
```

**追加する内容**:
```bicep
// 新しいパラメータ（すべて必須）
@description('ACR name for container registry')
param acrName string

@description('ACR login server URL')
param acrLoginServer string

@description('ACR admin username')
param acrAdminUsername string

@description('ACR admin password')
@secure()
param acrAdminPassword string

@description('nginx container image from ACR')
param nginxImage string
```

**更新する内容**:
```bicep
// nginxImageパラメータとACR認証情報を使用するように更新
module containerAppNginx 'modules/nginxContainerApp.bicep' = {
  params: {
    nginxImage: nginxImage  // パラメータから渡される
    acrLoginServer: acrLoginServer
    acrAdminUsername: acrAdminUsername
    acrAdminPassword: acrAdminPassword
    // その他のパラメータ...
  }
}

// ACR出力を削除
// output acrName string = acr.outputs.acrName  // 削除
// output acrLoginServer string = acr.outputs.acrLoginServer  // 削除
```

### 3. 更新されたデプロイスクリプト (`scripts/deploy.sh`)

**新しいフロー**:

```bash
# フェーズ1: ACRデプロイ
print_header "Phase 1: Deploy ACR"
az deployment group create \
  --name "acr-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$PROJECT_ROOT/bicep/acr-only/main.bicep" \
  --parameters "$PROJECT_ROOT/bicep/acr-only/parameters/${ENVIRONMENT}.bicepparam"

# ACR情報を取得
ACR_NAME=$(az deployment group show ... --query 'properties.outputs.acrName.value' -o tsv)
ACR_LOGIN_SERVER=$(az deployment group show ... --query 'properties.outputs.acrLoginServer.value' -o tsv)

# フェーズ2: nginxコンテナのビルドとプッシュ
print_header "Phase 2: Build and Push nginx Container"
bash "$SCRIPT_DIR/build-and-push-nginx.sh" \
  --resource-group "$RESOURCE_GROUP" \
  --acr-name "$ACR_NAME"

# nginxイメージURLを構築
NGINX_IMAGE_URL="${ACR_LOGIN_SERVER}/dify-nginx:latest"

# ACR認証情報を取得（Container Appsでの認証用）
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query 'username' -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query 'passwords[0].value' -o tsv)

# フェーズ3: メインインフラストラクチャのデプロイ
print_header "Phase 3: Deploy Main Infrastructure"
az deployment group create \
  --name "main-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$PROJECT_ROOT/bicep/main/main.bicep" \
  --parameters "$PROJECT_ROOT/bicep/main/parameters/${ENVIRONMENT}.bicepparam" \
  --parameters acrName="$ACR_NAME" \
  --parameters acrLoginServer="$ACR_LOGIN_SERVER" \
  --parameters acrAdminUsername="$ACR_USERNAME" \
  --parameters acrAdminPassword="$ACR_PASSWORD" \
  --parameters nginxImage="$NGINX_IMAGE_URL"
```

**エラーハンドリング**:
- 各フェーズの後に終了コードをチェック
- 失敗時は明確なエラーメッセージを表示して停止
- 各フェーズの成功/失敗をログに記録

### 4. 更新されたnginx Container Appモジュール (`bicep/modules/nginxContainerApp.bicep`)

**変更点**:

**追加するパラメータ（すべて必須）**:
```bicep
@description('ACR login server URL')
param acrLoginServer string

@description('ACR admin username')
param acrAdminUsername string

@description('ACR admin password')
@secure()
param acrAdminPassword string
```

**更新する内容**:
```bicep
resource nginxContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  properties: {
    configuration: {
      // ACR認証情報を追加（必須）
      secrets: [
        {
          name: 'acr-password'
          value: acrAdminPassword
        }
      ]
      registries: [
        {
          server: acrLoginServer
          username: acrAdminUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      // その他の設定...
    }
  }
}
```

**重要な変更**:
- ACR認証情報は必須パラメータ（デフォルト値なし）
- ACRなしでのデプロイは不可

### 5. 更新されたビルドスクリプト (`scripts/build-and-push-nginx.sh`)

**変更点**:

**現在の実装**:
- リソースグループからACR名を取得
- ACRにログイン
- イメージをビルドしてプッシュ

**必要な更新**:
- ACR名を必須パラメータとして受け入れる（デプロイ出力から渡される）
- イメージURLを標準出力に出力（スクリプトから取得可能にする）
- エラーハンドリングの改善

**新しいインターフェース**:
```bash
# 使用方法
./build-and-push-nginx.sh --acr-name <acr-name>

# 出力
# 標準出力: <acr-login-server>/dify-nginx:latest
# 終了コード: 0 (成功) または 1 (失敗)
```

### 5. パラメータファイルの更新

**ACRパラメータファイル (`bicep/acr-only/parameters/dev.bicepparam` と `prod.bicepparam`)**:

**新規作成**:
```bicep
using '../main.bicep'

param environment = 'dev'  // または 'prod'
param location = 'japaneast'
param tags = {
  Environment: 'Development'  // または 'Production'
  Project: 'Dify'
  ManagedBy: 'Bicep'
}
```

**メインパラメータファイル (`bicep/main/parameters/dev.bicepparam` と `prod.bicepparam`)**:

**削除する内容**:
- 既存のnginxImageパラメータ（存在する場合）
- ACR関連のパラメータ（存在する場合）

**重要な変更**:
- ACR関連のパラメータ（acrName, acrLoginServer, acrAdminUsername, acrAdminPassword, nginxImage）はパラメータファイルに含めない
- これらの値はデプロイスクリプトによってコマンドライン引数として渡される
- パラメータファイルには他のインフラストラクチャパラメータのみを含める

**理由**:
- ACR情報はフェーズ1のデプロイ出力から動的に取得される
- パラメータファイルに固定値を書くと、環境間での不整合が発生する可能性がある
- セキュリティ: ACR管理者パスワードをファイルに保存しない

## データモデル

### デプロイ状態の管理

デプロイスクリプトは、各フェーズの状態を追跡します：

```bash
# 状態変数
ACR_DEPLOYED=false
NGINX_PUSHED=false
MAIN_DEPLOYED=false

# 各フェーズ後に更新
if [ $? -eq 0 ]; then
  ACR_DEPLOYED=true
fi
```

### 出力データの受け渡し

```bash
# フェーズ1の出力
ACR_NAME=$(az deployment group show ... -o tsv)
ACR_LOGIN_SERVER=$(az deployment group show ... -o tsv)

# フェーズ2の出力
NGINX_IMAGE_URL="${ACR_LOGIN_SERVER}/dify-nginx:latest"

# フェーズ3への入力
--parameters acrName="$ACR_NAME" nginxImage="$NGINX_IMAGE_URL"
```

## エラーハンドリング

### フェーズ1の失敗（ACRデプロイ）

```bash
if [ $? -ne 0 ]; then
  print_error "ACR deployment failed"
  print_info "Check Azure portal for deployment errors"
  exit 1
fi
```

### フェーズ2の失敗（nginxビルド/プッシュ）

```bash
if [ $? -ne 0 ]; then
  print_error "nginx container build/push failed"
  print_info "ACR has been deployed but nginx image is not available"
  print_info "You can retry by running: bash scripts/build-and-push-nginx.sh --acr-name $ACR_NAME"
  exit 1
fi
```

### フェーズ3の失敗（メインデプロイ）

```bash
if [ $? -ne 0 ]; then
  print_error "Main infrastructure deployment failed"
  print_info "ACR and nginx image are available"
  print_info "You can retry the main deployment with the same parameters"
  exit 1
fi
```

### ロールバック戦略

- 各フェーズは独立しているため、部分的なロールバックが可能
- ACRデプロイ失敗: リソースグループを削除して再試行
- nginxプッシュ失敗: ビルドスクリプトのみ再実行
- メインデプロイ失敗: パラメータを修正して再デプロイ

## テスト戦略

### 1. 単体テスト

**ACR専用テンプレート**:
```bash
# what-ifモードでテスト
az deployment group what-if \
  --resource-group test-rg \
  --template-file bicep/acr-only.bicep \
  --parameters environment=dev location=japaneast
```

**メインテンプレート（ACRなし）**:
```bash
# ACRモジュールが削除されていることを確認
az bicep build --file bicep/main.bicep
# エラーがないことを確認
```

### 2. 統合テスト

**完全な3フェーズデプロイ**:
```bash
# テスト環境でフルデプロイを実行
bash scripts/deploy.sh \
  --environment dev \
  --resource-group dify-test-rg \
  --location japaneast
```

**検証項目**:
1. ACRが正常にデプロイされる
2. nginxイメージがACRにプッシュされる
3. メインインフラストラクチャがnginxイメージを使用してデプロイされる
4. nginx Container Appが正常に起動する
5. Application Gatewayからnginxへのルーティングが機能する

### 3. エラーシナリオテスト

**フェーズ2の失敗をシミュレート**:
```bash
# Dockerfileを一時的に壊してビルド失敗をテスト
# スクリプトが適切にエラーハンドリングすることを確認
```

**パラメータ不足のテスト**:
```bash
# nginxImageパラメータなしでメインテンプレートをデプロイ
# デフォルト値が使用されることを確認
```

### 4. 後方互換性テスト

**既存のパラメータファイルとの互換性**:
```bash
# 古いパラメータファイル（ACRパラメータあり）でデプロイ
# エラーが発生しないことを確認
```

## 実装の考慮事項

### 命名規則の一貫性

ACR名は両方のテンプレートで同じロジックを使用：
```bicep
var acrName = 'difyacr${environment}${uniqueString(resourceGroup().id)}'
```

### 必須パラメータの検証

すべてのACR関連パラメータは必須：
```bicep
// デフォルト値なし = 必須パラメータ
param acrName string
param acrLoginServer string
param acrAdminUsername string
param acrAdminPassword string
param nginxImage string
```

デプロイスクリプトがこれらの値を提供しない場合、デプロイは失敗する

### スクリプトの冪等性

- ACRが既に存在する場合は再利用
- nginxイメージが既に存在する場合は上書き
- メインデプロイは通常のBicepの冪等性に従う

### ドキュメントの更新

以下のドキュメントを更新する必要があります：
- `README.md`: 新しいデプロイフローを説明
- `docs/deployment-guide.md`: 3フェーズデプロイの詳細手順
- パラメータファイルのコメント: nginxImageの説明

## セキュリティの考慮事項

### ACR認証

**認証方式**: 全環境で管理者ユーザー認証を使用

**理由**:
- Bicepデプロイ時にContainer AppsがACRからイメージをプルする際、ポリシーベースのアクセス（マネージドID）が即座に有効にならない
- ACRとContainer Appsが同じデプロイで作成される場合、RBACロールの割り当てが完全に伝播する前にContainer Appがイメージをプルしようとする
- Azure RBACの伝播には数分かかる場合があり、デプロイの信頼性が低下する

**実装**:

1. **Container Appsでの認証設定**:
```bicep
// nginxContainerApp.bicep
resource nginxContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  properties: {
    configuration: {
      secrets: [
        {
          name: 'acr-password'
          value: acrAdminPassword
        }
      ]
      registries: [
        {
          server: acrLoginServer
          username: acrAdminUsername
          passwordSecretRef: 'acr-password'
        }
      ]
    }
  }
}
```

2. **デプロイフロー**:
   - フェーズ1: ACRを管理者ユーザー有効でデプロイ
   - フェーズ2: 管理者認証情報を使用してイメージをプッシュ
   - フェーズ3: Container Appsを管理者認証情報でデプロイ

**セキュリティ考慮事項**:
- 管理者パスワードはBicepのsecureパラメータとして扱う
- パスワードはContainer Appsのシークレットとして保存
- 必要に応じてACRのネットワークアクセス制限を設定可能

### イメージの検証

- プッシュ後にイメージの存在を確認
- イメージタグのバージョニング戦略（現在は `latest` のみ）

## パフォーマンスの考慮事項

### デプロイ時間

- フェーズ1（ACR）: 約2-3分
- フェーズ2（nginxビルド/プッシュ）: 約3-5分
- フェーズ3（メインインフラ）: 約20-30分
- **合計**: 約25-38分（現在とほぼ同じ）

### 最適化の機会

- nginxイメージのキャッシュ利用
- 並列デプロイ（ACRと他のリソースが独立している場合）
- イメージの事前ビルド（CI/CDパイプライン）
