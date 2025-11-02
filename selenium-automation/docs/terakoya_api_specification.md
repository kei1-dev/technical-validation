# Samurai Terakoya 請求申請自動化 - API仕様書（リファクタリング版）

## 1. 概要

本ドキュメントは、Terakoya請求申請自動化システムの各クラスとメソッドの詳細な仕様を定義します。

**リファクタリング後の主な変更**:
- TerakoyaClientをSingle Responsibility Principleに従って分割
- Result<T>パターンによる統一的なエラーハンドリング
- WebBrowserインターフェースによる依存性逆転
- Validation層の追加による入力検証の強化
- Circuit Breakerパターンによるレジリエンス向上

## 1.1 新しいクラス構成

### 主要クラス

1. **TerakoyaClient (Facade)** - 統一インターフェース提供
2. **TerakoyaAuthenticator** - 認証とセッション管理
3. **TerakoyaDataRetriever** - データ取得
4. **InvoiceSubmissionService** - 請求処理
5. **DuplicateChecker** - 重複チェック
6. **WebBrowser Interface** - ブラウザ操作の抽象化
7. **Browser** - WebBrowser実装（Circuit Breaker統合）
8. **Validator層** - データ検証
9. **Result<T>** - 統一的な結果型

### アーキテクチャ図

```
TerakoyaClient (Facade)
    ├── TerakoyaAuthenticator
    ├── TerakoyaDataRetriever
    ├── InvoiceSubmissionService
    └── DuplicateChecker
         └── WebBrowser Interface
              └── Browser (Circuit Breaker付き)
```

## 1.2 Result<T>パターン

すべてのメソッドは`Result<T>`型を返すことで、エラーハンドリングを統一します。

```python
from dataclasses import dataclass
from typing import Optional, Generic, TypeVar
from enum import Enum

T = TypeVar('T')

class ResultStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"

@dataclass
class Result(Generic[T]):
    """統一的な結果ラッパー"""
    status: ResultStatus
    value: Optional[T] = None
    error: Optional[Exception] = None
    message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == ResultStatus.SUCCESS

    @classmethod
    def success(cls, value: T, message: str = None) -> 'Result[T]':
        return cls(status=ResultStatus.SUCCESS, value=value, message=message)

    @classmethod
    def failure(cls, message: str, error: Exception = None) -> 'Result[T]':
        return cls(status=ResultStatus.FAILURE, message=message, error=error)

# 使用例
result: Result[bool] = client.login(email, password)
if result.is_success:
    print("ログイン成功")
else:
    logger.error(f"ログイン失敗: {result.message}")
```

## 2. TerakoyaClient クラス

### 2.1 概要

**モジュール**: `src/automation/terakoya.py`

**責務**: Samurai Terakoya固有の操作を提供するクラス

**依存関係**:
- `automation.browser.Browser`
- `automation.scraper.Scraper`
- `utils.logger`
- `utils.config`

### 2.2 コンストラクタ

#### `__init__(browser: Browser)`

Terakoyaクライアントを初期化します。

**引数**:
- `browser` (Browser): Browserインスタンス

**例外**:
- なし

**使用例**:
```python
from automation.browser import Browser
from automation.terakoya import TerakoyaClient

browser = Browser(headless=False)
client = TerakoyaClient(browser)
```

### 2.3 認証関連メソッド

#### `login(email: str, password: str) -> bool`

Samurai Terakoyaにログインします。

**引数**:
- `email` (str): ログインメールアドレス
- `password` (str): パスワード

**戻り値**:
- `bool`: ログイン成功時はTrue、失敗時はFalse

**例外**:
- `TimeoutException`: ページロードまたは要素検索がタイムアウト
- `NoSuchElementException`: ログインフォーム要素が見つからない

**処理フロー**:
1. トップページ (`base_url`) にアクセス
2. JavaScriptレンダリングを待機（3秒）
   - Terakoyaはクライアントサイドレンダリングを使用
3. ヘッダーのログインdiv要素をJavaScriptでクリック
   - XPath: `/html/body/div[1]/header/div/div/div[2]/div[1]`
   - 通常のclickは効かないため、`driver.execute_script("arguments[0].click()", element)`を使用
4. ログインモーダルの表示を待機（2秒）
5. メールアドレス入力フィールドを検索して入力
   - セレクター: `input[type='email'], input[name='email'], #email`
6. パスワード入力フィールドを検索して入力
   - セレクター: `input[type='password'], input[name='password'], #password`
7. ボタン有効化を待機（1秒）
   - ボタンは初期状態で`disabled`、入力後に有効化される
