# Samurai Terakoya 請求申請自動化 - 実装計画書

## 概要

Samurai Terakoyaの月次請求申請作業を自動化するスクリプトを実装します。
Seleniumによる画面操作とVertex AI（Claude）による知的処理を組み合わせて、安全かつ効率的な自動化を実現します。

**作業対象:** 2025年10月分の請求申請（将来的には任意の月に対応）

## 業務フロー

### 現在の手作業フロー
1. terakoya.sejuku.net にログイン
2. 「レッスン→専属レッスン」から対象月のレッスン一覧を確認
3. 「請求申請」画面で請求申請月を選択（2025/10）
4. 各レッスンに対して請求項目を追加：
   - モーダルを開く
   - 日付、カテゴリー（専属レッスン）、受講生、レッスンを選択
   - 時間: 60、単価: 2,300 を入力
   - 「追加」ボタンをクリック
5. すべてのレッスンを登録後、申請を送信

### 自動化後のフロー
1. スクリプト実行（対象月を指定）
2. 自動でログイン・データ取得・申請項目追加
3. 最終確認プロンプトで内容確認
4. 確認後、自動送信

## セキュリティとリスク管理

### 1. 認証情報の保護
- パスワード等をコードに直接記載しない
- `.env` ファイルに保存（Gitignore済み）
- 環境変数から読み込み

### 2. 重複申請の防止
- スクリプト実行前に既存の請求申請を確認
- 既に申請済みのレッスンはスキップ
- 重複チェック結果をログに記録

### 3. 最終確認ステップ
- すべての請求項目を追加した後、送信前に一時停止
- 申請内容をコンソールに表示
- ユーザーが「y」を入力するまで送信しない

### 4. ログとトレーサビリティ
- 全処理の詳細ログをファイルに保存
- 各ステップでスクリーンショットを保存
- エラー発生時は詳細なエラー情報を記録

### 5. エラーハンドリング
- ネットワークエラー、タイムアウトに対応
- 要素が見つからない場合のリトライ処理
- エラー発生時はブラウザを閉じて安全に終了

## 実装ファイル構成

```
selenium-automation/
├── plans/
│   └── terakoya_invoice_automation.md  # この計画書
├── src/
│   └── automation/
│       └── terakoya.py                  # Terakoya固有の操作クラス
├── examples/
│   └── terakoya_invoice.py              # メインスクリプト
├── output/
│   ├── terakoya_logs/                   # ログファイル保存先
│   └── terakoya_screenshots/            # スクリーンショット保存先
└── .env                                 # 認証情報（更新）
```

## 詳細設計

### 1. 環境変数設定 (.env)

追加する項目:
```bash
# Terakoya Login Credentials
# 注意: 実際の認証情報は.envファイルに記載し、Gitにコミットしないこと
TERAKOYA_EMAIL=your_email@example.com
TERAKOYA_PASSWORD=your_secure_password
TERAKOYA_URL=https://terakoya.sejuku.net/

# Invoice Settings
TERAKOYA_LESSON_DURATION=60
TERAKOYA_LESSON_UNIT_PRICE=2300

# AI Extraction Settings
TERAKOYA_USE_AI_EXTRACTION=true
TERAKOYA_AI_BATCH_SIZE=10
```

**重要**: 実際の認証情報は`.env`ファイルに記載し、**絶対にGitにコミットしないこと**。`.env`ファイルは`.gitignore`に含まれています。

### 2. Terakoya操作クラス (src/automation/terakoya.py)

```python
class TerakoyaClient:
    """Samurai Terakoya操作クラス"""

    def __init__(self, browser: Browser):
        """初期化"""

    def login(self, email: str, password: str) -> bool:
        """ログイン処理"""

    def get_lessons_for_month(self, year: int, month: int) -> List[Dict]:
        """指定月のレッスン一覧を取得"""

    def navigate_to_invoice_page(self, year: int, month: int):
        """請求申請ページへ移動し、対象月を設定"""

    def get_existing_invoices(self) -> List[Dict]:
        """既存の請求申請を取得（重複防止用）"""

    def add_invoice_item(self, lesson: Dict) -> bool:
        """請求項目を追加

        Args:
            lesson: レッスン情報
                - date: レッスン日
                - student_name: 受講生名
                - lesson_id: レッスンID
                - duration: 時間（デフォルト60）
                - unit_price: 単価（デフォルト2300）
        """

```

