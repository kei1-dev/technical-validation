# Azure Functions Flex Consumption - Bicep デプロイメント

このプロジェクトは、Azure Functions Flex Consumption プランを Bicep テンプレートを使用してデプロイするためのインフラストラクチャコードです。

## プロジェクト概要

Azure Functions の Flex Consumption プランは、柔軟なスケーリングとコスト最適化を実現する新しいホスティングオプションです。このプロジェクトでは、以下のリソースを自動的にプロビジョニングします：

- **ストレージアカウント**: Function App のバックエンドストレージ
- **App Service プラン**: Flex Consumption プラン（FC1 SKU）
- **Function App**: Python 3.11 ランタイムを使用した Function App

## 前提条件

以下のツールがインストールされている必要があります：

- **Azure CLI**: バージョン 2.77.0 以上
  ```bash
  az --version
  ```

- **Bicep CLI**: バージョン 0.38.33 以上
  ```bash
  az bicep version
  ```

- **Azure サブスクリプション**: デプロイ先のアクティブなサブスクリプション
- **Azure へのログイン**: `az login` でログイン済みであること

## アーキテクチャ

このテンプレートは、以下のリソースを作成します：

```
Resource Group
├── Storage Account (StorageV2)
│   ├── SKU: Standard_LRS
│   ├── TLS: 1.2 以上
│   └── Blob Public Access: 無効
│
├── App Service Plan
│   ├── SKU: FC1 (FlexConsumption)
│   └── OS: Linux
│
└── Function App
    ├── Runtime: Python 3.11
    ├── Maximum Instances: 100
    ├── Instance Memory: 2048 MB
    └── Always Ready Instances: 0
```

## プロジェクト構造

```
bicep/
├── main.bicep                              # メインのオーケストレーションテンプレート
└── modules/
    ├── storageAccount.bicep                # ストレージアカウントモジュール
    └── functionAppFlexConsumption.bicep    # Function App モジュール
```

### ファイル説明

- **main.bicep**: 全リソースを統合する親テンプレート。App Service プランを定義し、2つのモジュールを呼び出します。
- **storageAccount.bicep**: ストレージアカウントを作成し、接続文字列を出力します。
- **functionAppFlexConsumption.bicep**: Flex Consumption プラン用の Function App を作成します。

## 設定パラメータ

### 必須パラメータ

| パラメータ名 | 説明 | 例 |
|------------|------|-----|
| `storageAccountName` | グローバルに一意なストレージアカウント名（3-24文字、小文字と数字のみ） | `kurosawaflexsto` |
| `functionAppName` | グローバルに一意な Function App 名 | `kurosawa-flex-func` |

### オプションパラメータ

| パラメータ名 | 説明 | デフォルト値 | 設定可能な値 |
|------------|------|------------|-------------|
| `location` | デプロイ先の Azure リージョン | リソースグループのロケーション | 任意の Azure リージョン |
| `functionsWorkerRuntime` | Azure Functions ワーカーランタイム | `python` | `dotnet-isolated`, `node`, `powershell`, `python`, `java` |
| `maximumInstanceCount` | スケーリング時の最大インスタンス数 | `100` | 1-100 |
| `instanceMemoryMB` | インスタンスあたりのメモリ（MB） | `2048` | `2048`, `4096` |
| `alwaysReadyInstances` | 常時待機するインスタンス数 | `0` | 0以上 |

## デプロイ手順

### 1. Azure へのログイン

```bash
az login
```

### 2. サブスクリプションの設定（必要に応じて）

```bash
az account set --subscription "<サブスクリプション名またはID>"
```

### 3. リソースグループの確認または作成

既存のリソースグループを使用する場合：

```bash
az group show --name <リソースグループ名>
```

新規作成する場合：

```bash
az group create --name <リソースグループ名> --location japaneast
```

### 4. デプロイ前の検証（推奨）

what-if コマンドで変更内容をプレビューします：

```bash
az deployment group what-if \
  --resource-group <リソースグループ名> \
  --template-file bicep/main.bicep \
  --parameters storageAccountName=<ストレージアカウント名> \
  --parameters functionAppName=<Function App名>
```

### 5. デプロイの実行

```bash
az deployment group create \
  --resource-group <リソースグループ名> \
  --template-file bicep/main.bicep \
  --parameters storageAccountName=<ストレージアカウント名> \
  --parameters functionAppName=<Function App名>
```

#### カスタムパラメータを使用する場合の例

```bash
az deployment group create \
  --resource-group kurosawa-jp-rg \
  --template-file bicep/main.bicep \
  --parameters storageAccountName=kurosawaflexsto \
  --parameters functionAppName=kurosawa-flex-func \
  --parameters functionsWorkerRuntime=python \
  --parameters maximumInstanceCount=100 \
  --parameters instanceMemoryMB=2048 \
  --parameters alwaysReadyInstances=0
```

## デプロイ確認

### デプロイ結果の確認

デプロイが成功すると、以下の出力が表示されます：

```json
{
  "functionAppDefaultHostname": "your-function-app.azurewebsites.net",
  "functionAppName": "your-function-app",
  "storageAccountName": "yourstorageaccount"
}
```

### リソースの確認

作成されたリソースを確認：

```bash
az resource list --resource-group <リソースグループ名> --output table
```

### Function App の詳細確認

```bash
az functionapp show \
  --name <Function App名> \
  --resource-group <リソースグループ名>
```

### App Service プランの確認

```bash
az appservice plan show \
  --name <Function App名>-plan \
  --resource-group <リソースグループ名>
```

## 出力値

デプロイ完了後、以下の値が出力されます：

| 出力名 | 説明 | 使用例 |
|-------|------|--------|
| `functionAppName` | 作成された Function App の名前 | Azure Portal での検索、CLI コマンドでの参照 |
| `functionAppDefaultHostname` | Function App のデフォルトホスト名 | HTTP エンドポイントへのアクセス（`https://<hostname>/`) |
| `storageAccountName` | 作成されたストレージアカウントの名前 | ストレージの管理、接続文字列の取得 |

### 出力値の取得方法

デプロイ後に出力値を取得する場合：

```bash
az deployment group show \
  --resource-group <リソースグループ名> \
  --name <デプロイ名> \
  --query properties.outputs
```

## ライセンス

このプロジェクトは技術検証用のサンプルコードです。
