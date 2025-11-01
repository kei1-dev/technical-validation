# Samurai Terakoya 請求申請自動化 - データ構造設計書（リファクタリング版）

## 1. 概要

本ドキュメントは、Terakoya請求申請自動化システムで使用するデータ構造とフォーマットを定義します。

**主な更新内容**:
- スキーマバージョニングの導入
- TypedDictによる型安全性の向上
- データ整合性チェックの追加
- Result<T>パターンとの統合

## 1.1 スキーマバージョニング

### 目的
データ構造の進化に対応し、後方互換性を保つためのバージョニング戦略。

### バージョン管理

```python
from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass

class SchemaVersion(Enum):
    """スキーマバージョン"""
    V1_0 = "1.0"  # 初期バージョン
    V1_1 = "1.1"  # オプションフィールド追加
    V2_0 = "2.0"  # 破壊的変更

@dataclass
class VersionedData:
    """バージョン情報付きデータ"""
    schema_version: str
    data: Dict[str, Any]

    def validate(self) -> bool:
        """スキーマバージョンに基づくバリデーション"""
        validator = get_validator_for_version(self.schema_version)
        return validator.validate(self.data)
```

### JSONファイルでのバージョン表現

```json
{
    "schema_version": "1.0",
    "metadata": {
        "target_month": "2025-10",
        "retrieved_at": "2025-11-01T10:00:00+09:00"
    },
    "lessons": [...]
}
```

### マイグレーション戦略

```python
class SchemaMigrator:
    """スキーママイグレーション"""

    def migrate(
        self,
        data: VersionedData,
        target_version: SchemaVersion
    ) -> VersionedData:
        """指定バージョンへマイグレーション"""
        current = SchemaVersion(data.schema_version)

        if current == target_version:
            return data

        # マイグレーションパスを適用
        migrated_data = data.data
        for migration in self.get_migration_path(current, target_version):
            migrated_data = migration.apply(migrated_data)

        return VersionedData(
            schema_version=target_version.value,
            data=migrated_data
        )
```

## 1.2 データ整合性チェック

### チェックサム生成

```python
import hashlib
import json
from datetime import datetime
from dataclasses import dataclass

@dataclass
class IntegrityMetadata:
    """データ整合性メタデータ"""
    checksum: str
    algorithm: str
    timestamp: str

    @classmethod
    def compute(cls, data: Dict[str, Any], algorithm: str = "sha256") -> 'IntegrityMetadata':
        """チェックサム計算"""
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)

        hasher = hashlib.new(algorithm)
        hasher.update(serialized.encode('utf-8'))
        checksum = hasher.hexdigest()

        return cls(
            checksum=checksum,
            algorithm=algorithm,
            timestamp=datetime.now().isoformat()
        )

    def verify(self, data: Dict[str, Any]) -> bool:
        """データ整合性検証"""
        computed = self.compute(data, self.algorithm)
        return computed.checksum == self.checksum
```

### ファイル保存時の整合性保護

```python
def save_json_with_integrity(data: Dict, filepath: Path) -> bool:
    """整合性メタデータ付きJSON保存"""
    integrity = IntegrityMetadata.compute(data)

    wrapped = {
        "integrity": {
            "checksum": integrity.checksum,
            "algorithm": integrity.algorithm,
            "timestamp": integrity.timestamp
        },
        "data": data
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(wrapped, f, ensure_ascii=False, indent=2)

    return True
```

## 2. データモデル（TypedDict版）

### 型安全性の向上

Python 3.8+の`TypedDict`を使用して、型安全性を向上させます。

```python
from typing import TypedDict, Literal

# ステータスの型定義
LessonStatus = Literal["completed", "pending", "cancelled"]
InvoiceStatus = Literal["added", "failed", "skipped"]
```

### 2.1 LessonData（レッスン情報 - TypedDict版）

システム内で扱うレッスンの基本情報を表すデータ構造。

#### TypedDict定義

