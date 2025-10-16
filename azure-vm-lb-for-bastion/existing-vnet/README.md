# Azure 踏み台VM + Private Link + Internal Load Balancer（既存VNet利用版）

オンプレミス環境から Azure 内の複数踏み台VMに対して、Private Link Service経由でセキュアにSSH接続するための Infrastructure as Code (IaC) テンプレートです。

**このバージョンは既存のVNetとSubnet（Peering接続済み）を利用します。**

## このバージョンの特徴

- ✅ 既存VNet/Subnetを利用
- ✅ 既存VNet Peeringを活用
- ✅ NSGは既存のものを利用可能（オプション作成も可）
- ✅ 既存環境・本番環境に最適

## 適用シナリオ

- 既存環境への追加
- 本番環境
- ネットワーク設計が確定済み
- Peering接続が設定済み

## デプロイ対象リソース

- Internal Load Balancer + NAT Rules
- Private Link Service
- Private Endpoint（Hub VNet内）
- 踏み台VM（複数台）
- Azure SSH Public Key
- Network Security Groups（オプション）

## アーキテクチャ

```
オンプレミス (ExpressRoute/VPN)
    ↓
Hub VNet (Private Endpoint - 新規)
    ↓ Private Link接続
VNet-A (LB用RG) - 既存
    ├─ Private Link Service - 新規
    └─ Internal Load Balancer - 新規
        ↓ VNet Peering - 既存
VNet-B (VM用RG) - 既存
    ├─ 踏み台VM1 (Port 2201 → 22) - 新規
    ├─ 踏み台VM2 (Port 2202 → 22) - 新規
    └─ 踏み台VM3 (Port 2203 → 22) - 新規
```

詳細な構成図は [docs/architecture.md](./docs/architecture.md) を参照してください。

## 前提条件

### 必須の既存リソース

以下のリソースが**事前に構築済み**である必要があります：

#### 1. Hub VNet
- ExpressRoute / VPN Gateway 接続済み
- Private Endpoint用Subnetが存在

#### 2. LB用VNet
- **LB Subnet**: Internal Load Balancer配置用（最低5個以上のIPアドレス）
- **PLS Subnet**: Private Link Service配置用（`privateLinkServiceNetworkPolicies` が `Disabled`）

#### 3. VM用VNet
- **VM Subnet**: 踏み台VM配置用（VM台数分のIPアドレス確保）

#### 4. VNet Peering
- LB用VNet ⇔ VM用VNet 間で**双方向**Peering設定済み
- Peering状態が `Connected` であること

### その他

- Azure CLI (`az`) インストール済み
- Bicep CLI インストール済み
- Azure サブスクリプションへのContributor以上の権限

## デプロイ手順

### 1. 既存リソースのリソースIDを取得

```bash
# LB Subnet ID
az network vnet subnet show \
  --resource-group <LB_RG_NAME> \
  --vnet-name <LB_VNET_NAME> \
  --name snet-lb \
  --query id -o tsv

# PLS Subnet ID
az network vnet subnet show \
  --resource-group <LB_RG_NAME> \
  --vnet-name <LB_VNET_NAME> \
  --name snet-pls \
  --query id -o tsv

# VM Subnet ID
az network vnet subnet show \
  --resource-group <VM_RG_NAME> \
  --vnet-name <VM_VNET_NAME> \
  --name snet-vm \
  --query id -o tsv
```

### 2. パラメータファイルの編集

`bicep/parameters/main.parameters.json` を編集します：

```json
{
  "hubPeSubnetId": {
    "value": "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-hub/providers/Microsoft.Network/virtualNetworks/vnet-hub/subnets/snet-pe"
  },
  "lbSubnetId": {
    "value": "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<LB_RG>/providers/Microsoft.Network/virtualNetworks/<LB_VNET>/subnets/snet-lb"
  },
  "plsSubnetId": {
    "value": "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<LB_RG>/providers/Microsoft.Network/virtualNetworks/<LB_VNET>/subnets/snet-pls"
  },
  "vmSubnetId": {
    "value": "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<VM_RG>/providers/Microsoft.Network/virtualNetworks/<VM_VNET>/subnets/snet-vm"
  },
  "deployNsgs": {
    "value": false
  }
}
```