8. ログインボタンをクリック
   - XPath: `//button[contains(text(), 'ログイン') and not(contains(text(), 'Google')) and not(contains(text(), 'Facebook'))]`
   - CSSセレクターの`:contains()`は非対応のため、XPathを使用
9. ページ遷移を待機（`wait_for_page_load()`）
10. エラーメッセージの有無をチェック（オプション）
    - セレクター: `.error, .alert-danger, [role='alert']`

**技術的制約**:
- Seleniumの`:contains()`疑似クラスは非対応のため、XPathで代替
- div要素のクリックにはJavaScriptが必要（通常のclickイベントが伝播しない）
- クライアントサイドレンダリングのため、明示的な待機時間が必要

**使用例**:
```python
success = client.login(
    email="user@example.com",
    password="secure_password"
)
if success:
    print("ログイン成功")
else:
    print("ログイン失敗")
```

#### `check_session_validity() -> bool`

セッションの有効性をチェックします。

**引数**:
- なし

**戻り値**:
- `bool`: セッション有効時はTrue、無効時はFalse

**例外**:
- なし（内部で例外をキャッチ）

**使用例**:
```python
if not client.check_session_validity():
    client.login(email, password)
```

#### `ensure_logged_in() -> bool`

ログイン状態を確保します（必要に応じて再ログイン）。

**引数**:
- なし

**戻り値**:
- `bool`: ログイン状態確保時はTrue

**例外**:
- `SessionExpiredError`: 再ログインに失敗

**使用例**:
```python
try:
    client.ensure_logged_in()
    # 処理続行
except SessionExpiredError:
    print("セッションが回復できませんでした")
```

### 2.4 データ取得メソッド

#### `get_lessons_for_month(year: int, month: int) -> List[Dict]`

指定月のレッスン一覧を取得します。

**引数**:
- `year` (int): 対象年（例: 2025）
- `month` (int): 対象月（1-12）

**戻り値**:
- `List[Dict]`: レッスン情報のリスト

レッスン情報の構造:
```python
{
    "id": str,              # レッスンID
    "date": str,            # レッスン日（YYYY-MM-DD）
    "student_id": str,      # 受講生ID
    "student_name": str,    # 受講生名
    "status": str,          # ステータス
    "duration": int,        # 時間（分）
    "category": str         # カテゴリー
}
```

**例外**:
- `TimeoutException`: ページロードタイムアウト
- `NoSuchElementException`: レッスンテーブルが見つからない

**処理フロー**:
1. 「レッスン→専属レッスン」メニューをクリック
2. JavaScriptで「編集」ボタンを検出（最大100件）
   - `textContent.trim() === '編集'` で完全一致検索（「受講履歴編集」を除外）
3. 各レッスンカードのテキストを取得
4. AI抽出 or 正規表現で情報を抽出:
   - 日付: MM/DD(曜) → YYYY-MM-DD形式
   - 生徒名: 人名のみ（「最終レッ」「キャンセ」等のステータス語を除外）
   - カテゴリ: 専属レッスン/初回レッスン/エキスパートコース
   - 時間: 開始・終了時刻から計算
5. 重複削除: (date + student_name) の組み合わせでユニーク化
6. List[LessonData]形式で返却

**技術詳細**:
- **ボタン選択**: 各レッスンには「編集」と「受講履歴編集」の2つのボタンが存在。完全一致でフィルタリングして重複を回避
- **AI抽出**: 環境変数 `TERAKOYA_USE_AI_EXTRACTION=true` で有効化。バッチサイズは `TERAKOYA_AI_BATCH_SIZE` で設定（デフォルト: 10）
- **フォールバック**: AI抽出失敗時は自動的に正規表現ベースの抽出にフォールバック

**使用例**:
```python
lessons = client.get_lessons_for_month(year=2025, month=10)
print(f"取得したレッスン数: {len(lessons)}")
for lesson in lessons:
    print(f"日付: {lesson['date']}, 受講生: {lesson['student_name']}")
```

#### `get_existing_invoices() -> List[Dict]`

既存の請求申請を取得します（重複防止用）。

**引数**:
- なし

**戻り値**:
- `List[Dict]`: 既存の請求項目リスト

請求項目の構造:
```python
{
    "id": str,              # レッスンID（あれば）
    "date": str,            # レッスン日（YYYY-MM-DD）
    "student_id": str,      # 受講生ID
    "student_name": str,    # 受講生名
    "duration": int,        # 時間（分）
    "unit_price": int       # 単価（円）
}
```

**例外**:
- `TimeoutException`: ページロードタイムアウト

**使用例**:
```python
existing = client.get_existing_invoices()
print(f"既存申請: {len(existing)}件")
```

### 2.5 ナビゲーションメソッド

#### `navigate_to_invoice_page(year: int, month: int)`