#### 主要メソッドの実装詳細

##### login()
1. トップページにアクセス
2. 「ログインする」ボタンをクリック
3. メールアドレスとパスワードを入力
4. ログインボタンをクリック
5. ログイン成功を確認（ダッシュボード表示）

##### get_lessons_for_month()
1. 左メニュー「レッスン→専属レッスン」をクリック
2. JavaScriptを使用してレッスンカードの「編集」ボタンを検出（最大100件）
   - `textContent.trim() === '編集'` で完全一致検索（「受講履歴編集」を除外）
3. 各カードのテキストを取得
4. AI抽出（主要）または正規表現（フォールバック）で各レッスンの情報を抽出:
   - **AI抽出**: Claude Sonnet 4.5を使用したバッチ処理（デフォルト10件/回）
     - 環境変数: `TERAKOYA_USE_AI_EXTRACTION=true`、`TERAKOYA_AI_BATCH_SIZE=10`
   - **正規表現抽出**: AI失敗時の自動フォールバック
   - レッスン日（MM/DD形式からYYYY-MM-DD形式へ変換）
   - 受講生名（人名のみ、「最終レッ」「キャンセ」等のステータス語を除外）
   - カテゴリ（専属レッスン/初回レッスン/エキスパートコース等）
   - 時間（開始・終了時刻から計算）
5. 重複削除（date + student_nameの組み合わせ）を実行
6. List[LessonData]形式で返却

##### navigate_to_invoice_page()
1. `/claim` URLへ直接遷移
2. ページ読み込みを待機（2秒）
3. 画面右上「請求申請月」ドロップダウンを探す
4. 対象月（YYYY/MM形式、例: 2025/10）を選択
5. ページ更新を待機（2秒）
6. ドロップダウン選択失敗時は警告ログを記録して継続

##### get_existing_invoices()
1. 請求申請ページで既存の申請項目を取得
2. テーブルまたはリストから申請済みレッスン情報を抽出
3. 重複チェック用のキー（レッスンIDまたは日付+受講生）を生成
4. List[Dict]形式で返却

**重複判定ロジックの詳細:**
```python
def generate_duplicate_key(self, lesson: Dict) -> str:
    """重複チェック用の一意キーを生成

    Args:
        lesson: レッスン情報

    Returns:
        重複チェック用キー（例: "2025-10-15_student_789_lesson_12345"）
    """
    # レッスンIDがある場合はIDベースで判定
    if lesson.get('id'):
        return f"{lesson['date']}_{lesson['student_id']}_{lesson['id']}"
    # レッスンIDがない場合は日付+受講生で判定
    return f"{lesson['date']}_{lesson['student_id']}"

def is_duplicate(self, lesson: Dict, existing_invoices: List[Dict]) -> bool:
    """既存申請との重複チェック

    Args:
        lesson: チェック対象のレッスン
        existing_invoices: 既存の請求申請リスト

    Returns:
        重複している場合True
    """
    lesson_key = self.generate_duplicate_key(lesson)
    existing_keys = {self.generate_duplicate_key(inv) for inv in existing_invoices}

    if lesson_key in existing_keys:
        logger.warning(f"重複申請を検出: {lesson_key}")
        return True

    return False
```

##### add_invoice_item()
1. 「請求項目の追加」ボタンをJavaScriptでクリック
2. モーダルが開くまで待機（1.5秒）
3. フィールドに入力:
   - 日付: React DatePickerにJavaScript経由で値を設定（YYYY年MM月DD日形式）
   - カテゴリー: カテゴリ名を数値ID（1-26）にマッピングして選択
   - 受講生: 標準SELECT or カスタムReactドロップダウン（検索機能付き）から選択
   - 専属レッスン: API非同期読み込み後（最大12秒待機）、レッスン一覧から選択
   - 時間: JavaScript経由で値を設定（60）
   - 単価: JavaScript経由で値を設定（2300）
