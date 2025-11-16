# S3 Vectors ドキュメント (HTML保存版)

このディレクトリには、AWS S3 Vectors公式ドキュメントのHTMLファイルが保存されています。

## ダウンロード日時

2025-11-16

## ソース

https://docs.aws.amazon.com/ja_jp/AmazonS3/latest/userguide/s3-vectors.html

## ファイル一覧（18ページ）

### メインページとチュートリアル

1. **s3-vectors.html** - S3 Vectorsとベクトルバケットの操作（メインページ）
   - S3 Vectorsの概要
   - ユースケース
   - 主要機能

2. **s3-vectors-getting-started.html** - チュートリアル: S3 Vectorsの開始方法
   - チュートリアル
   - 基本的な操作手順

### ベクトルバケット

3. **s3-vectors-buckets.html** - ベクトルバケット概要
   - ベクトルバケットの概要
   - 管理方法

4. **s3-vectors-buckets-naming.html** - ベクトルバケットの命名規則
   - 命名ルール
   - 制約事項

5. **s3-vectors-buckets-create.html** - ベクトルバケットの作成
   - バケット作成手順
   - 設定オプション

6. **s3-vectors-buckets-list.html** - ベクトルバケットの一覧表示
   - 一覧表示方法
   - フィルタリング

7. **s3-vectors-buckets-delete.html** - ベクトルバケットの削除
   - 削除手順
   - 注意事項

### ベクトルインデックス

8. **s3-vectors-indexes.html** - ベクトルインデックス
   - インデックスの概要
   - インデックス管理

### ベクトル操作

9. **s3-vectors-list.html** - ベクトルの一覧表示
   - ベクトル一覧の取得
   - ページネーション

10. **s3-vectors-query.html** - ベクトルのクエリ
    - 類似度検索
    - k-NN検索

11. **s3-vectors-delete.html** - ベクトルの削除
    - ベクトル削除操作
    - バッチ削除

12. **s3-vectors-metadata-filtering.html** - メタデータフィルタリング
    - メタデータによるフィルタリング
    - クエリ条件の指定

### セキュリティとベストプラクティス

13. **s3-vectors-access-management.html** - アクセス管理
    - IAMポリシー
    - アクセス制御

14. **s3-vectors-data-encryption.html** - データ暗号化
    - 暗号化オプション
    - セキュリティベストプラクティス

15. **s3-vectors-security.html** - S3 Vectorsのセキュリティ
    - セキュリティ全般
    - ID管理

16. **s3-vectors-best-practices.html** - ベストプラクティス
    - パフォーマンス最適化
    - コスト最適化

### 制限と統合

17. **s3-vectors-limitations.html** - 制限と制約
    - クォータ
    - サービス制限

18. **s3-vectors-opensearch.html** - OpenSearch統合
    - OpenSearchとの連携
    - ハイブリッドアーキテクチャ

## 主要トピック

### ベクトルバケットの操作
- ベクトルバケットの作成、削除
- バケットポリシーの設定
- 暗号化設定

### ベクトルインデックスの管理
- インデックスの作成、削除
- 次元数の設定
- インデックスクォータ

### ベクトルデータの操作
- ベクトルの追加（PutVectors）
- 類似度検索（QueryVectors）
- ベクトルの削除（DeleteVectors）
- メタデータフィルタリング

### セキュリティとアクセス管理
- IAMポリシー（s3vectors:* アクション）
- データ暗号化（SSE-S3、SSE-KMS）
- VPCエンドポイント

### 制限事項
- バケットあたりのインデックス数：10,000
- インデックスあたりのベクトル数：数千万
- 1回のPutVectors呼び出し：最大500ベクトル
- クエリレート：低〜中程度の頻度に最適

## 関連リソース

- [Amazon S3 Vectors 料金](https://aws.amazon.com/s3/pricing/)
- [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)

## 注意事項

- Amazon S3 Vectorsはプレビュー版サービスです
- ドキュメントの内容は変更される可能性があります
- 利用可能なリージョン：
  - us-east-1 (N. Virginia)
  - us-east-2 (Ohio)
  - us-west-2 (Oregon)
  - ap-southeast-2 (Sydney)
  - eu-central-1 (Frankfurt)