請求申請ページへ移動し、対象月を設定します。

**引数**:
- `year` (int): 対象年
- `month` (int): 対象月（1-12）

**戻り値**:
- なし

**例外**:
- `TimeoutException`: ページロードタイムアウト
- `NoSuchElementException`: 月選択ドロップダウンが見つからない

**処理フロー**:
1. 左メニュー「請求申請」をクリック
2. 画面右上「請求申請月」ドロップダウンを探す
3. 対象月（例: 2025/10）を選択
4. ページ更新を待機

**使用例**:
```python
client.navigate_to_invoice_page(year=2025, month=10)
```

### 2.6 請求申請メソッド

#### `add_invoice_item(lesson: Dict, dry_run: bool = False) -> InvoiceResult`

請求項目を1件追加します。

**引数**:
- `lesson` (Dict): レッスン情報
  - `date` (str): レッスン日（YYYY-MM-DD）
  - `student_name` (str): 受講生名
  - `student_id` (str): 受講生ID
  - `lesson_id` (str, optional): レッスンID
  - `category` (str, optional): カテゴリ名（デフォルト: "専属レッスン"）
  - `duration` (int, optional): 時間（デフォルト: 60）
  - `unit_price` (int, optional): 単価（デフォルト: 2300）
- `dry_run` (bool, optional): dry-runモード（デフォルト: False）

**戻り値**:
- `InvoiceResult`: 処理結果

**例外**:
- `TimeoutException`: モーダル操作タイムアウト
- `NoSuchElementException`: フォーム要素が見つからない

**処理フロー**:
1. 「請求項目の追加」ボタンを**JavaScriptでクリック**（通常のclickでは動作しない）
2. モーダルが開くまで待機（1.5秒）
3. モーダル表示を確認
4. **日付入力（React DatePicker対応）**:
   - YYYY-MM-DD形式を YYYY年MM月DD日 形式に変換（例: 2025-10-15 → 2025年10月15日）
   - 日付フィールドをクリック（フォーカス）
   - `set_value_javascript()` でReact対応の値設定
   - TABキーで blur イベント発火
   - フォールバック: JavaScript失敗時は `send_keys()` で手動入力
5. **カテゴリ選択（26種類対応）**:
   - カテゴリ名を数値ID（1-26）にマッピング
   - SELECT要素から対応するIDを選択
   - 1秒待機（フォーム安定化）
6. **受講生選択（カスタムReactドロップダウン対応）**:
   - 標準SELECT要素の存在を先にチェック
   - 標準SELECTが存在する場合: 通常の選択処理
   - カスタムドロップダウンの場合:
     - ドロップダウン表示要素をクリック
     - 検索input（placeholder='検索'）に受講生名を入力
     - ENTERキーで確定
     - 一致するオプションを選択
     - change イベントをディスパッチ
7. **レッスン選択（API非同期読み込み待機）**:
   - 最大12秒待機してオプションがAPI経由で読み込まれるのを待つ
   - 待機条件: `len(Select(element).options) > 1`
   - SELECT要素を再取得（DOMが更新されるため）
   - 日付が一致するレッスンを選択
8. **時間・単価入力**:
   - JavaScript経由で値を設定
9. **dry_runモードの場合**:
   - スクリーンショット保存（`dry_run_form_filled_{timestamp}.png`）
   - モーダルを開いたまま終了（手動確認可能）
   - `InvoiceResult.SUCCESS` を返却（ただし、実際には送信していない）
10. **通常モードの場合**:
   - 「追加」ボタンをクリック
   - モーダルが閉じるまで待機
11. InvoiceResultを返却

**サポートするカテゴリ（26種類）**:

カテゴリ名から数値IDへのマッピング:
- 専属レッスン → 1
- 専属レッスン前後対応 → 2
- 質問対応(担当生徒) → 3
- カリキュラム作成 → 4
- ポートフォリオ添削 → 5
- チャット質問対応 → 6
- 教材作成 → 7
- 技術ブログ執筆 → 8
- 勉強会開催 → 9
- メンタリング → 10
- その他業務 → 11
- 初回レッスン → 12
- 単発レッスン → 15
- エキスパートコース → 16
- 専属レッスンコンサル → 17
- 勉強会登壇 → 18
- イベント運営 → 19
- 面談 → 20
- チーム開発サポート → 21
- 企業研修 → 22
- インターン指導 → 23
- コミュニティ運営 → 24
- 広報活動 → 25
- 公開講座対応 → 26

**技術的詳細**:

1. **React DatePicker**: 標準的な Selenium の `send_keys()` では値が反映されないため、JavaScriptで値を設定し、Reactのchangeイベントを手動でディスパッチします。

