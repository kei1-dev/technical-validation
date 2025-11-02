# Samurai Terakoya 請求申請自動化 - セキュリティ設計書

## 1. 概要

### 1.1 目的
Terakoya請求申請自動化システムにおけるセキュリティリスクを特定し、対策を定義します。
認証情報の保護、重複申請の防止、監査証跡の確保など、安全な自動化を実現します。

### 1.2 対象範囲
- 認証情報の管理
- 重複申請の防止
- エラーハンドリングとリトライ
- ログとトレーサビリティ
- データ保護

## 2. セキュリティリスク分析

### 2.1 リスクマトリクス

| リスク | 発生確率 | 影響度 | リスクレベル | 対策優先度 |
|--------|---------|--------|-------------|-----------|
| 認証情報の漏洩 | 中 | 高 | **高** | 1 |
| 重複申請 | 中 | 高 | **高** | 1 |
| 誤った金額での申請 | 低 | 高 | 中 | 2 |
| セッションタイムアウト | 高 | 中 | 中 | 2 |
| ネットワークエラー | 中 | 中 | 中 | 3 |
| サイト構造変更 | 低 | 中 | 低 | 4 |

### 2.2 脅威モデル

#### 2.2.1 認証情報の漏洩
- **脅威**: パスワード等がコードやログに記録され、外部に漏洩
- **攻撃者**: 内部関係者、外部攻撃者（リポジトリ侵害時）
- **影響**: 不正ログイン、不正な請求申請
- **対策**: 環境変数管理、.gitignore設定、ログマスキング

#### 2.2.2 重複申請
- **脅威**: 同一レッスンに対して複数回請求申請
- **攻撃者**: なし（システムバグまたは操作ミス）
- **影響**: 二重請求、信用失墜
- **対策**: 重複チェック、最終確認プロンプト

#### 2.2.3 誤った金額での申請
- **脅威**: 単価や時間の設定ミス
- **攻撃者**: なし（設定ミス）
- **影響**: 過少/過大請求
- **対策**: バリデーション、最終確認プロンプト、監査ログ

#### 2.2.4 セッションハイジャック
- **脅威**: セッションタイムアウト時の予期しない動作
- **攻撃者**: なし（タイミング問題）
- **影響**: 処理失敗、部分的な申請
- **対策**: セッション管理、自動再ログイン

---

## 3. 認証情報の保護

### 3.1 環境変数による管理

#### 3.1.1 .env ファイル

**保存場所**: プロジェクトルート（`/Users/keiichi/Documents/technical-validation/selenium-automation/.env`）

**構造**:
```bash
# Terakoya Login Credentials
# WARNING: Never commit this file to Git
TERAKOYA_EMAIL=actual_email@example.com
TERAKOYA_PASSWORD=actual_secure_password
TERAKOYA_URL=https://terakoya.sejuku.net/

# AI Extraction Settings
TERAKOYA_USE_AI_EXTRACTION=true
TERAKOYA_AI_BATCH_SIZE=10

# Vertex AI Authentication
ANTHROPIC_VERTEX_PROJECT_ID=your-project-id
CLOUD_ML_REGION=global
ANTHROPIC_MODEL=claude-sonnet-4-5@20250929
```

**セキュリティ要件**:
- ✅ `.gitignore` に登録済み
- ✅ ファイルパーミッション: 600（所有者のみ読み書き可）
- ✅ バックアップ時は暗号化
- ❌ Slackやメールで送信しない
- ❌ スクリーンショットに含めない

**設定方法**:
```bash
# 1. テンプレートをコピー
cp .env.template .env

# 2. パーミッション設定
chmod 600 .env

# 3. エディタで編集（実際の認証情報を入力）
nano .env
```

#### 3.1.2 .env.template ファイル

