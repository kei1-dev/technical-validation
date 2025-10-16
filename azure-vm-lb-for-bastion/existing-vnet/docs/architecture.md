# Azure 踏み台VM + Private Link + Internal Load Balancer 構成（既存VNet版）

既存のVNet・Subnet（Peering接続済み）を利用して、オンプレミス環境から Azure 内の複数踏み台VMに対して Private Link Service経由でセキュアにSSH接続するためのアーキテクチャです。

---

## 目次

1. [概要](#概要)
2. [新規VNet版との違い](#新規vnet版との違い)
3. [アーキテクチャ図](#アーキテクチャ図)
4. [前提条件](#前提条件)
5. [コンポーネント詳細](#コンポーネント詳細)
6. [デプロイ手順](#デプロイ手順)
7. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### 設計目標

- **既存VNetを活用**: 新たにVNetを作成せず、既存のネットワークインフラを利用
- **Peering接続済み前提**: LB用VNetとVM用VNetは既にPeering接続されている
- オンプレミスから Azure 踏み台VMへの**完全プライベート接続**（インターネット非経由）
- 複数踏み台VMへの**単一エントリポイント**（Private Link Service経由）

### 適用シナリオ

このバージョンは以下のケースに最適です：

1. **既存ネットワーク環境への追加**: 既にVNetとSubnetが構築済みの環境
2. **ネットワーク設計が確定済み**: VNetアドレス範囲やSubnet設計が既に完了
3. **Peering接続が設定済み**: VNet間の通信経路が確立済み
4. **最小限の変更**: 既存ネットワークに影響を与えず、LBとVMのみをデプロイ

---

## 新規VNet版との違い

| 項目 | 新規VNet版 (`main.bicep`) | 既存VNet版 (`main-existing-vnet.bicep`) |
|------|-------------------------|--------------------------------------|
| **VNet作成** | 新規作成 | 既存VNetを利用 |
| **Subnet作成** | 新規作成 | 既存Subnetを利用 |
| **VNet Peering** | 新規作成 | 既存Peering接続を利用 |
| **NSG** | 新規作成（デフォルト） | オプション（`deployNsgs`パラメータで制御） |
| **パラメータ** | VNetアドレス範囲を指定 | SubnetリソースIDを指定 |
| **デプロイ対象** | VNet + LB + VM | LB + VM のみ |
| **適用環境** | 新規環境、検証環境 | 既存環境、本番環境 |

---

## アーキテクチャ図

### 全体構成

```mermaid
graph TB
    subgraph OnPrem["オンプレミス環境"]
        Client["管理者PC<br/>(SSH Client)"]
    end

    subgraph Azure["Azure Cloud"]
        subgraph HubVNet["Hub VNet<br/>(既存: オンプレ接続用)"]
            ER["ExpressRoute<br/>Gateway"]
            PE["Private Endpoint<br/>(新規デプロイ)"]
        end

        subgraph RG_A["RG-A: LB用リソースグループ"]
            subgraph VNetA["VNet-A (既存)<br/>(10.1.0.0/16)"]
                subgraph SubnetLB["LB Subnet (既存)<br/>(10.1.1.0/24)"]
                    ILB["Internal Load Balancer<br/>(新規デプロイ)"]
                end
                subgraph SubnetPLS["PLS Subnet (既存)<br/>(10.1.2.0/24)"]
                    PLS["Private Link Service<br/>(新規デプロイ)"]
                end
            end
        end

        subgraph RG_B["RG-B: VM用リソースグループ"]
            subgraph VNetB["VNet-B (既存)<br/>(10.2.0.0/16)"]
                subgraph SubnetVM["VM Subnet (既存)<br/>(10.2.1.0/24)"]
                    VM1["踏み台VM1<br/>(新規デプロイ)"]
                    VM2["踏み台VM2<br/>(新規デプロイ)"]
                    VM3["踏み台VM3<br/>(新規デプロイ)"]
                end
            end
        end
    end

    Client -->|ExpressRoute/VPN| ER
    ER --> PE
    PE -->|プライベート接続| PLS
    PLS --> ILB
    ILB -->|NAT: 2201→22| VM1
    ILB -->|NAT: 2202→22| VM2
    ILB -->|NAT: 2203→22| VM3
    VNetA -.->|VNet Peering<br/>(既存)| VNetB

    style OnPrem fill:#f9f,stroke:#333,stroke-width:2px
    style Azure fill:#e1f5ff,stroke:#333,stroke-width:2px
    style HubVNet fill:#fff4e6,stroke:#ff9800,stroke-width:2px
    style RG_A fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style RG_B fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style VNetA stroke:#666,stroke-width:3px,stroke-dasharray: 5 5
    style VNetB stroke:#666,stroke-width:3px,stroke-dasharray: 5 5
```

**凡例:**
- 実線枠: 新規デプロイされるリソース
- 破線枠: 既存のリソース

---

## 前提条件

### 既存リソース要件

以下のリソースが**事前に構築済み**である必要があります：

#### 1. Hub VNet
- ExpressRoute または VPN Gateway が接続済み
- Private Endpoint用のSubnetが存在

#### 2. LB用VNet (VNet-A)
- **LB Subnet**: Internal Load Balancer配置用
  - 推奨サイズ: `/24` 以上
  - 利用可能なIPアドレスが最低5個以上
- **PLS Subnet**: Private Link Service配置用
  - 推奨サイズ: `/24` 以上
  - `privateLinkServiceNetworkPolicies` が `Disabled` であること

#### 3. VM用VNet (VNet-B)
- **VM Subnet**: 踏み台VM配置用
  - 推奨サイズ: `/24` 以上
  - VMの台数分のIPアドレスが確保可能

#### 4. VNet Peering
- VNet-A ⇔ VNet-B 間でPeeringが**双方向**に設定済み
- Peering状態が `Connected` であること

#### 5. その他
- Azure CLI (`az`) インストール済み
- Bicep CLI インストール済み
- Azure サブスクリプションへのContributor以上の権限

---

## コンポーネント詳細

### デプロイされるリソース

| リソース | 種類 | 配置先 | 詳細 |
|---------|------|--------|------|
| SSH Public Key | Microsoft.Compute/sshPublicKeys | RG-B (VM用RG) | Azure生成のSSHキーペア |
| Internal Load Balancer | Microsoft.Network/loadBalancers | RG-A (LB用RG) | Standard SKU、NAT Rules設定 |
| Private Link Service | Microsoft.Network/privateLinkServices | RG-A (LB用RG) | ILBのフロントエンドを公開 |
| Private Endpoint | Microsoft.Network/privateEndpoints | Hub VNet RG | PLSへの接続エンドポイント |
| 踏み台VM (複数台) | Microsoft.Compute/virtualMachines | RG-B (VM用RG) | Ubuntu 22.04 LTS |
| NSG (オプション) | Microsoft.Network/networkSecurityGroups | RG-A, RG-B | `deployNsgs=true` の場合のみ |

### 既存リソースの参照方法

Bicepテンプレートでは、以下のようにリソースIDで既存リソースを参照します：

```bicep
// パラメータでSubnetリソースIDを受け取る
param lbSubnetId string

// Internal Load Balancerデプロイ時に既存Subnetを指定
module ilb 'modules/internal-lb.bicep' = {
  params: {
    subnetId: lbSubnetId  // 既存SubnetのリソースID
  }
}
```

---

## デプロイ手順

### 1. 既存リソースのリソースIDを取得

既存のSubnetリソースIDを取得します。

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

# Hub PE Subnet ID
az network vnet subnet show \
  --resource-group rg-hub \
  --vnet-name vnet-hub \
  --name snet-pe \
  --query id -o tsv
```

### 2. パラメータファイルの編集

`bicep/parameters/main-existing-vnet.parameters.json` を編集します：

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
  "lbSubnetPrefix": {
    "value": "10.1.1.0/24"
  },
  "deployNsgs": {
    "value": false
  }
}
```

**重要パラメータ:**
- `lbSubnetPrefix`: NSGルール作成に使用（既存SubnetのCIDR範囲）
- `deployNsgs`: 既存NSGがある場合は `false` に設定

### 3. VNet Peeringの確認

VNet間のPeering接続が正常であることを確認します。

```bash
# VNet-A → VNet-B のPeering状態確認
az network vnet peering show \
  --resource-group <LB_RG_NAME> \
  --vnet-name <LB_VNET_NAME> \
  --name <PEERING_NAME> \
  --query peeringState

# VNet-B → VNet-A のPeering状態確認
az network vnet peering show \
  --resource-group <VM_RG_NAME> \
  --vnet-name <VM_VNET_NAME> \
  --name <PEERING_NAME> \
  --query peeringState
```

両方とも `Connected` であることを確認してください。

### 4. デプロイスクリプトの実行

```bash
cd scripts
chmod +x deploy-existing-vnet.sh
./deploy-existing-vnet.sh
```

スクリプトは以下を実行します：

1. 前提条件チェック
2. パラメータファイル検証
3. 既存リソース確認（手動確認プロンプト）
4. what-if検証（オプション）
5. デプロイ実行
6. SSH接続方法案内
7. Private Link接続承認

### 5. Private Link接続の承認

```bash
az network private-endpoint-connection approve \
  --name <connection-name> \
  --resource-name pls-bastion \
  --resource-group rg-lb-bastion \
  --type Microsoft.Network/privateLinkServices \
  --description "Approved for onpremise access"
```

---

## トラブルシューティング

### 問題: Subnet not found エラー

**原因:**
- パラメータファイルのSubnetリソースIDが間違っている
- 指定したSubnetが存在しない

**対処:**
```bash
# リソースIDの形式を確認
az network vnet subnet show \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <SUBNET_NAME> \
  --query id -o tsv
```

### 問題: VNet Peering not connected

**原因:**
- VNet Peering が正しく設定されていない
- Peering状態が `Disconnected` または `Pending`

**対処:**
```bash
# Peering状態を確認
az network vnet peering list \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --query "[].{Name:name, State:peeringState}" -o table

# Peering を再同期
az network vnet peering sync \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name <PEERING_NAME>
```

### 問題: Private Link Service の Subnet で NetworkPolicies エラー

**原因:**
- PLS SubnetでPrivate Link Service用のネットワークポリシーが有効になっている

**対処:**
```bash
# ネットワークポリシーを無効化
az network vnet subnet update \
  --resource-group <RG_NAME> \
  --vnet-name <VNET_NAME> \
  --name snet-pls \
  --disable-private-link-service-network-policies true
```

### 問題: NSG との競合

既存のNSGルールが通信をブロックしている可能性があります。

**対処:**
```bash
# 有効なNSGルールを確認
az network nic show-effective-nsg \
  --name <VM_NIC_NAME> \
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

---

## 参考リンク

- [既存リソースの参照 (Bicep)](https://learn.microsoft.com/azure/azure-resource-manager/bicep/existing-resource)
- [VNet Peering のトラブルシューティング](https://learn.microsoft.com/azure/virtual-network/virtual-network-troubleshoot-peering-issues)
- [Private Link Service のネットワークポリシー](https://learn.microsoft.com/azure/private-link/disable-private-link-service-network-policy)
- [Azure Load Balancer のトラブルシューティング](https://learn.microsoft.com/azure/load-balancer/load-balancer-troubleshoot)

---

## 変更履歴

| 日付 | 変更内容 | 作成者 |
|------|---------|--------|
| 2025-10-16 | 初版作成（既存VNet版） | - |