2. **カスタムReactドロップダウン**: styled-componentsによる動的クラス名（`sc-eYHxxX`, `sc-eVrRMb`等）を使用したカスタムコンポーネントです。標準SELECTとの互換性のため、両方のパターンをサポートしています。

3. **API非同期読み込み**: レッスンドロップダウンのオプションは受講生選択後にAPI経由で非同期に読み込まれます。明示的な待機が必要です。

4. **dry-runモード**: フォーム入力の検証用。実際には送信せず、モーダルを開いたまま残すため、入力内容を目視確認できます。

**使用例**:
```python
# 通常モード
lesson = {
    "date": "2025-10-15",
    "student_name": "山田太郎",
    "student_id": "student_789",
    "lesson_id": "lesson_12345",
    "category": "専属レッスン",
    "duration": 60,
    "unit_price": 2300
}

result = client.add_invoice_item(lesson, dry_run=False)
if result.status == InvoiceStatus.SUCCESS:
    print("追加成功")
else:
    print(f"追加失敗: {result.error_message}")

# dry-runモード（検証用）
result = client.add_invoice_item(lesson, dry_run=True)
# モーダルが開いたまま残るので、入力内容を確認できる
```

#### `add_invoice_item_with_retry(lesson: Dict, max_retries: int = 3) -> InvoiceResult`

リトライ機能付きで請求項目を追加します。

**引数**:
- `lesson` (Dict): レッスン情報
- `max_retries` (int, optional): 最大リトライ回数（デフォルト: 3）

**戻り値**:
- `InvoiceResult`: 処理結果

**例外**:
- なし（内部で例外をキャッチしてInvoiceResultを返却）

**処理フロー**:
1. add_invoice_item()を実行
2. 成功時: InvoiceResult.SUCCESS を返却
3. TimeoutException時:
   - リトライ回数確認
   - 最大回数未満: 2秒待機後リトライ
   - 最大回数到達: InvoiceResult.FAILED を返却
4. その他の例外: InvoiceResult.FAILED を返却
5. スクリーンショットを保存

**使用例**:
```python
result = client.add_invoice_item_with_retry(
    lesson=lesson,
    max_retries=3
)
print(f"ステータス: {result.status}")
print(f"リトライ回数: {result.retry_count}")
if result.screenshot_path:
    print(f"スクリーンショット: {result.screenshot_path}")
```

**注意**: 請求書の送信機能は実装されていません。すべての請求項目を追加した後、Web画面から手動で送信してください。

### 2.7 ユーティリティメソッド

#### `is_duplicate(lesson: Dict, existing_invoices: List[Dict]) -> bool`

既存申請との重複チェックを行います。

**引数**:
- `lesson` (Dict): チェック対象のレッスン
- `existing_invoices` (List[Dict]): 既存の請求申請リスト

**戻り値**:
- `bool`: 重複している場合True

**例外**:
- なし

**判定ロジック**:
- レッスンIDがある場合: `{date}_{student_id}_{lesson_id}` で判定
- レッスンIDがない場合: `{date}_{student_id}` で判定

**使用例**:
```python
existing = client.get_existing_invoices()
for lesson in lessons:
    if client.is_duplicate(lesson, existing):
        print(f"スキップ: {lesson['date']} - {lesson['student_name']}")
    else:
        # 請求項目追加
        client.add_invoice_item_with_retry(lesson)
```

#### `generate_duplicate_key(lesson: Dict) -> str`

重複チェック用の一意キーを生成します。

**引数**:
- `lesson` (Dict): レッスン情報

**戻り値**:
- `str`: 重複チェック用キー

**例**:
```python
# レッスンIDがある場合
key = client.generate_duplicate_key({
    "date": "2025-10-15",
    "student_id": "student_789",
    "id": "lesson_12345"
})
# 結果: "2025-10-15_student_789_lesson_12345"

# レッスンIDがない場合
key = client.generate_duplicate_key({
    "date": "2025-10-15",
    "student_id": "student_789"
})
# 結果: "2025-10-15_student_789"
```

---

## 3. Browser クラス

### 3.1 概要

**モジュール**: `src/automation/browser.py`

**責務**: Selenium WebDriverのラッパー、基本的なブラウザ操作を提供

**依存関係**:
- `selenium.webdriver`
- `webdriver_manager`

### 3.2 コンストラクタ

#### `__init__(headless: bool = False, download_dir: Optional[str] = None)`

Browserインスタンスを初期化します。

**引数**:
- `headless` (bool, optional): ヘッドレスモード（デフォルト: False）
- `download_dir` (str, optional): ダウンロードディレクトリ

**例外**:
- `WebDriverException`: ChromeDriverの初期化失敗