**保存場所**: プロジェクトルート（Git管理対象）

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
```

**セキュリティ要件**:
- ✅ プレースホルダーのみ記載
- ✅ Git管理対象
- ✅ 実際の認証情報は含まない

#### 3.1.3 コマンドライン引数による管理（推奨）

**セキュリティ上の推奨方法**

パスワードを`.env`ファイルに保存せず、実行時に指定することを推奨します。

**方法1: コマンドライン引数（最推奨）**
```bash
python examples/terakoya_invoice.py --month 2025-11 --password "your_password"
```

**方法2: 環境変数（セッション限定）**
```bash
export TERAKOYA_PASSWORD="your_password"
python examples/terakoya_invoice.py --month 2025-11
```

**方法3: .envファイル（非推奨 - ローカルテストのみ）**
```bash
# .envファイルに記載（.gitignoreに登録されているがコミットしないこと）
TERAKOYA_PASSWORD=your_password
```

**優先順位**

スクリプトは以下の順序でパスワードを検索します：

1. `--password` コマンドライン引数（最優先）
2. `TERAKOYA_PASSWORD` 環境変数
3. `.env` ファイルの `TERAKOYA_PASSWORD`（後方互換性）

**セキュリティ上の利点**

- ✅ `.env`ファイルをGitにコミット可能（パスワードを含まないため）
- ✅ パスワードがファイルシステムに永続的に残らない
- ✅ セッション終了時に自動的に削除される
- ✅ 複数環境で異なるパスワードを使い分け可能
- ⚠️ コマンド履歴に残る点に注意（`history -c`で削除可能）

**リスクと対策**

| リスク | 対策 |
|--------|------|
| コマンド履歴への記録 | `history -c` または `HISTCONTROL=ignorespace` 設定 |
| プロセスリストでの可視化 | 短時間実行で最小化、環境変数使用を推奨 |
| ターミナル履歴の共有 | 実行後に履歴をクリア |

**使用例**

```bash
# 推奨: コマンドライン引数
python examples/terakoya_invoice.py \
  --month 2025-11 \
  --password "your_secure_password" \
  --dry-run

# 代替: 環境変数（履歴に残らない）
read -s TERAKOYA_PASSWORD
export TERAKOYA_PASSWORD
python examples/terakoya_invoice.py --month 2025-11
```

### 3.2 コード内での取り扱い

#### 3.2.1 Config クラス

```python
# src/utils/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # .envファイルを読み込み
        load_dotenv()

        # 環境変数から取得（デフォルト値なし）
        self._terakoya_email = os.getenv("TERAKOYA_EMAIL")
        self._terakoya_password = os.getenv("TERAKOYA_PASSWORD")
        self._terakoya_url = os.getenv("TERAKOYA_URL")

    @property
    def terakoya_email(self) -> str:
        """メールアドレス取得（マスキング付きログ出力用）"""
        if not self._terakoya_email:
            raise ValueError("TERAKOYA_EMAIL is not set")
        return self._terakoya_email

    @property
    def terakoya_password(self) -> str:
        """パスワード取得（ログ出力禁止）"""
        if not self._terakoya_password:
            raise ValueError("TERAKOYA_PASSWORD is not set")
        return self._terakoya_password

    def validate(self) -> bool:
        """設定値の検証"""
        try:
            # 必須項目チェック
            assert self._terakoya_email, "TERAKOYA_EMAIL is required"
            assert self._terakoya_password, "TERAKOYA_PASSWORD is required"
            assert self._terakoya_url, "TERAKOYA_URL is required"

            # フォーマットチェック
            assert "@" in self._terakoya_email, "Invalid email format"
            assert len(self._terakoya_password) >= 8, "Password too short"

            return True
        except AssertionError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

# シングルトンインスタンス
config = Config()
```

#### 3.2.2 使用例（安全）

```python
# ✅ 正しい使用方法
from utils.config import config

# ログイン処理
client.login(
    email=config.terakoya_email,
    password=config.terakoya_password
)

# ログ出力（マスキング）
logger.info(f"ログイン試行: {mask_email(config.terakoya_email)}")
# 出力例: "ログイン試行: u***@example.com"
```

#### 3.2.3 使用例（危険）

```python
# ❌ 絶対にやってはいけない
# パスワードをハードコード
client.login(email="user@example.com", password="my_password")