4. dry_runモードの場合: スクリーンショット保存してモーダルを開いたまま終了
5. 通常モードの場合: モーダル下部の「追加」ボタンをクリック
6. モーダルが閉じるまで待機
7. 成功/失敗を返却

**サポートするカテゴリ（26種類）**:
専属レッスン(1)、専属レッスン前後対応(2)、質問対応(担当生徒)(3)、カリキュラム作成(4)、
ポートフォリオ添削(5)、チャット質問対応(6)、教材作成(7)、技術ブログ執筆(8)、勉強会開催(9)、
メンタリング(10)、その他業務(11)、初回レッスン(12)、単発レッスン(15)、エキスパートコース(16)、
専属レッスンコンサル(17)、勉強会登壇(18)、イベント運営(19)、面談(20)、チーム開発サポート(21)、
企業研修(22)、インターン指導(23)、コミュニティ運営(24)、広報活動(25)、公開講座対応(26)

### 3. メインスクリプト (examples/terakoya_invoice.py)

```python
#!/usr/bin/env python
"""
Samurai Terakoya 請求申請自動化スクリプト

Usage:
    # 10月分の請求申請を実行
    pipenv run python examples/terakoya_invoice.py --month 2025-10

    # ドライラン（フォーム入力のみ、送信しない、モーダルは開いたまま）
    pipenv run python examples/terakoya_invoice.py --month 2025-10 --dry-run

    # ヘッドレスモードで実行
    pipenv run python examples/terakoya_invoice.py --month 2025-10 --headless
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# モジュールインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation.browser import Browser
from automation.terakoya import TerakoyaClient
from utils.logger import setup_logger
from utils.config import config
from utils.file_utils import save_json, generate_filename

def parse_arguments():
    """コマンドライン引数の解析"""

def main():
    """メイン処理"""

    # 1. 初期化
    # 2. ログイン
    # 3. レッスンデータ取得
    # 4. 既存申請確認
    # 5. 未申請レッスンに対して請求項目追加
    # 6. 完了（送信は手動で実行）
```

#### メイン処理フロー

```
1. 引数解析
   ├─ --month: 対象月（YYYY-MM形式）
   ├─ --dry-run: ドライラン（送信しない）
   └─ --headless: ヘッドレスモード

2. 環境変数読み込み
   ├─ TERAKOYA_EMAIL
   ├─ TERAKOYA_PASSWORD
   ├─ TERAKOYA_LESSON_DURATION
   └─ TERAKOYA_LESSON_UNIT_PRICE

3. ロギング設定
   └─ output/terakoya_logs/invoice_{timestamp}.log

4. ブラウザ起動
   └─ Browser(headless=args.headless)

5. ログイン
   ├─ TerakoyaClient.login()
   └─ スクリーンショット保存: login_success.png

6. レッスンデータ取得
   ├─ TerakoyaClient.get_lessons_for_month(year, month)
   ├─ データ保存: lessons_{YYYY-MM}.json
   └─ ログ出力: "取得したレッスン数: X件"

7. 請求申請ページへ移動
   └─ TerakoyaClient.navigate_to_invoice_page(year, month)

8. 既存申請確認
   ├─ TerakoyaClient.get_existing_invoices()
   ├─ 重複チェック
   └─ ログ出力: "既存申請: X件、未申請: Y件"

9. 請求項目追加ループ
   for lesson in未申請レッスン:
       ├─ TerakoyaClient.add_invoice_item(lesson)
       ├─ スクリーンショット: invoice_item_{index}.png
       ├─ 成功/失敗をログ記録
       └─ エラー時はスキップして続行

10. 追加結果サマリー表示
    ├─ 成功: X件
    ├─ 失敗: Y件
    └─ スキップ（既存）: Z件

11. 追加結果サマリー確認
    ├─ 成功件数、失敗件数を表示
    └─ ログ出力: "請求項目の追加が完了しました"

**注意**: 請求書の送信は自動化されていません。Web画面から手動で送信してください。

12. ブラウザクローズ
    └─ 処理完了
```

## データ構造

