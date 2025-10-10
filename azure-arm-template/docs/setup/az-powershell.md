# Az PowerShell セットアップ手順

ARM テンプレートのハンズオンでは Az PowerShell モジュールを使用します。以下の手順で最新バージョンをインストールまたは更新してください。詳細は公式ドキュメントを参照できます。

## 1. 事前確認
- Windows / macOS / Linux の PowerShell 7 以降、または Azure Cloud Shell (PowerShell) を利用可能であること。
- 管理者権限の PowerShell セッションを起動できること。

## 2. インストール
```powershell
# 初回のみ: スクリプト実行ポリシーを緩和
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Az モジュール本体とリソース管理コマンドをインストール
Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force
Install-Module -Name Az.Resources -Scope CurrentUser -Repository PSGallery -Force
Install-Module -Name Az.Storage -Scope CurrentUser -Repository PSGallery -Force

# コマンドを利用できるよう読み込む
Import-Module Az.Resources
Import-Module Az.Storage
```

## 3. 更新 (既に Az をインストール済みの場合)
```powershell
Update-Module -Name Az
Update-Module -Name Az.Resources
Update-Module -Name Az.Storage
```

## 4. バージョン確認
```powershell
Get-Module -Name Az,Az.Resources,Az.Storage -ListAvailable | Select-Object Name, Version
```

## 5. トラブルシュート
- TLS/プロキシの設定でインストールが止まる場合は、社内ポリシーやプロキシ設定を確認してください。
- 公式ガイド: [Install Azure PowerShell](https://learn.microsoft.com/powershell/azure/install-azure-powershell)
- `New-AzStorageAccount` などのコマンドレットが見つからない場合は、`Get-Module Az.Storage -ListAvailable` でモジュールを確認し、必要に応じて `Install-Module Az.Storage -Force` を再実行してください。