**使用例**:
```python
# 通常モード
browser = Browser()

# ヘッドレスモード
browser = Browser(headless=True)

# ダウンロードディレクトリ指定
browser = Browser(download_dir="/path/to/downloads")

# コンテキストマネージャ使用
with Browser(headless=False) as browser:
    browser.navigate("https://example.com")
    # 自動的にクローズされる
```

### 3.3 ナビゲーションメソッド

#### `navigate(url: str)`

指定URLへ移動します。

**引数**:
- `url` (str): アクセス先URL

**戻り値**:
- なし

**例外**:
- `WebDriverException`: URL遷移失敗

**使用例**:
```python
browser.navigate("https://terakoya.sejuku.net/")
```

#### `wait_for_page_load(timeout: int = 30)`

ページの完全ロードを待機します。

**引数**:
- `timeout` (int, optional): タイムアウト（秒）（デフォルト: 30）

**戻り値**:
- なし

**例外**:
- `TimeoutException`: ページロードタイムアウト

**使用例**:
```python
browser.navigate("https://example.com")
browser.wait_for_page_load(timeout=60)
```

### 3.4 要素操作メソッド

#### `find_element(by: By, value: str, timeout: int = 10) -> WebElement`

要素を検索します（明示的待機付き）。

**引数**:
- `by` (By): 検索方法（By.ID, By.CSS_SELECTOR, By.XPATH など）
- `value` (str): セレクタ値
- `timeout` (int, optional): タイムアウト（秒）（デフォルト: 10）

**戻り値**:
- `WebElement`: 見つかった要素

**例外**:
- `TimeoutException`: 要素が見つからない
- `NoSuchElementException`: 要素が存在しない

**使用例**:
```python
from selenium.webdriver.common.by import By

# IDで検索
element = browser.find_element(By.ID, "submit-button")

# CSSセレクタで検索
element = browser.find_element(By.CSS_SELECTOR, ".login-form input[type='email']")

# XPathで検索
element = browser.find_element(By.XPATH, "//button[contains(text(), 'ログイン')]")

# タイムアウト指定
element = browser.find_element(By.ID, "slow-element", timeout=30)
```

#### `click(by: By, value: str, timeout: int = 10)`

要素をクリックします。

**引数**:
- `by` (By): 検索方法
- `value` (str): セレクタ値
- `timeout` (int, optional): タイムアウト（秒）（デフォルト: 10）

**戻り値**:
- なし

**例外**:
- `TimeoutException`: 要素が見つからない
- `ElementNotInteractableException`: 要素がクリック不可

**使用例**:
```python
# IDでクリック
browser.click(By.ID, "submit-button")

# CSSセレクタでクリック
browser.click(By.CSS_SELECTOR, ".menu-item.active")

# XPathでクリック
browser.click(By.XPATH, "//button[contains(text(), '送信')]")
```

#### `input_text(by: By, value: str, text: str, timeout: int = 10)`

テキストを入力します。

**引数**:
- `by` (By): 検索方法
- `value` (str): セレクタ値
- `text` (str): 入力テキスト
- `timeout` (int, optional): タイムアウト（秒）（デフォルト: 10）

**戻り値**:
- なし

**例外**:
- `TimeoutException`: 要素が見つからない
- `ElementNotInteractableException`: 要素が入力不可

**使用例**:
```python
# メールアドレス入力
browser.input_text(By.NAME, "email", "user@example.com")

# パスワード入力
browser.input_text(By.CSS_SELECTOR, "input[type='password']", "secure_password")

# 数値入力
browser.input_text(By.NAME, "duration", "60")
```

### 3.5 ユーティリティメソッド

#### `screenshot(filepath: str) -> bool`

スクリーンショットを保存します。

**引数**:
- `filepath` (str): 保存先パス

**戻り値**:
- `bool`: 保存成功時はTrue、失敗時はFalse

**例外**:
- なし（内部で例外をキャッチ）

**使用例**:
```python
# 基本的な使用
browser.screenshot("/path/to/screenshot.png")

# タイムスタンプ付き
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
browser.screenshot(f"output/screenshots/page_{timestamp}.png")
```

#### `get_page_source() -> str`

現在のページのHTMLソースを取得します。

**引数**:
- なし

**戻り値**:
- `str`: HTMLソース

**例外**:
- なし

**使用例**:
```python
html = browser.get_page_source()
scraper = Scraper(html)
text = scraper.get_text()
```

#### `close()`

ブラウザを閉じます。

**引数**:
- なし

**戻り値**:
- なし

**例外**:
- なし

**使用例**:
```python
browser = Browser()
try:
    browser.navigate("https://example.com")
    # 処理
finally:
    browser.close()
```