```python
from typing import TypedDict

class LessonData(TypedDict):
    """レッスンデータの型定義"""
    id: str                 # レッスンID（例: "lesson_12345"）
    date: str               # レッスン日（YYYY-MM-DD形式、例: "2025-10-15"）
    student_id: str         # 受講生ID（例: "student_789"）
    student_name: str       # 受講生名（例: "山田太郎"）
    status: LessonStatus    # ステータス
    duration: int           # レッスン時間（分）（デフォルト: 60）
    category: str           # カテゴリー（例: "専属レッスン"）
```

#### 使用例

```python
# 型チェックが効く
lesson: LessonData = {
    "id": "lesson_12345",
    "date": "2025-10-15",
    "student_id": "student_789",
    "student_name": "山田太郎",
    "status": "completed",  # LessonStatusの値のみ許可
    "duration": 60,
    "category": "専属レッスン"
}

# IDEで自動補完が効く
def process_lesson(lesson: LessonData) -> None:
    print(lesson["student_name"])  # 型安全
    # print(lesson["invalid_key"])  # エラー: キーが存在しない
```

#### サンプルデータ

```json
{
    "id": "lesson_12345",
    "date": "2025-10-15",
    "student_id": "student_789",
    "student_name": "山田太郎",
    "status": "completed",
    "duration": 60,
    "category": "専属レッスン"
}
```

#### バリデーション

- `id`: 必須、非空文字列
- `date`: 必須、YYYY-MM-DD形式
- `student_id`: 必須、非空文字列
- `student_name`: 必須、非空文字列
- `status`: 必須、["completed", "pending", "cancelled"] のいずれか
- `duration`: 必須、正の整数
- `category`: 必須、非空文字列

#### 使用箇所

- `TerakoyaClient.get_lessons_for_month()` の戻り値
- `TerakoyaClient.add_invoice_item()` の引数
- JSONファイル保存: `output/terakoya_data/lessons_{YYYY-MM}.json`

---

### 2.2 InvoiceItem（請求項目）

請求申請システムに登録する個別の請求項目。

#### スキーマ

```python
{
    "date": str,            # レッスン日（YYYY-MM-DD形式）
    "category": str,        # カテゴリー（例: "専属レッスン"）
    "student_id": str,      # 受講生ID
    "student_name": str,    # 受講生名
    "lesson_id": str,       # レッスンID（オプション）
    "duration": int,        # レッスン時間（分）
    "unit_price": int,      # 単価（円）
    "total": int,           # 合計金額（円）（duration × unit_price / 60）
    "status": str           # ステータス（"added", "failed", "skipped"）
}
```

#### サンプルデータ

```json
{
    "date": "2025-10-15",
    "category": "専属レッスン",
    "student_id": "student_789",
    "student_name": "山田太郎",
    "lesson_id": "lesson_12345",
    "duration": 60,
    "unit_price": 2300,
    "total": 2300,
    "status": "added"
}
```

#### 計算式

```python
total = (duration / 60) * unit_price
# 例: (60 / 60) * 2300 = 2300円
```

#### バリデーション

- `date`: 必須、YYYY-MM-DD形式
- `category`: 必須、非空文字列
- `student_id`: 必須、非空文字列
- `student_name`: 必須、非空文字列
- `lesson_id`: オプション、文字列
- `duration`: 必須、正の整数
- `unit_price`: 必須、正の整数
- `total`: 必須、正の整数
- `status`: 必須、["added", "failed", "skipped"] のいずれか

#### 使用箇所

- `TerakoyaClient.add_invoice_item()` の内部処理
- `TerakoyaClient.get_existing_invoices()` の戻り値
- サマリーレポート生成

---

### 2.3 InvoiceResult（請求処理結果）

請求項目追加処理の結果を表すデータクラス。

#### スキーマ

```python
@dataclass
class InvoiceResult:
    lesson: Dict[str, Any]           # 処理対象のレッスン情報
    status: InvoiceStatus            # 処理状態（Enum）
    error_message: Optional[str]     # エラーメッセージ（失敗時のみ）
    retry_count: int                 # リトライ回数
    screenshot_path: Optional[str]   # スクリーンショットパス（エラー時）
```

#### InvoiceStatus Enum

```python
from enum import Enum

class InvoiceStatus(Enum):
    SUCCESS = "success"    # 追加成功
    FAILED = "failed"      # 追加失敗
    SKIPPED = "skipped"    # スキップ（重複検出）
    PENDING = "pending"    # 保留中
```

