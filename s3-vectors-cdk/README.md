# S3 Vectors CDK Project

このプロジェクトは、AWS CDK（Python）を使用してAmazon S3 Vectorsのインフラストラクチャを構築し、Pythonスクリプトで動作検証を行うためのものです。

## プロジェクト構成

```
s3-vectors-cdk/
├── s3-vectors-infra/                # CDKプロジェクト
│   ├── app.py                       # CDKアプリケーションエントリーポイント
│   ├── cdk.json                     # CDK設定
│   ├── Pipfile                      # Pipenv依存関係定義
│   └── s3_vectors_infra/
│       └── s3_vectors_infra_stack.py  # S3 Vectorsスタック定義
├── s3-vectors-test-scripts/         # 動作検証用スクリプト
│   ├── Pipfile                      # Pipenv依存関係定義
│   ├── utils.py                     # 共通ユーティリティ
│   ├── test_basic_operations.py     # 基本CRUD操作テスト
│   ├── test_similarity_search.py    # 類似度検索テスト
│   ├── test_metadata_filter.py      # メタデータフィルタリングテスト
│   └── test_html_documents.py       # HTMLドキュメント埋め込みテスト
└── s3-vectors-files/                # S3 Vectorsドキュメント（HTML）
    ├── README.md
    └── *.html                       # 18ページのドキュメント
```

## 前提条件

- Python 3.12以上
- pipenv（`pip install pipenv`）
- Node.js（CDK CLI用）
- AWS CLI（設定済み）
- AWS CDK CLI（`npm install -g aws-cdk`）
- S3 Vectorsが利用可能なAWSリージョンへのアクセス
  - us-east-1（N. Virginia）
  - us-east-2（Ohio）
  - us-west-2（Oregon）
  - ap-southeast-2（Sydney）
  - eu-central-1（Frankfurt）

## セットアップ

### 1. CDKプロジェクトのセットアップ

```bash
cd s3-vectors-infra

# pipenvで依存関係をインストール
pipenv install

# pipenv環境に入る
pipenv shell
```

### 2. AWS認証情報の設定

```bash
# AWS CLIで認証情報を設定
aws configure

# または環境変数で設定
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

### 3. CDKブートストラップ（初回のみ）

```bash
# CDKをアカウント/リージョンにブートストラップ
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

## デプロイ

### 1. CloudFormationテンプレートの確認

```bash
cd s3-vectors-infra
cdk synth
```

### 2. デプロイ

```bash
cdk deploy
```

デプロイには数分かかります。`install_latest_aws_sdk=True`を使用しているため、初回デプロイ時は約60秒かかります。

### 3. デプロイ確認

デプロイが成功すると、以下の出力が表示されます：

```
Outputs:
S3VectorsInfraStack.VectorBucketName = my-s3-vector-bucket
S3VectorsInfraStack.VectorIndexName = my-vector-index
S3VectorsInfraStack.VectorDimensions = 1024
```

## 動作検証

### テストスクリプトの準備

```bash
cd s3-vectors-test-scripts

# pipenvで依存関係をインストール
pipenv install

# pipenv環境に入る
pipenv shell
```

### 1. 基本CRUD操作のテスト

ベクトルの追加、削除などの基本操作をテストします。

```bash
# デフォルト: ランダムベクトルで基本テスト
python test_basic_operations.py --num-vectors 10

# HTMLドキュメントベクトルを全削除
python test_basic_operations.py --delete-html-docs

# 特定のベクトルIDを削除
python test_basic_operations.py --delete-ids s3-vectors s3-vectors-buckets s3-vectors-query
```

オプション：
- `--bucket`: ベクトルバケット名（デフォルト: my-s3-vector-bucket）
- `--index`: インデックス名（デフォルト: my-vector-index）
- `--region`: AWSリージョン（デフォルト: us-east-1）
- `--num-vectors`: 作成するベクトル数（デフォルト: 10）
- `--delete-html-docs`: HTMLドキュメントベクトルを全削除
- `--delete-ids`: 削除する特定のベクトルID（スペース区切り）
- `--html-dir`: HTMLファイルのディレクトリ（デフォルト: ../s3-vectors-files）

### 2. 類似度検索のテスト（HTMLドキュメントデータ使用）

投入したHTMLドキュメントデータに対して類似度検索を実行します。

```bash
# デフォルト: 事前定義されたクエリで検索
python test_similarity_search.py

# テキストクエリで検索
python test_similarity_search.py --query-text "ベクトルバケットの作成方法"

# HTMLファイルをクエリとして使用
python test_similarity_search.py --query-html ../s3-vectors-files/s3-vectors-buckets.html

# 事前定義クエリを実行
python test_similarity_search.py --test-queries
```

