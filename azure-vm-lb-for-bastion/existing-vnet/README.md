# Azure 踏み台VM + Private Link + Internal Load Balancer（既存VNet利用版）

外部VNetから Azure 内の踏み台VMに対して、Private Link Service経由でセキュアにSSH接続するための Infrastructure as Code (IaC) テンプレートです。

**このバージョンは既存のVNetを利用し、必要なSubnetを新規作成します。同一VNet内にLB、Private Link Service、VMを配置します。**

## このバージョンの特徴

- ✅ 既存VNetを利用（Subnetは新規作成）
- ✅ 同一VNet内に全リソースを配置（LB、PLS、VM）
- ✅ NSGは常に新規作成
- ✅ 既存環境・本番環境に最適
- ✅ VMは1台固定（シンプル構成）
- ✅ パスワード認証（SSHキーは後から追加）

## 適用シナリオ

- 既存環境への追加
- 本番環境
- ネットワーク設計が確定済み
- 同一VNet内での構成が望ましい場合

## デプロイ対象リソース

- Subnet × 3（LB用、PLS用、VM用）
- Network Security Groups × 3（LB用、PLS用、VM用）
- Internal Load Balancer + NAT Rules
- Private Link Service
- 踏み台VM（1台、パスワード認証）

**注意:**
- Private Endpointは含まれません（外部VNetから別途作成）
- SSHキーは含まれません（デプロイ後にAzure Portalから追加）
- VNetは既存のものを利用します

## アーキテクチャ

```
外部VNet（Hub VNet等）
    └─ Private Endpoint（別途作成）
        ↓ Private Link接続
VNet (既存) - 同一VNet内に全リソースを配置
    ├─ [LB Subnet] Internal Load Balancer - 新規
    ├─ [PLS Subnet] Private Link Service - 新規
    └─ [VM Subnet] 踏み台VM (Port 2201 → 22) - 新規
```

詳細な構成図は [docs/architecture.md](./docs/architecture.md) を参照してください。

## 前提条件

### 必須の既存リソース

以下のリソースが**事前に構築済み**である必要があります：

#### 1. VNet
- 既存のVNetが必要です
- VNetには新規Subnet作成に必要な十分なアドレス空間が必要です
- 推奨: 最低3つの /24 Subnet分のアドレス空間（例: /16 VNet）

**注意:** Subnetは自動作成されます。事前に作成する必要はありません。

### その他

- Azure CLI (`az`) インストール済み
- Bicep CLI インストール済み
- Azure サブスクリプションへのContributor以上の権限

## デプロイ手順

### 1. 既存VNetの情報を取得

既存のVNetのリソースIDと名前を確認します：

```bash
# VNet リソースID
az network vnet show \
  --resource-group <VNET_RG_NAME> \
  --name <VNET_NAME> \
  --query id -o tsv

# VNet アドレス空間の確認
az network vnet show \
  --resource-group <VNET_RG_NAME> \
  --name <VNET_NAME> \
  --query addressSpace.addressPrefixes -o table
```

### 2. パラメータファイルの編集

`bicep/parameters/main.parameters.json` を編集します：

```json
{
  "vnetId": {
    "value": "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<VNET_RG_NAME>/providers/Microsoft.Network/virtualNetworks/<VNET_NAME>"
  },
  "vnetResourceGroup": {
    "value": "<VNET_RG_NAME>"
  },
  "vnetName": {
    "value": "<VNET_NAME>"
  },
  "lbSubnetPrefix": {
    "value": "10.1.1.0/24"
  },
  "plsSubnetPrefix": {
    "value": "10.1.2.0/24"
  },
  "vmSubnetPrefix": {
    "value": "10.1.3.0/24"
  },
  "ilbPrivateIp": {
    "value": "10.1.1.4"
  },
  "adminUsername": {
    "value": "azureuser"
  },
  "adminPassword": {
    "value": "YourSecurePassword123!"
  }
}
```

**重要パラメータ:**
- `vnetId`: 既存VNetのリソースID
- `vnetResourceGroup`: 既存VNetが所属するリソースグループ名
- `vnetName`: 既存VNet名
- `lbSubnetPrefix` / `plsSubnetPrefix` / `vmSubnetPrefix`: 新規作成するSubnetのCIDR範囲（VNetのアドレス空間内で未使用の範囲を指定）
- `ilbPrivateIp`: Internal Load BalancerのプライベートIP（lbSubnetPrefix内のIPアドレス）
- `adminPassword`: 最低12文字、大文字・小文字・数字・記号を含む

### 3. デプロイの実行

```bash
cd bicep
az deployment sub create \
  --location japaneast \
  --template-file main.bicep \
  --parameters parameters/main.parameters.json
```