### 3.6 コンテキストマネージャ

#### `__enter__() -> Browser`

コンテキストマネージャのエントリーポイント。

**使用例**:
```python
with Browser(headless=False) as browser:
    browser.navigate("https://example.com")
    # 自動的にブラウザがクローズされる
```

#### `__exit__(exc_type, exc_val, exc_tb)`

コンテキストマネージャの終了処理。

**使用例**:
```python
with Browser() as browser:
    browser.navigate("https://example.com")
    # 例外が発生してもブラウザは確実にクローズされる
```

---

## 4. Scraper クラス

### 4.1 概要

**モジュール**: `src/automation/scraper.py`

**責務**: HTML解析、データ抽出

**依存関係**:
- `beautifulsoup4`
- `lxml`
- `pandas`

### 4.2 コンストラクタ

#### `__init__(html: str)`

Scraperインスタンスを初期化します。

**引数**:
- `html` (str): 解析するHTML文字列

**例外**:
- なし

**使用例**:
```python
html = browser.get_page_source()
scraper = Scraper(html)
```

### 4.3 データ抽出メソッド

#### `get_text(selector: str = None) -> str`

テキストコンテンツを抽出します。

**引数**:
- `selector` (str, optional): CSSセレクタ（Noneの場合は全テキスト）

**戻り値**:
- `str`: 抽出されたテキスト

**例外**:
- なし（要素が見つからない場合は空文字列）

**使用例**:
```python
# ページ全体のテキスト
text = scraper.get_text()

# 特定要素のテキスト
title = scraper.get_text(".page-title")
content = scraper.get_text("#main-content")
```

#### `extract_table(selector: str = "table") -> Optional[pd.DataFrame]`

表データをDataFrameとして抽出します。

**引数**:
- `selector` (str, optional): テーブルのCSSセレクタ（デフォルト: "table"）

**戻り値**:
- `Optional[pd.DataFrame]`: 抽出されたデータ（見つからない場合はNone）

**例外**:
- なし

**使用例**:
```python
# デフォルトテーブル抽出
df = scraper.extract_table()

# 特定テーブル抽出
lessons_df = scraper.extract_table("table.lesson-list")

if df is not None:
    print(df.head())
    df.to_csv("output/lessons.csv", index=False)
```

#### `extract_structured_data(item_selector: str, field_selectors: Dict[str, str]) -> List[Dict[str, Any]]`

構造化データを抽出します。

**引数**:
- `item_selector` (str): アイテムのCSSセレクタ
- `field_selectors` (Dict[str, str]): フィールド名とセレクタのマッピング

**戻り値**:
- `List[Dict[str, Any]]`: 抽出されたデータのリスト

**例外**:
- なし

**使用例**:
```python
# レッスン情報を抽出
lessons = scraper.extract_structured_data(
    item_selector=".lesson-item",
    field_selectors={
        "date": ".lesson-date",
        "student_name": ".student-name",
        "status": ".lesson-status"
    }
)

for lesson in lessons:
    print(f"{lesson['date']}: {lesson['student_name']}")
```

---

## 5. Utility クラス群

### 5.1 Logger

**モジュール**: `src/utils/logger.py`

#### `setup_logger(name: str = "selenium_automation", level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger`

ロガーを設定します。

**引数**:
- `name` (str, optional): ロガー名（デフォルト: "selenium_automation"）
- `level` (int, optional): ログレベル（デフォルト: logging.INFO）
- `log_file` (str, optional): ログファイルパス

**戻り値**:
- `logging.Logger`: 設定済みロガー

**使用例**:
```python
from utils.logger import setup_logger
import logging

# 基本的な使用
logger = setup_logger()

# カスタム設定
logger = setup_logger(
    name="terakoya_automation",
    level=logging.DEBUG,
    log_file="output/terakoya_logs/automation.log"
)

# ログ出力
logger.info("処理開始")
logger.debug("デバッグ情報")
logger.warning("警告メッセージ")
logger.error("エラー発生", exc_info=True)
```

### 5.2 Config

**モジュール**: `src/utils/config.py`

#### `Config クラス`

環境変数を管理するクラス。

**プロパティ**:
- `terakoya_email: str` - Terakoyaログインメール
- `terakoya_password: str` - Terakoyaパスワード
- `terakoya_url: str` - TerakoyaサイトURL
- `lesson_duration: int` - レッスン時間（分）
- `lesson_unit_price: int` - 単価（円）
- `output_dir: Path` - 出力ディレクトリ
- `log_level: str` - ログレベル

**メソッド**:
- `validate() -> bool` - 設定値の検証

