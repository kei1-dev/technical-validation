# 実装計画

- [x] 1. フォルダ構造の作成とファイル移動

- [x] 1.1 ACR専用フォルダの作成


  - 'bicep/acr-only'フォルダを作成する
  - 'bicep/acr-only/modules'フォルダを作成する
  - 'bicep/acr-only/parameters'フォルダを作成する
  - _要件: 1.1_

- [x] 1.2 メインインフラフォルダへの移動


  - 'bicep/main'フォルダを作成する
  - 既存の'bicep/main.bicep'を'bicep/main/main.bicep'に移動する
  - 既存の'bicep/modules'フォルダを'bicep/main/modules'に移動する
  - 既存の'bicep/parameters'フォルダを'bicep/main/parameters'に移動する
  - _要件: 1.5_

- [x] 2. ACR専用Bicepテンプレートの作成

- [x] 2.1 ACRモジュールのコピー


  - 'bicep/main/modules/acr.bicep'を'bicep/acr-only/modules/acr.bicep'にコピーする
  - _要件: 1.4_

- [x] 2.2 ACRメインテンプレートの作成


  - 'bicep/acr-only/main.bicep'ファイルを作成し、ACRモジュールを使用してACRのみをデプロイする
  - environment、location、tagsをパラメータとして受け入れる
  - acrName、acrLoginServerを出力する
  - _要件: 1.1, 1.2, 1.3_

- [x] 2.3 ACRパラメータファイルの作成


  - 'bicep/acr-only/parameters/dev.bicepparam'を作成する
  - 'bicep/acr-only/parameters/prod.bicepparam'を作成する
  - environment、location、tagsパラメータを設定する
  - _要件: 1.2_

- [x] 3. メインBicepテンプレートの更新

- [x] 3.1 ACRモジュールデプロイの削除


  - 'bicep/main/main.bicep'からACRモジュールのデプロイセクションを削除する
  - ACR関連の出力を削除する
  - _要件: 1.5_

- [x] 3.2 ACR関連パラメータの追加


  - acrName、acrLoginServer、acrAdminUsername、acrAdminPassword、nginxImageパラメータを追加する（すべて必須）
  - パラメータの説明を追加する
  - _要件: 3.1, 3.4, 3.5_

- [x] 3.3 nginx Container Appモジュール呼び出しの更新


  - nginxImageパラメータをnginxContainerAppモジュールに渡す
  - ACR認証情報パラメータをnginxContainerAppモジュールに渡す
  - _要件: 3.2_

- [x] 4. nginx Container Appモジュールの更新


  - 'bicep/main/modules/nginxContainerApp.bicep'にACR認証情報パラメータを追加する（acrLoginServer、acrAdminUsername、acrAdminPassword）
  - Container Appのconfiguration.secretsにACRパスワードを追加する
  - Container Appのconfiguration.registriesにACR認証情報を追加する
  - _要件: 3.2_

- [x] 5. デプロイスクリプトの更新

- [x] 5.1 パス変数の更新


  - 'scripts/deploy.sh'のBicepディレクトリパスを更新する（bicep/acr-only と bicep/main）
  - パラメータファイルのパスを更新する
  - _要件: 2.1_

- [x] 5.2 3フェーズデプロイフローの実装


  - フェーズ1（ACRデプロイ）のロジックを追加する（bicep/acr-only/main.bicepを使用）
  - フェーズ1の出力からACR情報を取得するロジックを追加する
  - フェーズ2（nginxビルド/プッシュ）の呼び出しを追加する
  - フェーズ3（メインデプロイ）でACR情報とnginxイメージURLをパラメータとして渡す（bicep/main/main.bicepを使用）
  - _要件: 2.1, 2.2, 2.3_

- [x] 5.3 エラーハンドリングの追加

  - 各フェーズの終了コードをチェックし、失敗時に停止する
  - 各フェーズの成功/失敗メッセージを表示する
  - _要件: 2.4, 2.5_

- [x] 5.4 ACR認証情報の取得

  - az acr credential showコマンドを使用してACR管理者ユーザー名とパスワードを取得する
  - 取得した認証情報をフェーズ3のパラメータとして渡す
  - _要件: 2.3_

- [x] 6. ビルドスクリプトの更新


  - 'scripts/build-and-push-nginx.sh'がACR名を必須パラメータとして受け入れるように更新する（既に実装済みの場合は確認のみ）
  - スクリプトが正常に完了した場合の終了コードが0であることを確認する
  - _要件: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. メインパラメータファイルの更新


  - 'bicep/main/parameters/dev.bicepparam'から既存のnginxImageパラメータを削除する（存在する場合）
  - 'bicep/main/parameters/prod.bicepparam'から既存のnginxImageパラメータを削除する（存在する場合）
  - ACR関連パラメータがパラメータファイルに含まれていないことを確認する
  - _要件: 4.1, 4.2, 4.3_

- [x] 8. ドキュメントの更新



  - 'README.md'に新しい3フェーズデプロイフローを説明するセクションを追加する
  - 新しいフォルダ構造（bicep/acr-only と bicep/main）を説明する
  - 'docs/deployment-guide.md'に詳細なデプロイ手順を追加する
  - _要件: すべて_