**重要パラメータ:**
- `deployNsgs`: 既存NSGがある場合は `false`、新規作成する場合は `true`
- `lbSubnetPrefix`: NSGルール作成に使用（既存SubnetのCIDR範囲）

### 3. VNet Peeringの確認

```bash
# Peering状態確認
az network vnet peering show \
  --resource-group <LB_RG_NAME> \
  --vnet-name <LB_VNET_NAME> \
  --name <PEERING_NAME> \
  --query peeringState
```

両方向とも `Connected` であることを確認してください。

### 4. デプロイスクリプトの実行

```bash
cd scripts
chmod +x deploy.sh
./deploy.sh
```

スクリプトは以下を実行します：

1. 前提条件チェック
2. パラメータファイル検証
3. 既存リソース確認（手動確認プロンプト）
4. Bicepテンプレートビルド
5. what-if検証（オプション）
6. デプロイ実行
7. SSH キー接続方法案内
8. Private Link Service接続承認

### 5. Private Link接続の承認

```bash
az network private-endpoint-connection approve \
  --name <connection-name> \
  --resource-name pls-bastion \
  --resource-group rg-lb-bastion \
  --type Microsoft.Network/privateLinkServices \
  --description "Approved for onpremise access"
```

### 6. SSH接続

#### 方法1: Azure CLI SSH（推奨）

```bash
az ssh vm --resource-group rg-vm-bastion --name vm-bastion-1
```

#### 方法2: Azure Portal から秘密鍵をダウンロード

1. Azure Portal → `rg-vm-bastion` → `ssh-bastion`
2. 「Download private key」をクリック
3. SSH接続:
   ```bash
   ssh -i ~/Downloads/ssh-bastion.pem azureuser@<Private-Endpoint-IP> -p 2201
   ```

## トラブルシューティング

### Subnet not found エラー

パラメータファイルのSubnetリソースIDを確認してください。

```bash
az network vnet subnet show \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <SUBNET_NAME> \
  --query id -o tsv
```

### VNet Peering が Connected でない

```bash
# Peering状態確認
az network vnet peering list \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --query "[].{Name:name, State:peeringState}" -o table

# Peering 再同期
az network vnet peering sync \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <PEERING_NAME>
```

### Private Link Service の NetworkPolicies エラー

```bash
# ネットワークポリシーを無効化
az network vnet subnet update \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name snet-pls \
  --disable-private-link-service-network-policies true
```

詳細は [docs/architecture.md](./docs/architecture.md) を参照してください。

## クリーンアップ

```bash
# デプロイしたリソースのみ削除
az group delete --name rg-lb-bastion --yes --no-wait
az group delete --name rg-vm-bastion --yes --no-wait
az network private-endpoint delete --name pe-bastion-pls --resource-group rg-hub
```

**注意:** 既存のVNet/Subnet/Peeringは削除されません。

## 新規VNet版との比較

新規環境を構築する場合は、[新規VNet作成版](../new-vnet/) を使用してください。

| 項目 | 既存VNet版（このバージョン） | 新規VNet版 |
|------|---------------------------|-----------|
| VNet作成 | ❌ 既存利用 | ✅ 新規作成 |
| VNet Peering | ❌ 既存前提 | ✅ 新規作成 |
| 適用環境 | 既存・本番 | 新規・検証 |

## 参考リンク

- [既存リソースの参照 (Bicep)](https://learn.microsoft.com/azure/azure-resource-manager/bicep/existing-resource)
- [VNet Peering トラブルシューティング](https://learn.microsoft.com/azure/virtual-network/virtual-network-troubleshoot-peering-issues)
- [Private Link Service ネットワークポリシー](https://learn.microsoft.com/azure/private-link/disable-private-link-service-network-policy)
- [Azure Load Balancer](https://learn.microsoft.com/azure/load-balancer/load-balancer-overview)

## ライセンス

MIT License