オプション：
- `--query-text`: 検索クエリテキスト
- `--query-html`: クエリとして使用するHTMLファイルパス
- `--test-queries`: 事前定義された5つのクエリを実行
- `--top-k`: 取得する上位結果の数（デフォルト: 10）

### 3. メタデータフィルタリングのテスト（HTMLドキュメントデータ使用）

投入したHTMLドキュメントのメタデータでフィルタリング検索をテストします。

```bash
# すべてのテストを実行（デフォルト）
python test_metadata_filter.py

# メタデータフィルターのテスト
python test_metadata_filter.py --test-filters

# トピック別検索のテスト
python test_metadata_filter.py --test-topics

# ドキュメントカバレッジ分析
python test_metadata_filter.py --analyze-coverage
```

オプション：
- `--test-filters`: メタデータフィルターのテスト
- `--test-topics`: トピック別検索のテスト
- `--analyze-coverage`: ドキュメントカバレッジ分析

### 4. HTMLドキュメントの埋め込みテスト（Titan Embeddings V2使用）

S3 Vectorsドキュメント（HTMLファイル）をTitan Embeddings V2でベクトル化してS3 Vectorsに格納します。

```bash
python test_html_documents.py --html-dir ../s3-vectors-files --bucket my-s3-vector-bucket --index my-vector-index
```

このスクリプトは：
- `s3-vectors-files`ディレクトリ内のすべてのHTMLファイルを読み込み
- HTMLからテキストを抽出
- Amazon Titan Embeddings V2で1024次元のベクトル埋め込みを生成
- メタデータ（ファイル名、サイズ、テキスト長など）とともにS3 Vectorsに格納

オプション：
- `--html-dir`: HTMLファイルのディレクトリ（デフォルト: ../s3-vectors-files）
- `--bucket`: ベクトルバケット名（デフォルト: my-s3-vector-bucket）
- `--index`: インデックス名（デフォルト: my-vector-index）
- `--region`: AWSリージョン（デフォルト: us-east-1）
- `--batch-size`: 一度にアップロードするベクトル数（デフォルト: 100）

**前提条件:**
- Amazon Bedrockへのアクセス権限（`bedrock:InvokeModel`）
- Titan Embeddings V2モデルへのアクセス

## スタックの設定

`s3-vectors-infra/s3_vectors_infra/s3_vectors_infra_stack.py`で以下の設定が可能です：

```python
# バケット名
vector_bucket_name = "my-s3-vector-bucket"

# インデックス名
index_name = "my-vector-index"

# ベクトル次元数（使用する埋め込みモデルに合わせて変更）
vector_dimensions = 1024  # Titan Embeddings V2用
```

### 一般的な埋め込みモデルの次元数

- Amazon Titan Text Embeddings V2: 1024
- OpenAI text-embedding-ada-002: 1536
- OpenAI text-embedding-3-small: 1536
- BERT/SentenceTransformers: 768

## リソースの削除

```bash
cd s3-vectors-infra
cdk destroy
```

注意：削除前に、インデックス内のすべてのベクトルが削除されることを確認してください。

## S3 Vectors API概要

### 主要なAPI操作

```python
import boto3

client = boto3.client('s3vectors', region_name='us-east-1')

# ベクトルの追加（最大500個/回）
client.put_vectors(
    vectorBucketName='my-bucket',
    indexName='my-index',
    vectors=[{
        'vectorId': 'vec-001',
        'vector': [0.1, 0.2, ...],  # float32の配列
        'metadata': {'key': 'value'}
    }]
)

# 類似度検索
response = client.query_vectors(
    vectorBucketName='my-bucket',
    indexName='my-index',
    queryVector=[0.1, 0.2, ...],
    topK=10,
    metadataFilter={'category': {'$eq': 'news'}}  # オプション
)

# ベクトルの削除
client.delete_vectors(
    vectorBucketName='my-bucket',
    indexName='my-index',
    vectorIds=['vec-001', 'vec-002']
)
```

## トラブルシューティング

### エラー: "S3 Vectors is not available in this region"

S3 Vectorsは現在プレビュー段階で、限られたリージョンでのみ利用可能です。`us-east-1`など対応リージョンを使用してください。

### エラー: "AccessDenied"

IAMユーザー/ロールに`s3vectors:*`権限が必要です。以下のポリシーを適用してください：

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3vectors:*",
    "Resource": "*"
  }]
}
```

### デプロイが遅い

`install_latest_aws_sdk=True`を使用しているため、初回デプロイ時は約60秒の追加時間がかかります。これは、LambdaランタイムにS3 Vectors APIが含まれていないためです。

## 参考資料

- [Amazon S3 Vectors Documentation](https://docs.aws.amazon.com/s3/latest/userguide/s3-vectors.html)
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS CDK Custom Resources](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources.html)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プルリクエストを歓迎します！バグ報告や機能リクエストはIssuesで受け付けています。
