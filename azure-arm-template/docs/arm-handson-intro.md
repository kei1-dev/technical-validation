# Azure ARM 超初心者向けハンズオン目次

これから ARM テンプレートを体験する方向けの事前学習資料です。専門用語はなるべく平易に説明し、詳しく学びたい場合にすぐ確認できるよう Microsoft 公式ドキュメントのリンクを多めに掲載しています。

---

## 1. Azure Resource Manager (ARM)とは

### 1.1 ARMの役割
- **制御プレーンの説明**: Azure Portal / CLI / PowerShell / REST API など、どのツールから操作しても最終的に ARM がリクエストを受け付け、正しいリソース プロバイダーへ伝達します。ARM はアクセス許可の確認、ポリシー適用、依存関係の解決を担う「管理プレーン (Control Plane)」です（[Azure Resource Manager とは](https://learn.microsoft.com/azure/azure-resource-manager/management/overview)）。
- **実リソースと管理プレーンの違い**: 仮想マシンやストレージなどの「実リソース (データプレーン)」はワークロードを処理します。ARM はその前面で操作命令を仲介し、構成管理・監査を担当するため、管理系トラフィックと実データ処理を分離できます（[Azure のデプロイ モデル](https://learn.microsoft.com/azure/azure-resource-manager/management/deployment-model-overview)）。
- **宣言的デプロイ（Desired State）の考え方**: ユーザーは「最終的にこうしたい」という Desired State をテンプレートで宣言するだけで、ARM が現在との差分を判断してリソースを作成・更新します。再現性が高まり、同じテンプレートを繰り返し適用しても状態が安定します（[ARM テンプレートの概要](https://learn.microsoft.com/azure/azure-resource-manager/templates/overview)）。

### 1.2 ARMの特徴
- **一元管理（複数リソースをまとめて扱える）**: リソース グループを単位にアプリ一式を束ね、タグ付け・ロール割り当て・削除などをまとめて実行できます（[リソース グループの管理](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)）。
- **依存関係管理（順序を自動解決）**: テンプレート内で `dependsOn` を指定すると、ARM が必要な順序で並列・直列デプロイを調整します。人手で手順を組み立てなくても失敗しにくい構成が実現します（[テンプレートの依存関係](https://learn.microsoft.com/azure/azure-resource-manager/templates/define-resource-dependency)）。
- **アクセス制御（RBACによる権限管理）**: ロール ベース アクセス制御 (RBAC) を使い、サブスクリプションやリソース グループ単位で権限を割り当てると、ARM が各リクエストに対して許可・拒否を判断します（[Azure RBAC の概要](https://learn.microsoft.com/azure/role-based-access-control/overview)）。

### 1.3 ARMの位置づけ（図解）
```
利用者ツール層
  Azure Portal / CLI / PowerShell / テンプレート / SDK
          │  操作リクエスト
          ▼
Azure Resource Manager (管理プレーン)
  - 認可 (RBAC) ・ポリシー適用
  - 依存関係の解決・監査ログ
          │  制御命令
          ▼
実リソース (データプレーン)
  VM / App Service / Storage / SQL / VNet など
  → 実際の処理・データ保存を担当
```
- **利用者（ポータル／CLI／テンプレート）→ARM→実リソース**: すべての操作は ARM を経由してリソースへ届き、活動ログも同じ経路で記録されます。
- **「建築士」と「建物」の例え**: ARM は要求を設計図（テンプレート）に落とし込み、専門職（リソース プロバイダー）へ指示する建築士の役割。完成した建物が実リソースであり、実際に利用者が使う部分です。

---

## 2. 基本的な用語

### 2.1 リソース (Resource)
- **Azureの最小単位**: 仮想マシン、ストレージ アカウント、仮想ネットワークなど個別サービスの実体で、ARM テンプレートの `resources` 配列に宣言します（[Azure サービスとリソース プロバイダー](https://learn.microsoft.com/azure/azure-resource-manager/management/azure-services-resource-providers)）。
- **リソースプロバイダーによる管理**: 種類ごとに `Microsoft.Compute` や `Microsoft.Storage` といったリソース プロバイダーが API を提供し、テンプレートでは `type` で指定します（同上）。

### 2.2 リソースグループ (Resource Group)
- **リソースの「入れ物」**: 関連リソースを論理的にまとめ、タグやロック、アクセス権を共通で設定できます（[リソース グループの管理](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)）。
- **ライフサイクルの管理単位**: テストや本番など環境ごとにグループを作ると、一括削除や更新が容易になり、コスト管理もしやすくなります（同上）。
- **削除時の注意点**: グループを削除すると中のリソースはすべて削除されます。重要なデータはロック (`CanNotDelete`) やバックアップで保護してから操作しましょう（[リソース グループの削除](https://learn.microsoft.com/azure/azure-resource-manager/management/delete-resource-group)）。

### 2.3 デプロイメント (Deployment)
- **テンプレートを元にした展開作業**: テンプレートとパラメーターを ARM に送ると Desired State に向けてリソースが作成・更新されます。デプロイ履歴は `deployments` リソースとしてリソース グループに保存されます（[ARM テンプレートのデプロイ パターン](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-patterns)）。
- **ロールバック再実行の仕組み**: `az deployment group create --rollback-on-error` や `New-AzResourceGroupDeployment -RollbackToLastDeployment` で直前の正常デプロイに戻せます。同じテンプレートを再実行しても差分のみ適用されるため復旧が容易です（[Azure CLI でのデプロイ](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-cli)、[PowerShell でのデプロイ](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-powershell)）。

### 2.4 ARMテンプレート (ARM Template)
- **JSON/YAML形式の設計図**: 公式には JSON テンプレート (`deploymentTemplate.json`) がサポートされ、テンプレート仕様 (Template Specs) では付随情報に YAML を添付するケースもあります（[ARM テンプレートの概要](https://learn.microsoft.com/azure/azure-resource-manager/templates/overview)、[テンプレート仕様](https://learn.microsoft.com/azure/azure-resource-manager/templates/template-specs)）。
- **再現性自動化のポイント**: テンプレートとパラメーターを分離し、Git でバージョン管理、`what-if` で差分可視化、CI/CD に組み込むことで Desired State を自動再現できます（[テンプレートのベスト プラクティス](https://learn.microsoft.com/azure/azure-resource-manager/templates/best-practices)）。

---

## 3. ARMテンプレートの基本

### 3.1 テンプレートの構造
- **`$schema`**: テンプレート構文のバージョンを宣言。最新スキーマを指定することで利用可能な要素が決まります（[テンプレート構文](https://learn.microsoft.com/azure/azure-resource-manager/templates/syntax)）。
- **`contentVersion`**: 任意のバージョン文字列で、組織内でテンプレートの変更履歴を追跡するのに役立ちます（同上）。
- **`parameters`**: 外部から値を受け取る宣言。型や既定値、許可値を定義し、テンプレート内では `parameters('<name>')` で参照します（[パラメーターの定義](https://learn.microsoft.com/azure/azure-resource-manager/templates/parameters)）。
- **`variables`**: テンプレート内で共通利用する値や式。`[concat()]` などのテンプレート関数で動的に生成できます（[テンプレート関数](https://learn.microsoft.com/azure/azure-resource-manager/templates/template-functions)）。
- **`resources`**: 実際にデプロイする Azure リソースを配列で列挙します。`type`、`apiVersion`、`name`、`location`、`properties` などを指定します（[リソース定義](https://learn.microsoft.com/azure/azure-resource-manager/templates/resource-declaration)）。
- **`outputs`**: デプロイ後に返したい値を定義し、後続の自動化へ渡します（[outputs の使い方](https://learn.microsoft.com/azure/azure-resource-manager/templates/outputs)）。

### 3.2 最小テンプレート例
- **空テンプレート**
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
- **単一リソース（ストレージ アカウント）**: 
  ```json
  {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
      "storageName": {
        "type": "string",
        "minLength": 3,
        "maxLength": 24,
        "metadata": {
          "description": "作成するストレージ アカウント名 (グローバルで一意)"
        }
      },
      "storageSku": {
        "type": "string",
        "defaultValue": "Standard_LRS",
        "allowedValues": [
          "Standard_LRS",
          "Standard_GRS",
          "Standard_RAGRS",
          "Standard_ZRS"
        ]
      }
    },
    "variables": {
      "location": "japaneast"
    },
    "resources": [
      {
        "type": "Microsoft.Storage/storageAccounts",
        "apiVersion": "2022-05-01",
        "name": "[parameters('storageName')]",
        "location": "[variables('location')]",
        "sku": {
          "name": "[parameters('storageSku')]"
        },
        "kind": "StorageV2",
        "properties": {}
      }
    ],
    "outputs": {
      "storageId": {
        "type": "string",
        "value": "[resourceId('Microsoft.Storage/storageAccounts', parameters('storageName'))]"
      }
    }
  }
  ```
  [ストレージアカウントリソース定義](https://learn.microsoft.com/en-us/azure/templates/microsoft.storage/storageaccounts?pivots=deployment-language-arm-template)
  ストレージアカウントテンプレート作成の詳細: [チュートリアル - 最初のテンプレートを作成する](https://learn.microsoft.com/azure/azure-resource-manager/templates/template-tutorial-create-first-template)

### 3.3 パラメータの使い方
- **外部から値を渡す仕組み**: パラメーターは CLI の `--parameters`、PowerShell の `-TemplateParameterFile`、Portal の入力フォームなどから渡せます。セキュア値は `secureString` や `secureObject` で扱い、Key Vault 統合も可能です（[パラメーターの定義](https://learn.microsoft.com/azure/azure-resource-manager/templates/parameters)、[セキュア パラメーター](https://learn.microsoft.com/azure/azure-resource-manager/templates/secure-parameters)）。
- **default値の設定例**
  ```json
  "parameters": {
    "storageSku": {
      "type": "string",
      "defaultValue": "Standard_LRS",
      "allowedValues": [
        "Standard_LRS",
        "Standard_GRS",
        "Standard_RAGRS",
        "Standard_ZRS"
      ],
      "metadata": {
        "description": "ストレージ アカウントの SKU。未指定時は Standard_LRS を利用。"
      }
    }
  }
  ```
  値が未指定でも既定値が使われ、許可されていない値は検証で弾かれます。

### 3.4 実行方法
- **Azure Portal（テンプレートのデプロイ機能）**: Portal の「リソースの作成」→「テンプレートのデプロイ (独自のテンプレートを作成)」で JSON をアップロードし、パラメーター入力後にデプロイします。テンプレートを「マイ テンプレート」として保存すると再利用できます（[Portal からのデプロイ](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-portal)）。
- **Azure CLI / PowerShell**: CLI の `az deployment group create`、PowerShell の `New-AzResourceGroupDeployment` などでテンプレートとパラメーターを指定。`--what-if` や `-Mode Complete` など、差分確認・完全同期モードも活用できます（[CLI からのデプロイ](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-cli)、[PowerShell からのデプロイ](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-powershell)）。
- **CI/CD（GitHub Actions, Azure DevOps）**: GitHub Actions の `azure/login`＋`azure/arm-deploy`、Azure DevOps の `AzureResourceManagerTemplateDeployment@3` タスクを利用すると、プッシュやプルリクに連動してテンプレート検証・デプロイが自動化できます（[GitHub Actions でのデプロイ](https://learn.microsoft.com/azure/azure-resource-manager/templates/deploy-github-actions)、[Azure DevOps でのパイプライン](https://learn.microsoft.com/azure/azure-resource-manager/templates/deployment-tutorial-pipeline)）。

---

次のハンズオンでは、この資料で理解した ARM の役割とテンプレートの基本構造を踏まえ、実際にテンプレートを書きながら Azure リソースをデプロイしていきます。不明点があれば公式ドキュメントを参照し、自分なりのメモを残しておくと復習がスムーズです。