### 4. 接続方法

#### 同一VNet内からの接続

```bash
# 同一VNet内のVMやリソースから
ssh azureuser@10.1.1.4 -p 2201
```

#### 外部VNetからの接続（Private Endpoint経由）

外部VNetから接続する場合は、以下の手順でPrivate Endpointを作成してください：

1. デプロイ出力から Private Link Service Alias を取得

```bash
az deployment sub show \
  --name <DEPLOYMENT_NAME> \
  --query properties.outputs.plsAlias.value -o tsv
```

2. 外部VNet（Hub VNet等）に Private Endpoint を作成

```bash
az network private-endpoint create \
  --resource-group <HUB_RG_NAME> \
  --name pe-bastion \
  --vnet-name <HUB_VNET_NAME> \
  --subnet <HUB_SUBNET_NAME> \
  --private-connection-resource-id <PLS_RESOURCE_ID> \
  --connection-name conn-bastion \
  --manual-request true \
  --request-message "Connection from Hub VNet"
```

### 5. Private Link接続の承認

Private Endpoint作成後、接続を承認します：

```bash
az network private-endpoint-connection approve \
  --name <connection-name> \
  --resource-name pls-bastion \
  --resource-group rg-lb-bastion \
  --type Microsoft.Network/privateLinkServices \
  --description "Approved for onpremise access"
```

### 6. SSHキーの追加（オプション）

デプロイ後、Azure Portal からSSHキーを追加できます：

1. Azure Portal → `rg-vm-bastion` → `vm-bastion-1`
2. 「Connect」→「SSH using Azure CLI」
3. SSHキーをアップロードまたは生成
4. 以降はパスワード不要でSSH接続可能

```bash
# SSHキー追加後
az ssh vm --resource-group rg-vm-bastion --name vm-bastion-1
```

## トラブルシューティング

### VNet not found エラー

パラメータファイルのVNetリソースIDが正しいか確認してください。

```bash
az network vnet show \
  --resource-group <VNET_RG_NAME> \
  --name <VNET_NAME> \
  --query id -o tsv
```

### Subnet アドレス範囲の重複エラー

指定したSubnet CIDRが既存Subnetと重複している場合、エラーが発生します。

```bash
# 既存Subnetの確認
az network vnet subnet list \
  --resource-group <VNET_RG_NAME> \
  --vnet-name <VNET_NAME> \
  --query "[].{Name:name, AddressPrefix:addressPrefix}" -o table
```

未使用のアドレス範囲を指定してください。

### NSGによる通信ブロック

既存のNSGルールが通信をブロックしている可能性があります：

```bash
# 有効なNSGルールを確認
az network nic show-effective-nsg \
  --name vm-bastion-1-nic \
  --resource-group rg-vm-bastion

# 必要に応じてNSGルールを追加
az network nsg rule create \
  --resource-group <RG_NAME> \
  --nsg-name <NSG_NAME> \
  --name Allow-SSH-from-ILB \
  --priority 100 \
  --source-address-prefixes "10.1.1.0/24" \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp
```

詳細は [docs/architecture.md](./docs/architecture.md) を参照してください。

## クリーンアップ

```bash
# デプロイしたリソースのみ削除
az group delete --name rg-lb-bastion --yes --no-wait
az group delete --name rg-vm-bastion --yes --no-wait
```

**注意:**
- 既存のVNet/Subnetは削除されません
- Private Endpointは別途削除が必要です（外部VNetにある場合）

## 新規VNet版との比較

新規環境を構築する場合は、[新規VNet作成版](../new-vnet/) を使用してください。

| 項目 | 既存VNet版（このバージョン） | 新規VNet版 |
|------|---------------------------|-----------|
| VNet作成 | ❌ 既存利用 | ✅ 新規作成 |
| Load Balancer | Internal LB | Public LB |
| Private Link Service | ✅ あり | ❌ なし |
| VM台数 | 1台固定 | 1台固定 |
| 認証方式 | パスワード認証 | パスワード認証 |
| 適用環境 | 既存・本番 | 新規・検証 |

## 参考リンク

- [既存リソースの参照 (Bicep)](https://learn.microsoft.com/azure/azure-resource-manager/bicep/existing-resource)
- [Private Link Service ネットワークポリシー](https://learn.microsoft.com/azure/private-link/disable-private-link-service-network-policy)
- [Azure Load Balancer](https://learn.microsoft.com/azure/load-balancer/load-balancer-overview)
- [Azure Private Link Service](https://learn.microsoft.com/azure/private-link/private-link-service-overview)
- [詳細なアーキテクチャドキュメント](./docs/architecture.md)

## ライセンス

MIT License
