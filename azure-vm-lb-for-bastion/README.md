# Azure 踏み台VM + Private Link + Internal Load Balancer

オンプレミス環境から Azure 内の複数踏み台VMに対して、Private Link Service経由でセキュアにSSH接続するためのInfrastructure as Code (IaC) テンプレートです。

## 概要

この構成は以下の要件を満たします：

- オンプレミスから Azure 踏み台VMへの**完全プライベート接続**（インターネット非経由）
- 複数踏み台VMへの**単一エントリポイント**（Private Link Service経由）
- 異なるリソースグループ・VNet間での**柔軟なリソース配置**
- **Azure Bastion非採用**（ローカルからの直接SSH接続要件のため）
- **Azure 管理のSSH キー**（自動生成・安全管理）

## 2つのバージョン

環境に応じて選択できる**2つのバージョン**を用意しています：

### 🆕 [新規VNet作成版](./new-vnet/)

VNetとSubnetを新規作成し、VNet Peeringも自動設定します。

**📂 フォルダ:** `new-vnet/`

**適用シナリオ:**
- 新規環境の構築
- 検証・テスト環境
- ネットワーク設計が未確定

**デプロイ対象:**
- VNet + Subnet（LB用、VM用）
- VNet Peering（双方向）
- NSG
- Internal Load Balancer
- Private Link Service
- 踏み台VM

📖 **ドキュメント:** [new-vnet/README.md](./new-vnet/README.md) | [new-vnet/docs/architecture.md](./new-vnet/docs/architecture.md)

---

### 🏢 [既存VNet利用版](./existing-vnet/)

既存のVNetとSubnet（Peering接続済み）を利用します。

**📂 フォルダ:** `existing-vnet/`

**適用シナリオ:**
- 既存環境への追加
- 本番環境
- ネットワーク設計が確定済み
- Peering接続が設定済み

**デプロイ対象:**
- Internal Load Balancer
- Private Link Service
- 踏み台VM

📖 **ドキュメント:** [existing-vnet/README.md](./existing-vnet/README.md) | [existing-vnet/docs/architecture.md](./existing-vnet/docs/architecture.md)

---

## どちらを選ぶべきか？

| 判断基準 | 新規VNet版 | 既存VNet版 |
|---------|----------|----------|
| VNetが既に存在する | ❌ | ✅ |
| Peering接続が設定済み | ❌ | ✅ |
| 本番環境への追加 | ❌ | ✅ |
| 新規環境の構築 | ✅ | ❌ |
| 迅速な検証が必要 | ✅ | ❌ |

## クイックスタート

### 新規VNet作成版

```bash
cd new-vnet
# パラメータファイルを編集
vi bicep/parameters/main.parameters.json
# デプロイ
cd scripts && chmod +x deploy.sh && ./deploy.sh
```

### 既存VNet利用版

```bash
cd existing-vnet
# パラメータファイルを編集（既存リソースIDを指定）
vi bicep/parameters/main.parameters.json
# デプロイ
cd scripts && chmod +x deploy.sh && ./deploy.sh
```

## フォルダ構成

```
azure-vm-lb-for-bastion/
├── new-vnet/                               # 新規VNet作成版
│   ├── bicep/
│   │   ├── main.bicep
│   │   ├── modules/                        # 全モジュール
│   │   └── parameters/
│   ├── scripts/
│   │   └── deploy.sh
│   ├── docs/
│   │   └── architecture.md
│   └── README.md
│
├── existing-vnet/                          # 既存VNet利用版
│   ├── bicep/
│   │   ├── main.bicep
│   │   ├── modules/                        # 必要なモジュールのみ
│   │   └── parameters/
│   ├── scripts/
│   │   └── deploy.sh
│   ├── docs/
│   │   └── architecture.md
│   └── README.md
│
└── README.md                               # 本ファイル
```

## 主な機能

### セキュリティ

- ✅ パブリックIP不要の完全プライベート構成
- ✅ Private Link Service経由の閉域接続
- ✅ NSGによる最小権限の原則
- ✅ SSH公開鍵認証必須（パスワード認証無効）
- ✅ Azure 管理のSSH キー（自動生成）

### 柔軟性

- ✅ 複数VMへの統一エントリポイント
- ✅ NAT Rulesによるポート分散（2201, 2202, 2203...）
- ✅ VMの台数を1〜10台で柔軟に設定可能
- ✅ 異なるRG/VNet間での分離配置

### 運用性

- ✅ Infrastructure as Code（Bicep）
- ✅ 自動デプロイスクリプト
- ✅ Azure CLI SSH統合
- ✅ what-if検証機能

## アーキテクチャ概要

```
オンプレミス環境
    ↓ ExpressRoute / VPN
Hub VNet
    ↓ Private Endpoint
Private Link Service
    ↓
Internal Load Balancer
    ├─ NAT: Port 2201 → VM1:22
    ├─ NAT: Port 2202 → VM2:22
    └─ NAT: Port 2203 → VM3:22
    ↓ VNet Peering
踏み台VM群（VNet-B内）
```

## SSH接続方法

デプロイ後、以下の方法でSSH接続できます：

### Azure CLI SSH（推奨）

```bash
az ssh vm --resource-group rg-vm-bastion --name vm-bastion-1
```

### 秘密鍵をダウンロードして接続

```bash
# Azure Portalから秘密鍵をダウンロード
# Portal → rg-vm-bastion → ssh-bastion → "Download private key"

# SSH接続（オンプレミスから）
ssh -i ~/Downloads/ssh-bastion.pem azureuser@<Private-Endpoint-IP> -p 2201
```

## 参考リンク

- [Azure Private Link](https://learn.microsoft.com/azure/private-link/private-link-overview)
- [Azure Load Balancer](https://learn.microsoft.com/azure/load-balancer/load-balancer-overview)
- [VNet Peering](https://learn.microsoft.com/azure/virtual-network/virtual-network-peering-overview)
- [Azure Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure SSH Public Keys](https://learn.microsoft.com/azure/virtual-machines/ssh-keys-azure-cli)

## ライセンス

MIT License

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2025-10-16 | 初版作成（新規VNet作成版） |
| 2025-10-16 | 既存VNet利用版を追加 |
| 2025-10-16 | フォルダ構成を分離（new-vnet / existing-vnet） |