**使用例**:
```python
from utils.config import config

# 環境変数から読み込み（自動）
email = config.terakoya_email
password = config.terakoya_password

# 設定の検証
if not config.validate():
    print("設定が不正です")
    sys.exit(1)

# 出力ディレクトリ
output_path = config.output_dir / "screenshots"
output_path.mkdir(parents=True, exist_ok=True)
```

### 5.3 FileUtils

**モジュール**: `src/utils/file_utils.py`

#### `save_json(data: Dict, filepath: Path) -> bool`

データをJSON形式で保存します。

**引数**:
- `data` (Dict): 保存するデータ
- `filepath` (Path): 保存先パス

**戻り値**:
- `bool`: 保存成功時はTrue

**使用例**:
```python
from utils.file_utils import save_json
from pathlib import Path

data = {
    "lessons": lessons,
    "timestamp": "2025-10-01T10:00:00"
}
save_json(data, Path("output/lessons.json"))
```

#### `load_json(filepath: Path) -> Optional[Dict]`

JSONファイルを読み込みます。

**引数**:
- `filepath` (Path): 読み込むファイルパス

**戻り値**:
- `Optional[Dict]`: 読み込んだデータ（失敗時はNone）

**使用例**:
```python
from utils.file_utils import load_json

data = load_json(Path("output/lessons.json"))
if data:
    print(f"レッスン数: {len(data['lessons'])}")
```

#### `save_csv(df: pd.DataFrame, filepath: Path) -> bool`

DataFrameをCSV形式で保存します。

**引数**:
- `df` (pd.DataFrame): 保存するDataFrame
- `filepath` (Path): 保存先パス

**戻り値**:
- `bool`: 保存成功時はTrue

**使用例**:
```python
from utils.file_utils import save_csv

save_csv(lessons_df, Path("output/lessons.csv"))
```

#### `generate_filename(prefix: str, extension: str) -> str`

タイムスタンプ付きファイル名を生成します。

**引数**:
- `prefix` (str): ファイル名プレフィックス
- `extension` (str): 拡張子（ドットなし）

**戻り値**:
- `str`: 生成されたファイル名

**使用例**:
```python
from utils.file_utils import generate_filename

filename = generate_filename("screenshot", "png")
# 結果例: "screenshot_20251001_103045.png"

filepath = config.output_dir / "screenshots" / filename
browser.screenshot(str(filepath))
```

---

## 6. データクラス

### 6.1 InvoiceStatus

**モジュール**: `src/automation/terakoya.py`

```python
from enum import Enum

class InvoiceStatus(Enum):
    SUCCESS = "success"    # 追加成功
    FAILED = "failed"      # 追加失敗
    SKIPPED = "skipped"    # スキップ（重複）
    PENDING = "pending"    # 保留中
```

### 6.2 InvoiceResult

**モジュール**: `src/automation/terakoya.py`

```python
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class InvoiceResult:
    lesson: Dict                        # レッスン情報
    status: InvoiceStatus               # 処理状態
    error_message: Optional[str] = None # エラーメッセージ
    retry_count: int = 0                # リトライ回数
    screenshot_path: Optional[str] = None # スクリーンショットパス

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

**使用例**:
```python
result = InvoiceResult(
    lesson=lesson,
    status=InvoiceStatus.SUCCESS,
    retry_count=1
)

# 辞書形式で出力
result_dict = result.to_dict()
print(result_dict)
```

---

## 7. 例外クラス

### 7.1 SessionExpiredError

**モジュール**: `src/automation/terakoya.py`

```python
class SessionExpiredError(Exception):
    """セッション期限切れエラー"""
    pass
```

**使用例**:
```python
try:
    client.ensure_logged_in()
except SessionExpiredError:
    logger.error("セッションが回復できませんでした")
    sys.exit(1)
```

---

## 7. AIExtractor クラス

### 7.1 概要

**モジュール**: `src/utils/ai_extractor.py`

**責務**: Claude APIを使用したレッスンデータのAI抽出

**依存関係**:
- `anthropic` (AnthropicVertex)

**環境変数**:
- `ANTHROPIC_VERTEX_PROJECT_ID`: GCP プロジェクトID（必須）
- `CLOUD_ML_REGION`: リージョン（デフォルト: "global"）
- `ANTHROPIC_MODEL`: モデル名（デフォルト: "claude-sonnet-4-5@20250929"）
- `TERAKOYA_USE_AI_EXTRACTION`: AI抽出の有効化（"true" / "false"、デフォルト: "false"）
- `TERAKOYA_AI_BATCH_SIZE`: バッチサイズ（デフォルト: 10）

### 7.2 コンストラクタ

#### `__init__()`

AIExtractorインスタンスを初期化します。

**引数**:
- なし（環境変数から設定を取得）

**例外**:
- `ValueError`: `ANTHROPIC_VERTEX_PROJECT_ID` が設定されていない場合

**使用例**:
```python
# 環境変数を設定
os.environ["ANTHROPIC_VERTEX_PROJECT_ID"] = "your-project-id"
os.environ["TERAKOYA_USE_AI_EXTRACTION"] = "true"