# ❌ パスワードをログ出力
logger.info(f"パスワード: {config.terakoya_password}")

# ❌ パスワードをファイルに保存
with open("credentials.txt", "w") as f:
    f.write(f"Password: {config.terakoya_password}")
```

### 3.3 ログマスキング

#### 3.3.1 マスキング関数

```python
# src/utils/logger.py
import re

def mask_email(email: str) -> str:
    """メールアドレスをマスキング"""
    if not email or "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    masked_local = local[0] + "***" if len(local) > 0 else "***"
    return f"{masked_local}@{domain}"

def mask_password(password: str) -> str:
    """パスワードを完全にマスキング"""
    return "********"

# 使用例
logger.info(f"ログイン: {mask_email('user@example.com')}")
# 出力: "ログイン: u***@example.com"
```

### 3.4 Vertex AI認証

#### 3.4.1 Application Default Credentials (ADC)

AI抽出機能は Google Cloud の Vertex AI を利用します。認証には Application Default Credentials を使用します。

**認証設定**:
```bash
# Google Cloud認証
gcloud auth application-default login

# プロジェクトIDを環境変数に設定
export ANTHROPIC_VERTEX_PROJECT_ID="your-project-id"
```

**セキュリティ要件**:
- ✅ ADCは`~/.config/gcloud/application_default_credentials.json`に保存（`.gitignore`対象外のため注意）
- ✅ 認証情報は個人のGoogleアカウントに紐付け
- ✅ プロジェクトIDは環境変数で管理
- ❌ サービスアカウントキーをコードに埋め込まない
- ❌ ADC認証ファイルをGitに含めない

#### 3.4.2 AI API利用時のセキュリティ考慮事項

**データ送信**:
- レッスンカードのテキストのみを送信（認証情報は含まれない）
- 送信データ: 日付、生徒名、カテゴリ、時間の情報のみ
- 送信しないデータ: パスワード、セッションID、Cookie

**レート制限**:
- バッチサイズで制御（デフォルト: 10件/回）
- API呼び出し頻度の上限遵守

**フォールバック**:
- AI抽出失敗時は正規表現ベースの抽出に自動切り替え
- API障害時もシステム全体は継続動作

#### 3.3.2 ログフィルタ

```python
import logging

class SensitiveDataFilter(logging.Filter):
    """機密情報を自動マスキングするフィルタ"""

    def filter(self, record):
        # パスワードパターンをマスキング
        record.msg = re.sub(
            r'password["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
            r'password: ********',
            str(record.msg),
            flags=re.IGNORECASE
        )
        return True

# ロガーにフィルタを追加
logger = logging.getLogger("terakoya_automation")
logger.addFilter(SensitiveDataFilter())
```

### 3.4 .gitignore 設定

```gitignore
# Environment variables with credentials
# WARNING: .env may contain sensitive information (passwords, API keys)
.env
.env.local
.env.*.local

# Template file (no credentials) is safe to commit
!.env.template

# Output files that may contain personal information
output/
*.log
*.png
*.json
*.csv

# Keep example outputs for documentation
!examples/output/
```

---

## 4. 重複申請の防止

### 4.1 重複チェックメカニズム

#### 4.1.1 チェックフロー

```
[レッスン取得]
      │
      ▼
[既存申請取得]
      │
      ▼
[重複判定ループ]
   for each レッスン:
      │
      ├─ generate_duplicate_key(lesson)
      │  │
      │  ├─ レッスンIDがある → "{date}_{student_id}_{lesson_id}"
      │  └─ レッスンIDがない → "{date}_{student_id}"
      │
      ├─ 既存キーセットと照合
      │  │
      │  ├─ 一致 → InvoiceStatus.SKIPPED
      │  └─ 不一致 → 請求項目追加へ
      │
      └─ ログ記録
```

#### 4.1.2 実装

```python
# src/automation/terakoya.py
from typing import Dict, List, Set