#### サンプルデータ

成功時:
```python
InvoiceResult(
    lesson={
        "id": "lesson_12345",
        "date": "2025-10-15",
        "student_name": "山田太郎",
        ...
    },
    status=InvoiceStatus.SUCCESS,
    error_message=None,
    retry_count=0,
    screenshot_path=None
)
```

失敗時:
```python
InvoiceResult(
    lesson={...},
    status=InvoiceStatus.FAILED,
    error_message="タイムアウト: Message: timeout",
    retry_count=3,
    screenshot_path="output/terakoya_screenshots/error_lesson_12345_20251001_103045.png"
)
```

#### to_dict() メソッド

辞書形式への変換メソッド。

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "lesson_id": self.lesson.get("id"),
        "date": self.lesson.get("date"),
        "student_name": self.lesson.get("student_name"),
        "status": self.status.value,
        "error_message": self.error_message,
        "retry_count": self.retry_count,
        "screenshot_path": self.screenshot_path
    }
```

出力例:
```json
{
    "lesson_id": "lesson_12345",
    "date": "2025-10-15",
    "student_name": "山田太郎",
    "status": "success",
    "error_message": null,
    "retry_count": 0,
    "screenshot_path": null
}
```

#### 使用箇所

- `TerakoyaClient.add_invoice_item_with_retry()` の戻り値
- 処理サマリーの生成
- エラーログ記録

---

### 2.4 InvoiceSummary（請求処理サマリー）

バッチ処理全体の結果サマリー。

#### スキーマ

```python
{
    "target_month": str,              # 対象月（YYYY-MM形式）
    "execution_time": str,            # 実行日時（ISO 8601形式）
    "total_lessons": int,             # 取得したレッスン総数
    "existing_invoices": int,         # 既存申請数
    "processed": int,                 # 処理対象数
    "success": int,                   # 成功数
    "failed": int,                    # 失敗数
    "skipped": int,                   # スキップ数
    "dry_run": bool,                  # ドライランフラグ
    "submitted": bool,                # 送信実行フラグ
    "results": List[Dict],            # 個別結果のリスト
    "errors": List[Dict]              # エラー詳細のリスト
}
```

#### サンプルデータ

```json
{
    "target_month": "2025-10",
    "execution_time": "2025-11-01T10:30:45+09:00",
    "total_lessons": 25,
    "existing_invoices": 5,
    "processed": 20,
    "success": 18,
    "failed": 2,
    "skipped": 5,
    "dry_run": false,
    "submitted": true,
    "results": [
        {
            "lesson_id": "lesson_12345",
            "date": "2025-10-15",
            "student_name": "山田太郎",
            "status": "success",
            "retry_count": 0
        },
        {
            "lesson_id": "lesson_12346",
            "date": "2025-10-16",
            "student_name": "佐藤花子",
            "status": "failed",
            "error_message": "タイムアウト",
            "retry_count": 3,
            "screenshot_path": "output/screenshots/error_lesson_12346.png"
        }
    ],
    "errors": [
        {
            "lesson_id": "lesson_12346",
            "date": "2025-10-16",
            "error": "タイムアウト",
            "screenshot": "output/screenshots/error_lesson_12346.png"
        }
    ]
}
```

#### 使用箇所

- メインスクリプトの最終処理
- JSONファイル保存: `output/terakoya_data/summary_{YYYY-MM}_{timestamp}.json`
- レポート生成（Phase 2）

---

## 3. ファイルフォーマット

### 3.1 JSON フォーマット

#### 3.1.1 レッスンデータファイル

**パス**: `output/terakoya_data/lessons_{YYYY-MM}.json`

**構造**:
```json
{
    "metadata": {
        "target_month": "2025-10",
        "retrieved_at": "2025-11-01T10:00:00+09:00",
        "total_count": 25
    },
    "lessons": [
        {
            "id": "lesson_12345",
            "date": "2025-10-15",
            "student_id": "student_789",
            "student_name": "山田太郎",
            "status": "completed",
            "duration": 60,
            "category": "専属レッスン"
        },
        ...
    ]
}
```

#### 3.1.2 サマリーファイル

**パス**: `output/terakoya_data/summary_{YYYY-MM}_{timestamp}.json`

**構造**: [2.4 InvoiceSummary](#24-invoicesummary請求処理サマリー) 参照

#### 3.1.3 エラーログファイル

**パス**: `output/terakoya_data/errors_{YYYY-MM}_{timestamp}.json`

**構造**:
```json
{
    "target_month": "2025-10",
    "error_count": 2,
    "errors": [
        {
            "timestamp": "2025-11-01T10:15:30+09:00",
            "lesson_id": "lesson_12346",
            "error_type": "TimeoutException",
            "error_message": "Message: timeout",
            "stack_trace": "...",
            "screenshot_path": "output/terakoya_screenshots/error_lesson_12346.png"
        }
    ]
}
```

### 3.2 CSV フォーマット

#### 3.2.1 レッスンCSV

**パス**: `output/terakoya_data/lessons_{YYYY-MM}.csv`

**ヘッダー**:
```
id,date,student_id,student_name,status,duration,category
```

**サンプル**:
```csv
id,date,student_id,student_name,status,duration,category
lesson_12345,2025-10-15,student_789,山田太郎,completed,60,専属レッスン
lesson_12346,2025-10-16,student_790,佐藤花子,completed,60,専属レッスン
lesson_12347,2025-10-17,student_791,鈴木一郎,completed,60,専属レッスン
```

#### 3.2.2 請求結果CSV

**パス**: `output/terakoya_data/invoice_results_{YYYY-MM}_{timestamp}.csv`

**ヘッダー**:
```
lesson_id,date,student_name,status,error_message,retry_count,screenshot_path
```

**サンプル**:
```csv
lesson_id,date,student_name,status,error_message,retry_count,screenshot_path
lesson_12345,2025-10-15,山田太郎,success,,0,
lesson_12346,2025-10-16,佐藤花子,failed,タイムアウト,3,output/screenshots/error_lesson_12346.png
lesson_12347,2025-10-17,鈴木一郎,skipped,既存申請あり,0,
```

### 3.3 ログファイルフォーマット

#### 3.3.1 メインログ

**パス**: `output/terakoya_logs/invoice_{timestamp}.log`

**フォーマット**:
```
[timestamp] [level] [module:function:line] message
```

**サンプル**:
```
2025-11-01 10:00:00,123 INFO terakoya_invoice:main:45 処理開始: 対象月=2025-10
2025-11-01 10:00:05,456 INFO terakoya:login:102 ログイン成功
2025-11-01 10:00:10,789 INFO terakoya:get_lessons_for_month:150 取得したレッスン数: 25件
2025-11-01 10:00:15,012 INFO terakoya:navigate_to_invoice_page:180 請求申請ページへ移動
2025-11-01 10:00:20,345 INFO terakoya:get_existing_invoices:200 既存申請: 5件
2025-11-01 10:00:25,678 INFO terakoya:add_invoice_item:250 請求項目追加: lesson_12345 - 山田太郎
2025-11-01 10:00:30,901 INFO terakoya:add_invoice_item:250 請求項目追加成功
2025-11-01 10:00:35,234 WARNING terakoya:add_invoice_item_with_retry:420 タイムアウトエラー (試行 1/3)
2025-11-01 10:00:40,567 ERROR terakoya:add_invoice_item_with_retry:450 請求項目追加失敗: lesson_12346
2025-11-01 10:01:00,890 INFO terakoya_invoice:main:95 サマリー: 成功=18, 失敗=2, スキップ=5
2025-11-01 10:01:05,123 INFO terakoya:submit_invoice:300 申請送信完了
2025-11-01 10:01:10,456 INFO terakoya_invoice:main:110 処理完了
```

#### 3.3.2 エラーログ

エラー発生時はスタックトレース付きで記録:

```
2025-11-01 10:00:40,567 ERROR terakoya:add_invoice_item_with_retry:450 請求項目追加失敗: lesson_12346
Traceback (most recent call last):
  File "src/automation/terakoya.py", line 420, in add_invoice_item_with_retry
    success = self._add_invoice_item_internal(lesson)
  File "src/automation/terakoya.py", line 350, in _add_invoice_item_internal
    self.browser.click(By.CSS_SELECTOR, ".add-button")