# AIExtractorを初期化
extractor = AIExtractor()
```

### 7.3 メソッド

#### `extract_lessons_batch(card_texts: List[str], target_year: int, batch_size: int = 10) -> List[Optional[LessonData]]`

複数のカードテキストから一括でレッスンデータを抽出します。

**引数**:
- `card_texts` (List[str]): レッスンカードのテキストリスト
- `target_year` (int): 対象年（日付コンテキスト用、例: 2025）
- `batch_size` (int, optional): 1回のAPI呼び出しで処理するカード数（デフォルト: 10）

**戻り値**:
- `List[Optional[LessonData]]`: 抽出されたレッスンデータのリスト。抽出失敗時は `None`

**処理フロー**:
1. カードテキストを `batch_size` 単位で分割
2. 各バッチをClaude APIに送信
3. JSON形式のレスポンスをパース
4. `LessonData` 形式に変換
5. 生徒名の妥当性チェック（「最終レッ」「キャンセ」等を除外）

**使用例**:
```python
extractor = AIExtractor()

card_texts = [
    "11/01(土)20:00~21:00【第2回】Github林晃司マンツー編集受講履歴登録",
    "11/02(日)14:00~15:00初回レッスン山田太郎専属レッスン編集",
    # ... more cards
]

lessons = extractor.extract_lessons_batch(
    card_texts=card_texts,
    target_year=2025,
    batch_size=10
)

for lesson in lessons:
    if lesson:
        print(f"{lesson['date']}: {lesson['student_name']}")
```

#### `extract_lesson(card_text: str, target_year: int) -> Optional[LessonData]`

単一のカードテキストからレッスンデータを抽出します。

**引数**:
- `card_text` (str): レッスンカードのテキスト
- `target_year` (int): 対象年（日付コンテキスト用）

**戻り値**:
- `Optional[LessonData]`: 抽出されたレッスンデータ。抽出失敗時は `None`

**使用例**:
```python
extractor = AIExtractor()

card_text = "11/01(土)20:00~21:00【第2回】Github林晃司マンツー編集"
lesson = extractor.extract_lesson(card_text, 2025)

if lesson:
    print(f"生徒名: {lesson['student_name']}")
    print(f"日付: {lesson['date']}")
    print(f"時間: {lesson['duration']}分")
```

### 7.4 AI抽出の利点

1. **高精度な人名抽出**: 正規表現では困難な「最終レッ」「キャンセ」等のステータス語を生徒名と誤認しない
2. **柔軟な日付解析**: MM/DD(曜) 形式を YYYY-MM-DD 形式に正確に変換
3. **文脈理解**: レッスンカテゴリを文脈から判定
4. **DOM構造の変更に強い**: テキストベース抽出のため、HTML構造変更の影響を受けにくい
5. **バッチ処理**: 複数カードを一括処理し、API呼び出しコストを最小化

### 7.5 フォールバック

AI抽出が失敗した場合、自動的に正規表現ベースの抽出にフォールバックします:

```python
# TerakoyaClient内の処理
if self.use_ai_extraction and self.ai_extractor:
    try:
        # AI抽出を試行
        lessons = self.ai_extractor.extract_lessons_batch(card_texts, year)
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        # 正規表現ベースの抽出にフォールバック
        self.use_ai_extraction = False
```

---

## 8. メインスクリプト

### 8.1 コマンドライン引数

**スクリプト**: `examples/terakoya_invoice.py`

```bash
pipenv run python examples/terakoya_invoice.py [OPTIONS]
```

**オプション**:
- `--month YYYY-MM`: 対象月（必須）
- `--dry-run`: ドライラン（送信しない）
- `--headless`: ヘッドレスモード

**使用例**:
```bash
# 通常実行
pipenv run python examples/terakoya_invoice.py --month 2025-10

# ドライラン
pipenv run python examples/terakoya_invoice.py --month 2025-10 --dry-run

# ヘッドレス
pipenv run python examples/terakoya_invoice.py --month 2025-10 --headless
```

---

## 9. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-11-01 | 1.0 | 初版作成 | - |

---

## 10. 参考資料

- [システム設計書](./terakoya_system_design.md)
- [データ構造設計書](./terakoya_data_structure.md)
- [セキュリティ設計書](./terakoya_security_design.md)
- [Selenium Python API](https://selenium-python.readthedocs.io/api.html)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
