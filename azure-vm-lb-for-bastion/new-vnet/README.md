# Azure 踏み台VM + Public Load Balancer（新規VNet作成版）

インターネットから Azure 内の複数踏み台VMに対して、Public Load Balancer経由でセキュアにSSH接続するための Infrastructure as Code (IaC) テンプレートです。

**このバージョンは新規にVNetとSubnetを作成し、パブリックIPを持つLoad Balancerでインターネットからアクセスできます。**

## このバージョンの特徴

- ✅ VNetとSubnetを新規作成
- ✅ パブリックIPでインターネットからアクセス可能
- ✅ NSGで送信元IP制限可能
- ✅ 新規環境・検証環境に最適

## 適用シナリオ

- 新規環境の構築
- 検証・テスト環境
- インターネットからの直接アクセスが必要な場合
- オンプレミス接続がない環境

## デプロイ対象リソース

- VNet + Subnet（VM用）
- Network Security Groups
- Public IP Address
- Public Load Balancer + NAT Rules
- 踏み台VM（複数台）
- Azure SSH Public Key

## アーキテクチャ

```
インターネット
    ↓ SSH (パブリックIP:2201, 2202, 2203...)
Public Load Balancer (パブリックIP) - 新規作成
    ├─ NAT: Port 2201 → VM1:22
    ├─ NAT: Port 2202 → VM2:22
    └─ NAT: Port 2203 → VM3:22
        ↓
VNet (VM用RG) - 新規作成
    ├─ 踏み台VM1
    ├─ 踏み台VM2
    └─ 踏み台VM3
```

詳細な構成図は [docs/architecture.md](./docs/architecture.md) を参照してください。

## 前提条件

- Azure CLI (`az`) インストール済み
- Bicep CLI インストール済み (`az bicep install`)
- Azure サブスクリプションへのContributor以上の権限

**注意:** SSH キーペアは Azure が自動生成するため、事前準備は不要です。

## デプロイ手順

### 1. パラメータファイルの編集

`bicep/parameters/main.parameters.json` を編集します：

```json
{
  "hubPeSubnetId": {
    "value": "/subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-hub/providers/Microsoft.Network/virtualNetworks/vnet-hub/subnets/snet-pe"
  },
  "adminUsername": {
    "value": "azureuser"
  },
  "sshKeyName": {
    "value": "ssh-bastion"
  },
  "vmCount": {
    "value": 3
  }
}
```

**必須変更項目:**
- `<YOUR_SUBSCRIPTION_ID>`: 実際のサブスクリプションIDに置き換え

**オプション変更項目:**
- `vmCount`: 踏み台VMの台数（1〜10）
- `vmSize`: VMサイズ（デフォルト: `Standard_B2s`）
- `lbVnetAddressPrefix`, `vmVnetAddressPrefix`: VNetアドレス範囲

### 2. デプロイスクリプトの実行

```bash
cd scripts
chmod +x deploy.sh
./deploy.sh
```

スクリプトは以下を自動実行します：

1. 前提条件チェック
2. パラメータファイル検証
3. Bicepテンプレートビルド
4. what-if検証（オプション）
5. デプロイ実行
6. SSH キー接続方法案内
7. Private Link Service接続承認

### 3. 手動デプロイ（スクリプトを使わない場合）

```bash
# Bicepビルド
az bicep build --file bicep/main.bicep

# What-if検証
az deployment sub what-if \
  --location japaneast \
  --template-file bicep/main.bicep \
  --parameters bicep/parameters/main.parameters.json

# デプロイ実行
az deployment sub create \
  --name bastion-lb-deployment \
  --location japaneast \
  --template-file bicep/main.bicep \
  --parameters bicep/parameters/main.parameters.json
```

### 4. パブリックIPの確認

```bash
# デプロイ後、パブリックIPを確認
az network public-ip show \
  --name pip-lb-bastion \
  --resource-group rg-lb-bastion \
  --query ipAddress -o tsv
```

### 5. SSH接続

#### 方法1: パブリックIP経由で直接接続

```bash
# Azure Portalから秘密鍵をダウンロード
# Portal → rg-vm-bastion → ssh-bastion → "Download private key"

# SSH接続（パブリックIP使用）
ssh -i ~/Downloads/ssh-bastion.pem azureuser@<Public-IP> -p 2201  # VM1
ssh -i ~/Downloads/ssh-bastion.pem azureuser@<Public-IP> -p 2202  # VM2
ssh -i ~/Downloads/ssh-bastion.pem azureuser@<Public-IP> -p 2203  # VM3
```

#### 方法2: Azure CLI SSH（VM内部アクセス）

```bash
az ssh vm --resource-group rg-vm-bastion --name vm-bastion-1
```

## クリーンアップ

```bash
az group delete --name rg-lb-bastion --yes --no-wait
az group delete --name rg-vm-bastion --yes --no-wait
```

## セキュリティ考慮事項

### ⚠️ 重要: NSGでのIP制限

インターネットからアクセス可能な構成のため、以下を強く推奨します：

1. **送信元IP制限**: パラメータ `allowedSshSourceIp` で特定IPに制限
   ```json
   "allowedSshSourceIp": {
     "value": "xxx.xxx.xxx.xxx/32"  // 自分のグローバルIP
   }
   ```

2. **SSH公開鍵認証**: パスワード認証は無効化済み

3. **ポート番号変更**: 標準22番ではなく2201-から使用

4. **監視**: NSG Flow Logsを有効化（推奨）

## 既存VNet版との比較

既存のVNetを利用したい場合は、[既存VNet利用版](../existing-vnet/) を使用してください。

| 項目 | 新規VNet版（このバージョン） | 既存VNet版 |
|------|---------------------------|-----------|
| VNet作成 | ✅ 新規作成 | ❌ 既存利用 |
| アクセス方法 | インターネット | オンプレミス/既存網 |
| 適用環境 | 新規・検証・インターネット環境 | 既存・本番・閉域環境 |

## 参考リンク

- [Azure Private Link](https://learn.microsoft.com/azure/private-link/private-link-overview)
- [Azure Load Balancer NAT Rules](https://learn.microsoft.com/azure/load-balancer/load-balancer-inbound-nat-rules)
- [VNet Peering](https://learn.microsoft.com/azure/virtual-network/virtual-network-peering-overview)
- [Azure Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure SSH Public Keys](https://learn.microsoft.com/azure/virtual-machines/ssh-keys-azure-cli)

## ライセンス

MIT License