selenium.common.exceptions.TimeoutException: Message: timeout
  (Session info: chrome=118.0.5993.70)
```

---

## 4. データフロー

### 4.1 全体フロー図

```
[Terakoyaサイト]
      │
      │ (1) JavaScript実行（編集ボタン検出）
      ▼
[カードテキスト取得]
      │
      │ (2) AI抽出 or 正規表現抽出
      ▼
[レッスンデータ]
      │
      │ (3) 重複削除 (date + student_name)
      ▼
[一意なレッスンデータ]
      │
      │ (4) JSON保存
      ▼
[lessons_YYYY-MM.json]
      │
      │ (5) 重複チェック
      ▼
[既存申請データ]
      │
      │ (6) フィルタリング
      ▼
[未申請レッスン]
      │
      │ (7) 請求項目追加ループ
      ▼
[InvoiceResult] ──┐
      │           │ (8) 集約
      │           │
      │           ▼
      │      [InvoiceSummary]
      │           │
      │           │ (9) JSON保存
      │           ▼
      │      [summary_YYYY-MM_timestamp.json]
      │
      │ (10) CSV変換
      ▼
[invoice_results_YYYY-MM_timestamp.csv]
```

### 4.2 データ変換フロー

#### 4.2.1 レッスン取得からInvoiceItem変換

```python
# 1. レッスンデータ取得
lessons: List[Dict] = client.get_lessons_for_month(2025, 10)
# 出力: [{"id": "lesson_12345", "date": "2025-10-15", ...}, ...]