### レッスン情報 (Lesson)
```python
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

### 請求項目 (Invoice Item)
```python
{
    "date": "2025-10-15",
    "category": "専属レッスン",
    "student_id": "student_789",
    "student_name": "山田太郎",
    "lesson_id": "lesson_12345",
    "duration": 60,
    "unit_price": 2300,
    "total": 2300,
    "status": "added"  # or "failed", "skipped"
}
```

## エラーハンドリング戦略

### データクラス定義

```python
from typing import Optional
from dataclasses import dataclass
from enum import Enum

class InvoiceStatus(Enum):
    """請求項目の処理状態"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"

@dataclass
class InvoiceResult:
    """請求項目追加結果"""
    lesson: Dict
    status: InvoiceStatus
    error_message: Optional[str] = None
    retry_count: int = 0
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict:
        """辞書形式で出力"""
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

### エラーハンドリング実装

#### 1. リトライ機能付き請求項目追加

```python
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
                logger.info(f"請求項目追加試行 {attempt + 1}/{max_retries}: {lesson.get('id')}")

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

    def _save_error_screenshot(self, lesson: Dict) -> str:
        """エラー時のスクリーンショット保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_{lesson.get('id', 'unknown')}_{timestamp}.png"
        filepath = config.output_dir / "terakoya_screenshots" / filename
        self.browser.screenshot(str(filepath))
        return str(filepath)
```

#### 2. セッションタイムアウト対策

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
            # （実際のサイトに合わせて調整）
            self.browser.find_element(By.CSS_SELECTOR, ".user-menu", timeout=5)
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

    def add_invoice_item(self, lesson: Dict) -> InvoiceResult:
        """請求項目追加（セッションチェック付き）"""
        # セッション確認
        try:
            self.ensure_logged_in()
        except SessionExpiredError as e:
            return InvoiceResult(
                lesson=lesson,
                status=InvoiceStatus.FAILED,
                error_message=str(e)
            )

        # 通常の処理
        return self.add_invoice_item_with_retry(lesson)
```

### エラーケース別対応

#### 1. ネットワークエラー
- タイムアウト設定: 30秒
- リトライ: 最大3回（2秒間隔）
- エラー時はログに記録し、スクリーンショット保存

#### 2. 要素が見つからない
- 明示的待機: 最大10秒
- 代替セレクタを試行（実装時に設計）
- 失敗時はスクリーンショット保存してスキップ

#### 3. モーダル操作の失敗
- モーダルが開かない: 2秒待機後リトライ（最大3回）
- 入力失敗: エラーログ記録してスキップ
- 保存失敗: スクリーンショット保存して次のレッスンへ

#### 4. 重複エラー
- 既存申請と照合（`is_duplicate()`メソッド使用）
- 重複は自動スキップ（InvoiceStatus.SKIPPED）
- スキップ件数をログとサマリーに記録

#### 5. ログイン失敗
- 即座に処理中断
- 認証情報の確認を促すメッセージ表示
- スクリーンショット保存
- 終了コード: 1

#### 6. セッションタイムアウト
- 各操作前にセッション有効性チェック
- 無効の場合は自動再ログイン
- 再ログイン失敗時は処理中断

## セレクタ設計（予想）

※実際の実装時に画面を確認して調整が必要

### ログイン画面
```python
LOGIN_BUTTON = "//button[contains(text(), 'ログインする')]"
EMAIL_INPUT = "input[type='email']"
PASSWORD_INPUT = "input[type='password']"
SUBMIT_BUTTON = "button[type='submit']"
```

### レッスン一覧
```python
LESSON_MENU = "//a[contains(text(), 'レッスン')]"
EXCLUSIVE_LESSON_MENU = "//a[contains(text(), '専属レッスン')]"
LESSON_TABLE = "table.lesson-list"
MONTH_FILTER = "select.month-filter"
```

