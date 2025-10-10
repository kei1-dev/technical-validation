# Azure PowerShell で体験する ARM テンプレート ハンズオン

Azure Resource Manager (ARM) テンプレートの最小構成とストレージ アカウント デプロイを、Azure PowerShell (Az モジュール) を使って体験するハンズオン資料です。クラウド初心者でも進めやすいよう、手順・確認ポイント・公式ドキュメントリンクを併記しています。

---

## 1. はじめに

- **目的**: ARM テンプレートの基本構造を理解し、PowerShell からテンプレートを検証・デプロイする流れを体験する。
- **達成ゴール**
  - 空テンプレートを作成し、`Test-AzResourceGroupDeployment` で検証できる。
  - ストレージ アカウントをデプロイするテンプレートとパラメーター ファイルを作成し、`New-AzResourceGroupDeployment` で展開できる。
  - デプロイ結果を Azure Portal と PowerShell で確認し、不要なリソースをクリーンアップできる。
- **前提条件**
  - Azure サブスクリプションを保有し、`Contributor` 以上のロールが割り当てられていること。
  - Windows / macOS / Linux の PowerShell 7 以降、または Azure Cloud Shell (PowerShell) を利用可能であること。
  - Az PowerShell モジュール (推奨: 11.x 以降) がインストール済みであること。参考: [Azure PowerShell のインストール](https://learn.microsoft.com/powershell/azure/install-azure-powershell)

---

## 2. Azure PowerShell 環境セットアップ

### 2.1 Az モジュールのインストールと更新

Az モジュールのセットアップ手順は別ファイルにまとめています。未インストールの場合はハンズオン前に以下を参照してください。

- セットアップ手順: `docs/setup/az-powershell.md`
- 公式ドキュメント: [Install Azure PowerShell](https://learn.microsoft.com/powershell/azure/install-azure-powershell)

### 2.2 サインインとサブスクリプション選択

```powershell
# Azure へサインイン (ブラウザーで認証)
Connect-AzAccount

# 利用可能なサブスクリプション一覧を確認
Get-AzSubscription | Select-Object Name, Id, State

# 使用するサブスクリプションを選択
Set-AzContext -SubscriptionId "<SubscriptionId>"
```

Portal 側でアクティビティ ログを見る際は同じサブスクリプションに切り替えておく。

### 2.3 リソース グループの確認と作成

```powershell
# 既存のリソース グループを確認
Get-AzResourceGroup | Select-Object ResourceGroupName, Location

# ハンズオン全体で使うリソース グループ名を変数に保持
$rgName = "rg-arm-handson-jpe"

# ハンズオン用のリソース グループを作成
New-AzResourceGroup -Name $rgName -Location "JapanEast"
```

Location 一覧の取得: `Get-AzLocation | Select-Object Location, DisplayName`
> 補足: 以降のコマンドでは同じ PowerShell セッションで `$rgName` を再利用します。新しいセッションを開いた場合は、再度 `$rgName = "rg-arm-handson-jpe"` を実行してからコマンドを試してください。

---

## 3. ARM テンプレートの基礎

### 3.1 空テンプレートの構造を理解する

ARM テンプレートのトップレベル要素は `$schema`, `contentVersion`, `parameters`, `variables`, `resources`, `outputs` です。詳細: [テンプレートの構文](https://learn.microsoft.com/azure/azure-resource-manager/templates/syntax)

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {},
  "variables": {},
  "resources": [],
  "outputs": {}
}
```

- ### 3.2 リポジトリ内のフォルダー構成
  - `templates/` : 完成済みサンプル (空テンプレート、ストレージ テンプレートなど)
  - `work/` : 受講者が編集するワークスペース (空ファイルを事前配置)
  - `docs/` : 本ハンズオン資料

作業時は `work/` 以下のファイルを編集し、必要に応じて `templates/` を参照します。リポジトリ直下で PowerShell を開き、以下のコマンドで内容を確認します。

```powershell
# 参考: 作業開始時にフォルダー構成を確認
Get-ChildItem -Recurse -Depth 1 templates, work
```

---

## 4. ハンズオン Part 1: 空テンプレートの検証とデプロイ

### 4.1 テンプレート ファイルを作成
1. エディター (VS Code 推奨) で `work/empty-template.json` を開きます。
2. `templates/empty-template.json` を参考にしながら、同じ内容を入力 (またはコピー) します。
3. 保存後、PowerShell でファイル パスを確認します。

```powershell
$templatePath = (Resolve-Path "./work/empty-template.json")
Get-Content $templatePath
```

### 4.2 検証コマンド (`Test-AzResourceGroupDeployment`)

```powershell
Test-AzResourceGroupDeployment `
  -ResourceGroupName $rgName `
  -TemplateFile $templatePath `
  -Verbose
```

- `-Verbose` を付けると成功時に情報メッセージ (`Validation passed` など) が表示される。
- 失敗した場合はエラー メッセージから JSON の構文やスキーマ URL を確認。
- 成功判定は戻り値の `ProvisioningState` (`Succeeded` であれば成功) や `Timestamp` を確認する。
- `-Verbose` を外して実行する場合は、情報ストリームが既定で非表示のためメッセージが出ない。メッセージを明示的に表示したいときは `$InformationPreference = 'Continue'` を設定する。
- 参照: [デプロイの検証](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-powershell#validate-a-deployment)

### 4.3 (任意) デプロイの実行

空テンプレートは実リソースを作成しないため、そのままデプロイしても変更は発生しない。

```powershell
New-AzResourceGroupDeployment `
  -ResourceGroupName $rgName `
  -TemplateFile $templatePath
```

Azure Portal の「リソース グループ」ブレード → `rg-arm-handson-jpe` → 「デプロイ」タブで履歴を確認できる。

---

## 5. ハンズオン Part 2: ストレージ アカウントをデプロイ

### 5.1 必須パラメーターの確認

ストレージ アカウントの ARM テンプレートで必須となる主なプロパティは `name`, `location`, `sku.name`, `kind` など。詳細は公式リファレンス参照: [Microsoft.Storage/storageAccounts テンプレート リファレンス](https://learn.microsoft.com/azure/templates/microsoft.storage/storageaccounts)

### 5.2 テンプレートを編集して固定値を設定
1. `templates/storage-account.json` を開き、構成要素と必須プロパティを確認します。
2. `work/storage-account.json` を開き、以下のようにパラメーターを使わず固定値（またはテンプレート関数）で設定します。

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {},
  "variables": {
    "storageAccountName": "[concat('handsonstor', uniqueString(resourceGroup().id))]"
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2022-05-01",
      "name": "[variables('storageAccountName')]",
      "location": "japaneast",
      "sku": {
        "name": "Standard_LRS"
      },
      "kind": "StorageV2",
      "properties": {}
    }
  ],
  "outputs": {
    "storageAccountId": {
      "type": "string",
      "value": "[resourceId('Microsoft.Storage/storageAccounts', variables('storageAccountName'))]"
    }
  }
}
```

> 補足: `uniqueString(resourceGroup().id)` を使うことで、同じリソース グループ内で一意な名前を自動生成できます。別の命名ルールに変更しても構いません（小文字英数字のみ、3〜24 文字の制約に注意）。

3. 保存後、PowerShell でテンプレート パスを変数に格納します。

```powershell
$storageTemplatePath = (Resolve-Path "./work/storage-account.json")
```

### 5.3 what-if デプロイで変更内容を確認

```powershell
New-AzResourceGroupDeployment `
  -ResourceGroupName $rgName `
  -TemplateFile $storageTemplatePath `
  -WhatIf
```

`WhatIfResult` に新規作成されるリソースが表示され、破壊的変更がないか事前に確認できる。参考: [what-if 操作](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-what-if)

### 5.4 実デプロイの実行

```powershell
$deployment = New-AzResourceGroupDeployment `
  -ResourceGroupName $rgName `
  -TemplateFile $storageTemplatePath `
  -Verbose

$deployment.Outputs
```

- `Outputs` にストレージ アカウントのリソース ID が表示される。
- 失敗した場合は `-Debug` を付与すると詳細ログが確認可能。

### 5.5 デプロイ結果の確認

```powershell
# 作成されたストレージ アカウントを確認
Get-AzStorageAccount -ResourceGroupName $rgName

# 接続文字列を取得 (必要に応じて)
Get-AzStorageAccountKey -ResourceGroupName $rgName -Name "<StorageAccountName>"
```

Portal では「リソース グループ」→ 対象ストレージ アカウントを開き、`Deployment details` タブからテンプレートとパラメーターを再表示できる。

---

## 6. ハンズオン Part 3: テンプレート構造のフル活用とデプロイ モード

### 6.1 完成テンプレートで全構造を再確認
- `templates/storage-account-advanced/main.json` で `$schema` / `contentVersion` / `parameters` / `variables` / `functions` / `resources` / `outputs` がすべて揃っていることを確認します。
- `work/storage-account-advanced/main.json` に同じ内容をコピーし、必要であれば値を調整して保存します。
- 併せて `templates/storage-account-advanced/parameters.json` を開き、パラメーター構成を確認した上で `work/storage-account-advanced/parameters.json` に写経し、環境に合わせて値を編集します。
- 各構成要素のポイント
  - `parameters`: プレフィックス・リージョン・SKU・タグなど、外部から切り替えたい値を宣言。
  - `variables`: 一意なストレージ名や SKU マップなど、テンプレート内で再利用する計算値を保持。
  - `functions`: `handson` 名前空間内で `buildTags` を定義し、環境名とタイムスタンプを受け取ってタグ オブジェクトを組み立てる。関数本体では `deployment().name` をタグに含め、`Environment` フィールドと `LastDeployed` フィールドには呼び出し元から渡された値を格納する。呼び出し側 (`tags`) は `[handson.buildTags(parameters('environmentTag'), parameters('deploymentTimestamp'))]` の形で評価され、パラメーターの既定値として `utcNow()` を使うことでデプロイ時刻を一度だけ取得できる。
  - `resources`: StorageV2 をデプロイし、`tags` にユーザー定義関数から得たオブジェクトを設定。
  - `outputs`: ストレージ名とプライマリ エンドポイントを返し、後続の自動化に利用できるようにする。

> 補足: ユーザー定義関数はテンプレートの先頭で宣言し、`namespace` と `members` 配下に配置する必要があります。関数の `parameters` セクションは通常のパラメーターと同様の型指定が可能で、`output` セクションで返却する型と値を明示します。ARM エンジンはリソース評価前に関数を解決するため、`functions` に定義した処理はリソースから参照すれば自動的に展開されます。

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "storageAccountPrefix": {
      "type": "string",
      "defaultValue": "handsonstor",
      "minLength": 3,
      "maxLength": 11
    },
    "location": {
      "type": "string",
      "defaultValue": "japaneast"
    },
    "skuTier": {
      "type": "string",
      "defaultValue": "Standard",
      "allowedValues": [
        "Standard",
        "Premium"
      ]
    },
    "environmentTag": {
      "type": "string",
      "defaultValue": "Workshop"
    },
    "deploymentTimestamp": {
      "type": "string",
      "defaultValue": "[utcNow()]"
    }
  },
  "variables": {
    "storageAccountName": "[toLower(concat(parameters('storageAccountPrefix'), uniqueString(resourceGroup().id)))]",
    "skuNameMap": {
      "Standard": "Standard_LRS",
      "Premium": "Premium_LRS"
    }
  },
  "functions": [
    {
      "namespace": "handson",
      "members": {
        "buildTags": {
          "parameters": [
            {
              "name": "environment",
              "type": "string"
            },
            {
              "name": "timestamp",
              "type": "string"
            }
          ],
          "output": {
            "type": "object",
            "value": {
              "Environment": "[parameters('environment')]",
              "Owner": "[deployment().name]",
              "LastDeployed": "[parameters('timestamp')]"
            }
          }
        }
      }
    }
  ],
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2022-05-01",
      "name": "[variables('storageAccountName')]",
      "location": "[parameters('location')]",
      "sku": {
        "name": "[variables('skuNameMap')[parameters('skuTier')]]"
      },
      "kind": "StorageV2",
      "tags": "[handson.buildTags(parameters('environmentTag'), parameters('deploymentTimestamp'))]",
      "properties": {
        "supportsHttpsTrafficOnly": true,
        "accessTier": "Hot"
      }
    }
  ],
  "outputs": {
    "storageAccountName": {
      "type": "string",
      "value": "[variables('storageAccountName')]"
    },
    "primaryEndpoints": {
      "type": "object",
      "value": "[reference(resourceId('Microsoft.Storage/storageAccounts', variables('storageAccountName'))).primaryEndpoints]"
    }
  }
}
```

- パラメーター ファイル (例: `templates/storage-account-advanced/parameters.json`)

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "storageAccountPrefix": {
      "value": "handsonps"
    },
    "location": {
      "value": "japaneast"
    },
    "skuTier": {
      "value": "Standard"
    },
    "environmentTag": {
      "value": "Workshop"
    }
  }
}
```

### 6.2 パラメーターを渡して Incremental モードでデプロイ

```powershell
$advancedTemplatePath  = (Resolve-Path "./work/storage-account-advanced/main.json")
$advancedParametersPath = (Resolve-Path "./work/storage-account-advanced/parameters.json")