# 2. 既存申請取得
existing: List[Dict] = client.get_existing_invoices()
# 出力: [{"id": "lesson_12340", "date": "2025-10-10", ...}, ...]

# 3. 重複チェックとフィルタリング
new_lessons = [
    lesson for lesson in lessons
    if not client.is_duplicate(lesson, existing)
]

# 4. InvoiceItem追加
results: List[InvoiceResult] = []
for lesson in new_lessons:
    result = client.add_invoice_item_with_retry(lesson)
    results.append(result)

# 5. サマリー生成
summary = generate_summary(results, lessons, existing)
```

#### 4.2.2 InvoiceResultからCSV変換

```python
import pandas as pd

# InvoiceResultリストをDataFrameに変換
df = pd.DataFrame([result.to_dict() for result in results])

# CSV保存
df.to_csv("output/terakoya_data/invoice_results.csv", index=False)
```

---

## 5. 環境変数設定

### 5.1 .env ファイル

**パス**: `.env`（リポジトリルート）

**構造**:
```bash
# Terakoya Login Credentials
TERAKOYA_EMAIL=your_email@example.com
TERAKOYA_PASSWORD=your_secure_password
TERAKOYA_URL=https://terakoya.sejuku.net/

# Invoice Settings
TERAKOYA_LESSON_DURATION=60
TERAKOYA_LESSON_UNIT_PRICE=2300

# Output Settings
OUTPUT_DIR=output
LOG_LEVEL=INFO

# Browser Settings
BROWSER_HEADLESS=false
BROWSER_TIMEOUT=30

# AI Extraction Settings
TERAKOYA_USE_AI_EXTRACTION=true
TERAKOYA_AI_BATCH_SIZE=10
```

### 5.2 .env.template ファイル

**パス**: `.env.template`（Git管理対象）

**構造**:
```bash
# Terakoya Login Credentials
# 注意: 実際の認証情報は.envファイルに記載し、Gitにコミットしないこと
TERAKOYA_EMAIL=your_email@example.com
TERAKOYA_PASSWORD=your_secure_password
TERAKOYA_URL=https://terakoya.sejuku.net/

# Invoice Settings
TERAKOYA_LESSON_DURATION=60
TERAKOYA_LESSON_UNIT_PRICE=2300

# Output Settings (optional)
OUTPUT_DIR=output
LOG_LEVEL=INFO