### 請求申請
```python
INVOICE_MENU = "//a[contains(text(), '請求申請')]"
INVOICE_MONTH_SELECT = "select.invoice-month"
ADD_ITEM_BUTTON = "//button[contains(text(), '請求項目の追加')]"
MODAL = ".invoice-modal"
DATE_INPUT = "input[name='date']"
CATEGORY_SELECT = "select[name='category']"
STUDENT_SELECT = "select[name='student']"
LESSON_SELECT = "select[name='lesson']"
DURATION_INPUT = "input[name='duration']"
UNIT_PRICE_INPUT = "input[name='unit_price']"
ADD_BUTTON = ".modal-footer button.btn-danger"
SUBMIT_INVOICE_BUTTON = "//button[contains(text(), '申請を送信')]"
```

## 実装フェーズ

### Phase 0: 基盤コード実装（実装前に必須）

Terakoya固有機能の実装前に、以下の基盤コードを実装・テストする必要があります：

#### 優先度: Critical

##### 1. `src/automation/browser.py` - ブラウザ操作クラス

**実装内容:**
```python
class Browser:
    """Chrome browser automation wrapper."""

    def __init__(self, headless: bool = False, download_dir: Optional[str] = None):
        """Initialize browser instance"""

    def navigate(self, url: str):
        """Navigate to URL"""

    def find_element(self, by: By, value: str, timeout: int = 10):
        """Find element with wait"""

    def click(self, by: By, value: str, timeout: int = 10):
        """Click an element"""

    def input_text(self, by: By, value: str, text: str, timeout: int = 10):
        """Input text into a form field"""

    def wait_for_page_load(self, timeout: int = 30):
        """Wait for page to fully load"""

    def screenshot(self, filepath: str) -> bool:
        """Take screenshot"""

    def close(self):
        """Close browser"""

    def __enter__(self):
        """Context manager entry"""

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
```

**テスト:**
- 基本的なページ遷移
- 要素の検索・クリック
- スクリーンショット保存
- タイムアウト処理

##### 2. `src/utils/logger.py` - ロギング設定

**実装内容:**
```python
def setup_logger(
    name: str = "selenium_automation",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """Setup and configure logger with rotation"""
```

**テスト:**
- ログファイル作成
- ローテーション機能
- コンソール出力

##### 3. `src/utils/config.py` - 設定管理

**実装内容:**
```python
class Config:
    """Application configuration from environment variables"""

    def __init__(self):
        """Load configuration from .env"""

    def validate(self) -> bool:
        """Validate required configuration"""
```

**テスト:**
- 環境変数の読み込み
- バリデーション
- デフォルト値の適用

#### 優先度: High

##### 4. `src/utils/file_utils.py` - ファイル操作ユーティリティ

**実装内容:**
- JSON保存・読み込み
- CSV保存
- ファイル名生成
- ディレクトリ作成

**テスト:**
- ファイル保存・読み込み
- エラーハンドリング

##### 5. `src/automation/scraper.py` - HTML解析クラス

**実装内容:**
```python
class Scraper:
    """HTML parsing and data extraction."""

    def __init__(self, html: str):
        """Initialize with HTML content"""

    def get_text(self, selector: str = None) -> str:
        """Extract text content"""

    def extract_table(self, selector: str = "table") -> Optional[pd.DataFrame]:
        """Extract table data as DataFrame"""

    def extract_structured_data(
        self,
        item_selector: str,
        field_selectors: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Extract structured data"""
```

**テスト:**
- テキスト抽出
- 表データの抽出
- エラーハンドリング

#### 実装スケジュール（Phase 0）

| タスク | 工数 | 依存関係 |
|-------|------|---------|
| Browser クラス実装 | 2日 | なし |
| Browser 単体テスト | 1日 | Browser実装 |
| Logger/Config/FileUtils実装 | 1日 | なし |
| Logger/Config/FileUtils テスト | 0.5日 | 実装完了 |
| Scraper クラス実装 | 1日 | なし |
| Scraper 単体テスト | 0.5日 | Scraper実装 |
| 統合テスト | 1日 | 全実装完了 |

**合計**: 6-7営業日

#### Phase 0完了条件

- [ ] 全クラスの実装完了
- [ ] 単体テストカバレッジ 80%以上
- [ ] 統合テストが全てパス
- [ ] ドキュメント作成完了
- [ ] コードレビュー完了

### Phase 1: Terakoya固有機能実装

Phase 0完了後に以下を実装：