New-AzResourceGroupDeployment `
  -ResourceGroupName $rgName `
  -TemplateFile $advancedTemplatePath `
  -TemplateParameterFile $advancedParametersPath `
  -Mode Incremental `
  -Verbose
```

- `Outputs` に返却された `storageAccountName` と `primaryEndpoints` を確認し、テンプレートで宣言した値が適用されたことを確かめましょう。
- `Incremental` は既定モードであり、テンプレートに含まれないリソースは削除されません。

### 6.3 デプロイ モードの違いを理解する

| モード | 特徴 | 代表的な用途 |
|--------|------|--------------|
| Incremental (既定) | テンプレート記述のリソースのみ作成・更新。既存リソースは保持される。 | 段階的な更新、安全な本番運用 |
| Complete | テンプレートに存在しないリソースを同じスコープから削除し、構成を完全同期。 | 検証環境を都度初期化、本番での不要リソース除去 |

参考: [デプロイ モードについて](https://learn.microsoft.com/azure/azure-resource-manager/templates/deployment-modes)

### 6.4 ハンズオン: Complete モードの挙動を確認
1. テンプレートに含まれないリソースを直接Powershellで追加して差分を作成します。

   ```powershell
   $extraName = "extrastr$((Get-Random -Maximum 9999).ToString('0000'))"
   New-AzStorageAccount `
     -ResourceGroupName $rgName `
     -Name $extraName `
     -Location "japaneast" `
     -SkuName "Standard_LRS" `
     -Kind "StorageV2"
   ```

2. Complete モードを What-If で実行し、削除対象が表示されることを確認します。

   ```powershell
   New-AzResourceGroupDeployment `
     -ResourceGroupName $rgName `
     -TemplateFile $advancedTemplatePath `
     -TemplateParameterFile $advancedParametersPath `
     -Mode Complete `
     -WhatIf
   ```

   `Delete` アクションとしてテンプレート外のリソース (例: `extrastr****`) が表示されることを確認します。想定外のリソースが含まれている場合は、この段階でテンプレートや既存リソースを調整してください。

3. Complete モードを適用し、テンプレートに存在しないリソースが削除されることを確認します。`-Confirm` のプロンプトに応答し、完了後に `Get-AzStorageAccount -ResourceGroupName $rgName` などで構成がテンプレートと一致するか検証します。

   ```powershell
   New-AzResourceGroupDeployment `
     -ResourceGroupName $rgName `
     -TemplateFile $advancedTemplatePath `
     -TemplateParameterFile $advancedParametersPath `
     -Mode Complete `
     -Confirm
   ```

   ※Complete モードはテンプレートにないリソースを削除するため、実行前に必ず What-If の結果を確認し、削除したくないリソースはテンプレートに追加するか事前に整理しておきましょう。
---

## 7. 片付けとクリーンアップ

### 7.1 リソースの削除

```powershell
# リソース グループごと削除 (元に戻せないため要注意)
Remove-AzResourceGroup -Name $rgName -Force
```

削除コマンドは完了まで数分かかることがある。Portal の通知で進捗を確認。

### 7.2 コストとガバナンスの注意点

- 検証用リソースを残したままにすると課金が発生する可能性があるため、作業後に必ずリソースを点検する。
- 実案件では削除禁止ロック (`New-AzResourceLock`) やタグ付けでリソースを保護・分類する。参考: [Azure リソースのロック](https://learn.microsoft.com/azure/azure-resource-manager/management/lock-resources)

---

## 8. トラブルシュートと FAQ

| 症状 | 主な原因 | 対処 |
|------|----------|------|
| `AuthorizationFailed` エラー | 権限不足 (`Contributor` 以上が必要) | 管理者に RBAC の割り当てを依頼 |
| `InvalidTemplate` / JSON パース エラー | カンマや引用符の欠落、`$schema` の URL ミス | VS Code + ARM Tools 拡張で検証しながら編集 ([ARM Tools 拡張](https://learn.microsoft.com/azure/azure-resource-manager/templates/vscode-tools)) |
| 名前が使用済みでデプロイ失敗 | ストレージ名がグローバル一意でない | `Get-Random` などで一意な名前を生成し再実行 |
| `DeploymentFailed` で詳細が不明 | what-if 未実施、詳細ログ未確認 | `-WhatIf` や `-Debug`、Portal のデプロイ詳細ログを参照 |
| モジュールの読み込みエラー | Az モジュール未インストール・古いバージョン | セットアップ手順 (`docs/setup/az-powershell.md`) を参照して再インストール or 更新 |

---

## 9. 次のステップ

- **練習課題**: 同じテンプレートに Blob コンテナー初期作成や診断設定 (`diagnosticSettings`) を追加してみる。
- **Bicep へのステップアップ**: [Bicep の概要](https://learn.microsoft.com/azure/azure-resource-manager/bicep/overview) を学び、`az bicep install` と `New-AzResourceGroupDeployment -TemplateFile main.bicep` を試す。
- **Microsoft Learn モジュール**
  - [ARM テンプレートを使って Azure リソースをデプロイする](https://learn.microsoft.com/training/modules/create-azure-resource-manager-template/)
  - [Azure PowerShell での操作を自動化する](https://learn.microsoft.com/training/modules/automate-azure-tasks-with-powershell/)

ハンズオン後はテンプレートとパラメーターの変更点を Git 等で管理し、Pull Request ベースでレビューする運用も試してみてください。