# Browser Settings (optional)
BROWSER_HEADLESS=false
BROWSER_TIMEOUT=30
```

---

## 6. 出力ディレクトリ構造

```
output/
├── terakoya_data/                    # データファイル
│   ├── lessons_2025-10.json          # レッスンデータ（JSON）
│   ├── lessons_2025-10.csv           # レッスンデータ（CSV）
│   ├── summary_2025-10_20251101_103045.json  # サマリー
│   ├── invoice_results_2025-10_20251101_103045.csv  # 結果CSV
│   └── errors_2025-10_20251101_103045.json   # エラーログ
│
├── terakoya_logs/                    # ログファイル
│   ├── invoice_20251101_103045.log   # メインログ
│   └── invoice_20251015_093020.log   # 過去ログ
│
└── terakoya_screenshots/             # スクリーンショット
    ├── login_success.png             # ログイン成功
    ├── invoice_item_0.png            # 項目追加1
    ├── invoice_item_1.png            # 項目追加2
    ├── error_lesson_12346_20251101_103045.png  # エラー時
    └── invoice_submitted.png         # 送信完了
```

---

## 7. データ保持期間とクリーンアップ

### 7.1 保持期間

| ファイル種別 | 保持期間 | 理由 |
|-------------|---------|------|
| ログファイル | 90日 | トラブルシューティング用 |
| スクリーンショット | 30日 | 証跡確認用 |
| データファイル（JSON/CSV） | 1年 | 監査証跡 |
| エラーログ | 1年 | エラー分析用 |

### 7.2 クリーンアップスクリプト（Phase 2検討中）

```bash
# 30日以上前のスクリーンショットを削除
find output/terakoya_screenshots -name "*.png" -mtime +30 -delete

# 90日以上前のログファイルを削除
find output/terakoya_logs -name "*.log" -mtime +90 -delete
```

---

## 8. データバリデーション

### 8.1 入力バリデーション

#### レッスンデータ

```python
from typing import Dict, Any
import re

def validate_lesson(lesson: Dict[str, Any]) -> bool:
    """レッスンデータのバリデーション"""

    # 必須フィールドチェック
    required_fields = ["id", "date", "student_id", "student_name", "status", "duration", "category"]
    if not all(field in lesson for field in required_fields):
        return False

    # 日付フォーマットチェック（YYYY-MM-DD）
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, lesson["date"]):
        return False

    # 数値チェック
    if not isinstance(lesson["duration"], int) or lesson["duration"] <= 0:
        return False

    # ステータスチェック
    valid_statuses = ["completed", "pending", "cancelled"]
    if lesson["status"] not in valid_statuses:
        return False

    return True
```

### 8.2 出力バリデーション

#### InvoiceResult

```python
def validate_invoice_result(result: InvoiceResult) -> bool:
    """InvoiceResultのバリデーション"""

    # ステータスチェック
    if result.status not in InvoiceStatus:
        return False

    # 失敗時はエラーメッセージ必須
    if result.status == InvoiceStatus.FAILED and not result.error_message:
        return False

    # リトライ回数は非負
    if result.retry_count < 0:
        return False

    return True
```

---

## 9. データセキュリティ

### 9.1 機密情報の取り扱い

| データ種別 | 機密レベル | 保存場所 | Git管理 |
|-----------|----------|---------|---------|
| 認証情報（パスワード） | 高 | .env | ❌ 除外 |
| 受講生名 | 中 | JSON/CSV | ✅ 任意 |
| レッスンID | 低 | JSON/CSV | ✅ 任意 |
| ログファイル | 中 | output/logs | ❌ 除外 |
| スクリーンショット | 中 | output/screenshots | ❌ 除外 |

### 9.2 .gitignore 設定

```gitignore
# Environment variables with credentials
.env
.env.local
.env.*.local

# Output files (may contain personal information)
output/
*.log
*.png
*.jpg
*.json
*.csv

# Keep template and example outputs
!.env.template
!examples/output/
```

---

## 10. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-11-01 | 1.0 | 初版作成 | - |

---

## 11. 参考資料

- [システム設計書](./terakoya_system_design.md)
- [API仕様書](./terakoya_api_specification.md)
- [セキュリティ設計書](./terakoya_security_design.md)
- [実装計画書](../plans/terakoya_invoice_automation.md)