class TerakoyaClient:
    def generate_duplicate_key(self, lesson: Dict) -> str:
        """重複チェック用の一意キーを生成

        Args:
            lesson: レッスン情報

        Returns:
            重複チェック用キー
        """
        # レッスンIDがある場合はIDベースで判定
        if lesson.get('id'):
            return f"{lesson['date']}_{lesson['student_id']}_{lesson['id']}"

        # レッスンIDがない場合は日付+受講生で判定
        return f"{lesson['date']}_{lesson['student_id']}"

    def is_duplicate(
        self,
        lesson: Dict,
        existing_invoices: List[Dict]
    ) -> bool:
        """既存申請との重複チェック

        Args:
            lesson: チェック対象のレッスン
            existing_invoices: 既存の請求申請リスト

        Returns:
            重複している場合True
        """
        lesson_key = self.generate_duplicate_key(lesson)
        existing_keys: Set[str] = {
            self.generate_duplicate_key(inv)
            for inv in existing_invoices
        }

        if lesson_key in existing_keys:
            logger.warning(f"重複申請を検出: {lesson_key}")
            return True

        return False
```

#### 4.1.3 使用例

```python
# メインスクリプト
lessons = client.get_lessons_for_month(2025, 10)
existing = client.get_existing_invoices()

duplicates = []
new_lessons = []

for lesson in lessons:
    if client.is_duplicate(lesson, existing):
        duplicates.append(lesson)
        logger.info(f"スキップ（重複）: {lesson['date']} - {lesson['student_name']}")
    else:
        new_lessons.append(lesson)

logger.info(f"既存申請: {len(duplicates)}件、未申請: {len(new_lessons)}件")
```

### 4.2 最終確認プロンプト

#### 4.2.1 実装

```python
# examples/terakoya_invoice.py
def confirm_submission(summary: Dict) -> bool:
    """申請送信前の最終確認

    Args:
        summary: 申請内容のサマリー

    Returns:
        ユーザーが承認した場合True
    """
    print("\n" + "="*60)
    print("請求申請内容の最終確認")
    print("="*60)
    print(f"対象月: {summary['target_month']}")
    print(f"取得レッスン数: {summary['total_lessons']}件")
    print(f"既存申請: {summary['existing_invoices']}件")
    print(f"新規追加: {summary['success']}件")
    print(f"失敗: {summary['failed']}件")
    print(f"スキップ: {summary['skipped']}件")
    print("="*60)

    # 失敗があれば警告
    if summary['failed'] > 0:
        print(f"\n⚠️  警告: {summary['failed']}件の追加に失敗しました")
        print("エラーログとスクリーンショットを確認してください\n")

    # 確認プロンプト
    while True:
        response = input("申請を送信しますか？ (y/n): ").lower().strip()
        if response == 'y':
            return True
        elif response == 'n':
            print("申請を中止しました")
            return False
        else:
            print("'y' または 'n' を入力してください")

# メイン処理
if not args.dry_run:
    if confirm_submission(summary):
        client.submit_invoice()
        logger.info("申請送信完了")
    else:
        logger.info("ユーザーにより中止されました")
```

#### 4.2.2 出力例

```
============================================================
請求申請内容の最終確認
============================================================
対象月: 2025-10
取得レッスン数: 25件
既存申請: 5件
新規追加: 18件
失敗: 2件
スキップ: 5件
============================================================

⚠️  警告: 2件の追加に失敗しました
エラーログとスクリーンショットを確認してください