#### 1. サイト調査（1日）
- [ ] 実際のサイトにログイン
- [ ] HTML構造の確認
- [ ] セレクタの実測値取得
- [ ] スクリーンショット・HTMLスナップショット保存

#### 2. TerakoyaClient実装（3-4日）
- [ ] ログイン処理
- [ ] レッスン一覧取得
- [ ] 請求申請ページ操作
- [ ] モーダル操作
- [ ] 重複チェック
- [ ] セッション管理

#### 3. メインスクリプト実装（2日）
- [ ] コマンドライン引数処理
- [ ] メインフロー実装
- [ ] エラーハンドリング
- [ ] ログ出力

#### 4. テストとドキュメント（2-3日）
- [ ] 単体テスト作成
- [ ] 統合テスト作成
- [ ] ドライラン実行
- [ ] ドキュメント作成

**Phase 1合計**: 8-11営業日

### Phase 2: 本番稼働準備（3-5日）

- [ ] 本番環境でのテスト
- [ ] エラーケース対応
- [ ] 運用ドキュメント作成
- [ ] レビュー・承認

**全体スケジュール**: 17-23営業日

## テスト戦略

### 1. 単体テスト
- 各メソッドの動作確認
- モックデータでのテスト

### 2. 統合テスト
- ドライランモードでの全体フロー確認
- ログとスクリーンショットの確認

### 3. 本番実行前のチェックリスト
- [ ] .envファイルに正しい認証情報が設定されている
- [ ] 対象月が正しい（2025-10）
- [ ] ドライランで動作確認済み
- [ ] ログ出力先ディレクトリが存在する
- [ ] Chromeブラウザが最新版
- [ ] Vertex AI認証が有効

## 運用ガイドライン

### 初回実行
```bash
# 1. ドライランで動作確認
pipenv run python examples/terakoya_invoice.py --month 2025-10 --dry-run

# 2. ログとスクリーンショットを確認
# output/terakoya_logs/ と output/terakoya_screenshots/ を確認

# 3. 問題なければ本番実行
pipenv run python examples/terakoya_invoice.py --month 2025-10

# 4. 最終確認プロンプトで "y" を入力
```

### 定期実行
```bash
# 毎月1日に前月分を自動申請する場合
# cronやタスクスケジューラで実行
pipenv run python examples/terakoya_invoice.py --month $(date -d "last month" +%Y-%m)
```

### トラブルシューティング

#### 問題: ログインできない
- 認証情報を確認
- パスワードが変更されていないか
- サイトのログインフォームが変更されていないか

#### 問題: レッスンが取得できない
- 対象月にレッスンが存在するか確認
- セレクタが変更されていないか
- スクリーンショットで画面状態を確認

#### 問題: モーダルが開かない
- JavaScriptの読み込み待機時間を延長
- ボタンのセレクタを確認
- 手動で同じ操作ができるか確認

## 今後の拡張案

### Phase 2: レポート機能
- 月次の請求サマリーを自動生成
- PDF形式でレポート出力
- メール送信機能

### Phase 3: AI活用
- レッスン内容の自動分析
- 異常検知（単価の誤りなど）
- 最適な請求タイミングの提案

### Phase 4: CI/CD統合
- GitHub Actionsでの定期実行
- Slackへの実行結果通知
- エラー時のアラート

## 参考情報

### 使用技術
- Python 3.11+
- Selenium WebDriver
- Chrome/ChromeDriver
- BeautifulSoup4
- Anthropic Vertex AI

### 関連ドキュメント
- Selenium Python: https://selenium-python.readthedocs.io/
- Terakoya: https://terakoya.sejuku.net/

## 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-11-01 | 1.0 | 初版作成 | - |

## 承認

- [ ] セキュリティレビュー完了
- [ ] コードレビュー完了
- [ ] テスト実施完了
- [ ] 本番実行承認

---

**注意事項:**
- このスクリプトは個人の請求申請を自動化するものです
- 不正な申請や重複申請を防ぐため、必ず内容を確認してください
- パスワード等の認証情報は厳重に管理してください
- サイトの仕様変更により動作しなくなる可能性があります