申請を送信しますか？ (y/n):
```

---

## 5. エラーハンドリング

### 5.1 エラー分類

| エラータイプ | 対応 | リトライ | ログレベル |
|------------|------|---------|-----------|
| TimeoutException | 2秒待機後リトライ | ✅ 最大3回 | WARNING |
| NoSuchElementException | スキップ | ❌ | ERROR |
| SessionExpiredError | 再ログイン | ✅ 1回 | WARNING |
| ValidationError | スキップ | ❌ | ERROR |
| NetworkError | リトライ | ✅ 最大3回 | WARNING |
| UnexpectedError | スキップ | ❌ | ERROR |

### 5.2 リトライロジック

#### 5.2.1 実装

```python
# src/automation/terakoya.py
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class TerakoyaClient:
    def add_invoice_item_with_retry(
        self,
        lesson: Dict,
        max_retries: int = 3
    ) -> InvoiceResult:
        """リトライ機能付き請求項目追加

        Args:
            lesson: レッスン情報
            max_retries: 最大リトライ回数

        Returns:
            InvoiceResult: 処理結果
        """
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"請求項目追加試行 {attempt + 1}/{max_retries}: "
                    f"{lesson.get('id')}"
                )

                # 請求項目追加処理
                success = self._add_invoice_item_internal(lesson)

                if success:
                    logger.info(f"請求項目追加成功: {lesson.get('id')}")
                    return InvoiceResult(
                        lesson=lesson,
                        status=InvoiceStatus.SUCCESS,
                        retry_count=attempt
                    )

            except TimeoutException as e:
                logger.warning(
                    f"タイムアウトエラー (試行 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2)  # 2秒待機後リトライ
                else:
                    screenshot_path = self._save_error_screenshot(lesson)
                    return InvoiceResult(
                        lesson=lesson,
                        status=InvoiceStatus.FAILED,
                        error_message=f"タイムアウト: {str(e)}",
                        retry_count=attempt + 1,
                        screenshot_path=screenshot_path
                    )

            except NoSuchElementException as e:
                logger.error(f"要素が見つかりません: {e}")
                screenshot_path = self._save_error_screenshot(lesson)
                return InvoiceResult(
                    lesson=lesson,
                    status=InvoiceStatus.FAILED,
                    error_message=f"要素未検出: {str(e)}",
                    retry_count=attempt + 1,
                    screenshot_path=screenshot_path
                )

            except Exception as e:
                logger.error(f"予期しないエラー: {e}", exc_info=True)
                screenshot_path = self._save_error_screenshot(lesson)
                return InvoiceResult(
                    lesson=lesson,
                    status=InvoiceStatus.FAILED,
                    error_message=f"未知のエラー: {str(e)}",
                    retry_count=attempt + 1,
                    screenshot_path=screenshot_path
                )

        # 全リトライ失敗
        return InvoiceResult(
            lesson=lesson,
            status=InvoiceStatus.FAILED,
            error_message="最大リトライ回数に達しました",
            retry_count=max_retries
        )
```

### 5.3 セッション管理

#### 5.3.1 セッションチェック

```python
class SessionExpiredError(Exception):
    """セッション期限切れエラー"""
    pass

class TerakoyaClient:
    def check_session_validity(self) -> bool:
        """セッションの有効性チェック

        Returns:
            セッションが有効な場合True
        """
        try:
            # ログイン状態を示す要素の存在確認
            self.browser.find_element(
                By.CSS_SELECTOR,
                ".user-menu",
                timeout=5
            )
            return True
        except (TimeoutException, NoSuchElementException):
            logger.warning("セッションが無効です")
            return False

    def ensure_logged_in(self) -> bool:
        """ログイン状態の確保（必要に応じて再ログイン）

        Returns:
            ログイン成功の場合True

        Raises:
            SessionExpiredError: 再ログインに失敗
        """
        if self.check_session_validity():
            logger.debug("セッションは有効です")
            return True

        logger.info("セッションが切れているため再ログイン")

        # 再ログイン試行
        success = self.login(self.email, self.password)

        if not success:
            raise SessionExpiredError("再ログインに失敗しました")

        logger.info("再ログイン成功")
        return True
```

---

## 6. 監査証跡（トレーサビリティ）

### 6.1 ログ出力

#### 6.1.1 ログレベル

| レベル | 用途 | 例 |
|-------|------|---|
| DEBUG | デバッグ情報 | セレクタ値、要素の属性 |
| INFO | 通常動作 | ログイン成功、レッスン取得完了 |
| WARNING | 注意すべき事象 | タイムアウト、重複検出 |
| ERROR | エラー発生 | 要素未検出、処理失敗 |
| CRITICAL | 致命的エラー | 設定不正、システムエラー |

#### 6.1.2 ログフォーマット

```python
# src/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(
    name: str = "selenium_automation",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """ロガーのセットアップ"""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # フォーマット定義
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラ（ローテーション付き）
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 機密情報フィルタを追加
    logger.addFilter(SensitiveDataFilter())

    return logger
```

#### 6.1.3 重要イベントのログ出力

```python
# ログイン
logger.info(f"ログイン試行: {mask_email(email)}")
logger.info("ログイン成功")

# レッスン取得
logger.info(f"レッスンデータ取得開始: {year}-{month:02d}")
logger.info(f"取得したレッスン数: {len(lessons)}件")

# 重複チェック
logger.info(f"既存申請: {len(existing)}件、未申請: {len(new_lessons)}件")
logger.warning(f"重複申請を検出: {duplicate_key}")

# 請求項目追加
logger.info(f"請求項目追加: {lesson['id']} - {lesson['student_name']}")
logger.info(f"請求項目追加成功: {lesson['id']}")
logger.error(f"請求項目追加失敗: {lesson['id']}: {error_message}")

# 送信
logger.info("申請送信開始")
logger.info("申請送信完了")
```

### 6.2 スクリーンショット

#### 6.2.1 保存タイミング

| タイミング | ファイル名 | 目的 |
|----------|-----------|------|
| ログイン成功後 | `login_success.png` | ログイン確認 |
| レッスン取得後 | `lessons_retrieved.png` | データ取得確認 |
| 各項目追加後 | `invoice_item_{index}.png` | 追加確認 |
| エラー発生時 | `error_{lesson_id}_{timestamp}.png` | エラー調査 |
| 送信完了後 | `invoice_submitted.png` | 送信確認 |

#### 6.2.2 実装

```python
# src/automation/terakoya.py
from datetime import datetime
from pathlib import Path

class TerakoyaClient:
    def _save_screenshot(self, name: str) -> str:
        """スクリーンショット保存

        Args:
            name: ファイル名（拡張子なし）

        Returns:
            保存先パス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = config.output_dir / "terakoya_screenshots" / filename

        # ディレクトリ作成
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # スクリーンショット保存
        self.browser.screenshot(str(filepath))
        logger.debug(f"スクリーンショット保存: {filepath}")

        return str(filepath)

    def _save_error_screenshot(self, lesson: Dict) -> str:
        """エラー時のスクリーンショット保存

        Args:
            lesson: レッスン情報

        Returns:
            保存先パス
        """
        lesson_id = lesson.get('id', 'unknown')
        return self._save_screenshot(f"error_{lesson_id}")
```

### 6.3 データファイル保存

#### 6.3.1 保存タイミング

```python
# examples/terakoya_invoice.py
from utils.file_utils import save_json

# レッスンデータ保存
lessons_file = config.output_dir / f"terakoya_data/lessons_{year}-{month:02d}.json"
save_json({
    "metadata": {
        "target_month": f"{year}-{month:02d}",
        "retrieved_at": datetime.now().isoformat(),
        "total_count": len(lessons)
    },
    "lessons": lessons
}, lessons_file)

# サマリー保存
summary_file = config.output_dir / f"terakoya_data/summary_{year}-{month:02d}_{timestamp}.json"
save_json(summary, summary_file)

# エラーログ保存（失敗があった場合）
if failed_results:
    errors_file = config.output_dir / f"terakoya_data/errors_{year}-{month:02d}_{timestamp}.json"
    save_json({
        "target_month": f"{year}-{month:02d}",
        "error_count": len(failed_results),
        "errors": [result.to_dict() for result in failed_results]
    }, errors_file)
```

---

## 7. データ保護

### 7.1 個人情報の取り扱い

#### 7.1.1 含まれる個人情報

| データ種別 | 個人情報 | 保存場所 | 保護レベル |
|-----------|---------|---------|-----------|
| 受講生名 | ✅ | JSON/CSV | 中 |
| メールアドレス | ✅ | .env | 高 |
| レッスン日 | △ | JSON/CSV | 低 |
| レッスンID | ❌ | JSON/CSV | 低 |

#### 7.1.2 保護対策

```python
# 1. ファイルパーミッション設定
import os

def secure_file_permissions(filepath: Path):
    """ファイルパーミッションを安全に設定"""
    os.chmod(filepath, 0o600)  # 所有者のみ読み書き可

# 2. 暗号化（Phase 2検討中）
from cryptography.fernet import Fernet

def encrypt_file(filepath: Path, key: bytes):
    """ファイルを暗号化"""
    fernet = Fernet(key)
    with open(filepath, 'rb') as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    with open(filepath, 'wb') as f:
        f.write(encrypted)
```

### 7.2 データ保持期間

| データ種別 | 保持期間 | 削除方法 |
|-----------|---------|---------|
| ログファイル | 90日 | 自動削除スクリプト |
| スクリーンショット | 30日 | 自動削除スクリプト |
| データファイル | 1年 | 手動削除 |

---

## 8. セキュリティチェックリスト

### 8.1 実装前チェック

- [ ] `.env`ファイルが`.gitignore`に登録されている
- [ ] `.env.template`に実際の認証情報が含まれていない
- [ ] パスワードがコード内にハードコードされていない
- [ ] ログ出力にパスワードが含まれていない
- [ ] 重複チェックロジックが実装されている
- [ ] 最終確認プロンプトが実装されている
- [ ] エラーハンドリングが実装されている
- [ ] スクリーンショット保存が実装されている

### 8.2 テスト前チェック

- [ ] ドライランモードで動作確認済み
- [ ] 重複チェックが正しく動作する
- [ ] エラー時にスクリーンショットが保存される
- [ ] ログファイルが正しく出力される
- [ ] 環境変数が正しく読み込まれる
- [ ] バリデーションが正しく動作する

### 8.3 本番実行前チェック

- [ ] `.env`ファイルに正しい認証情報が設定されている
- [ ] 対象月が正しい
- [ ] ドライランで動作確認済み
- [ ] ログ出力先ディレクトリが存在する
- [ ] 既存申請を確認済み
- [ ] 最終確認プロンプトが有効

---

## 9. インシデント対応

### 9.1 インシデント分類

| インシデント | 重要度 | 対応時間 | 対応者 |
|------------|-------|---------|--------|
| 認証情報漏洩 | 🔴 Critical | 即座 | 管理者 |
| 重複申請 | 🟠 High | 24時間以内 | 管理者 |
| 処理失敗 | 🟡 Medium | 1週間以内 | 開発者 |
| ログエラー | 🟢 Low | 次回保守時 | 開発者 |

### 9.2 認証情報漏洩時の対応

#### 手順

1. **即座にパスワード変更**
   ```bash
   # Terakoyaサイトでパスワード変更
   # .envファイルを更新
   nano .env
   ```

2. **影響範囲の調査**
   - ログファイルを確認
   - Gitコミット履歴を確認
   - アクセスログを確認

3. **漏洩源の特定と封じ込め**
   - Gitリポジトリから削除（必要に応じて）
   - スクリーンショットを確認

4. **報告と記録**
   - インシデントレポート作成
   - 管理者へ報告

### 9.3 重複申請時の対応

#### 手順

1. **申請状況の確認**
   ```bash
   # ログファイルを確認
   grep "重複申請" output/terakoya_logs/*.log
   ```

2. **サイト上で確認**
   - Terakoyaサイトで請求申請一覧を確認
   - 重複項目を特定

3. **削除または修正**
   - サイト上で重複項目を削除
   - 必要に応じて正しい申請を手動追加

4. **原因調査**
   - ログとスクリーンショットを分析
   - 重複チェックロジックを検証

---

## 10. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-11-01 | 1.0 | 初版作成 | - |

---

## 11. 参考資料

- [システム設計書](./terakoya_system_design.md)
- [API仕様書](./terakoya_api_specification.md)
- [データ構造設計書](./terakoya_data_structure.md)
- [実装計画書](../plans/terakoya_invoice_automation.md)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [セキュアコーディングガイドライン](https://www.ipa.go.jp/security/vuln/securecodingguide.html)
