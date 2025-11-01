# Samurai Terakoya 請求申請自動化 - システム設計書

## 1. 概要

### 1.1 目的
Samurai Terakoyaの月次請求申請作業を自動化するシステムの設計仕様を定義します。
Seleniumによる画面操作とVertex AI（Claude）による知的処理を組み合わせ、安全かつ効率的な自動化を実現します。

### 1.2 対象範囲
- 専属レッスンの請求申請自動化
- 重複申請の防止
- エラーハンドリングとリトライ機能
- ログとトレーサビリティの確保

### 1.3 非対象
- レッスン実施記録の自動化
- 受講生管理機能
- レポート生成（Phase 2以降）

## 2. システムアーキテクチャ

### 2.1 全体構成

```
┌─────────────────────────────────────────────────────────┐
│                   Main Script Layer                      │
│            (examples/terakoya_invoice.py)                │
│  - コマンドライン引数処理                                │
│  - メインフロー制御                                      │
│  - ユーザー確認プロンプト                                │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│              Automation Layer                            │
│         (src/automation/terakoya.py)                     │
│  - TerakoyaClient: サイト固有の操作                      │
│  - ログイン、データ取得、請求申請                        │
│  - 重複チェック、セッション管理                          │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│              Core Layer                                  │
│         (src/automation/browser.py)                      │
│         (src/automation/scraper.py)                      │
│  - Browser: Selenium WebDriverラッパー                   │
│  - Scraper: HTML解析とデータ抽出                         │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│              Utility Layer                               │
│  - Logger: ロギング (src/utils/logger.py)               │
│  - Config: 設定管理 (src/utils/config.py)               │
│  - FileUtils: ファイル操作 (src/utils/file_utils.py)    │
└─────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                        │
│  - Selenium WebDriver                                    │
│  - Chrome/ChromeDriver                                   │
│  - Vertex AI (Claude)                                    │
│  - File System (logs, screenshots, data)                │
└─────────────────────────────────────────────────────────┘
```

### 2.2 コンポーネント関係図（リファクタリング後）

```
┌──────────────────────────────────────────────────────┐
│  Main Script (examples/terakoya_invoice.py)          │
└──────────────┬───────────────────────────────────────┘
               │ uses
               ▼
┌──────────────────────────────────────────────────────┐
│  TerakoyaClient (Facade)                             │
│  - 統一インターフェース提供                          │
└──────┬───────────────────────────────────────────────┘
       │ delegates to
       ├──────────────────────────────────────────┐
       │                                          │
       ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────┐
│ TerakoyaAuthenticator│              │ TerakoyaDataRetriever│
│ - login()            │              │ - get_lessons()      │
│ - check_session()    │              │ - get_invoices()     │
│ - ensure_logged_in() │              │                      │
└──────┬───────────────┘              └──────┬───────────────┘
       │ uses                                 │ uses
       │                                      │
       ├──────────────────────────────────────┤
       │                                      │
       ▼                                      ▼
┌──────────────────────────────────────────────────────┐
│  WebBrowser Interface (abstraction)                  │
└──────────────┬───────────────────────────────────────┘
               │ implements
               ▼
┌──────────────────────────────────────────────────────┐
│  Browser (Selenium wrapper)                          │
└──────────────┬───────────────────────────────────────┘
               │ uses
               ▼
┌──────────────────────────────────────────────────────┐
│  Selenium WebDriver + Circuit Breaker                │
└──────────────────────────────────────────────────────┘

       ┌──────────────────────┐      ┌──────────────────────┐
       │InvoiceSubmissionSvc  │      │  DuplicateChecker    │
       │ - navigate_to_page() │      │ - is_duplicate()     │
       │ - add_item()         │      │ - generate_key()     │
       │ - submit()           │      │                      │
       └──────┬───────────────┘      └──────────────────────┘
              │ uses
              ▼
       ┌──────────────────────┐
       │  Validator Layer     │
       │ - LessonValidator    │
       │ - InvoiceValidator   │
       └──────┬───────────────┘
              │ uses
              ▼
       ┌──────────────────────────────────────┐
       │  Utility Classes                      │
       │  - Logger (with masking)              │
       │  - Config (with validation)           │
       │  - FileUtils                          │
       │  - Result<T> (error handling)         │
       │  - DI Container                       │
       └───────────────────────────────────────┘
```

## 3. クラス設計（リファクタリング後）

### 3.0 共通型定義

#### Result<T> パターン（統一エラーハンドリング）

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
```

**責務**: すべての操作の結果を統一的に表現

**利点**:
- 例外とboolの混在を排除
- エラー情報の一貫した伝播
- Railway-oriented programming

### 3.1 WebBrowser インターフェース（抽象化）

```python
from abc import ABC, abstractmethod
from selenium.webdriver.common.by import By

class WebBrowser(ABC):
    """ブラウザ操作の抽象インターフェース"""

    @abstractmethod
    def navigate(self, url: str) -> Result[None]: ...

    @abstractmethod
    def find_element(self, by: By, value: str, timeout: int = 10) -> Result[WebElement]: ...

    @abstractmethod
    def click(self, by: By, value: str, timeout: int = 10) -> Result[None]: ...

    @abstractmethod
    def input_text(self, by: By, value: str, text: str, timeout: int = 10) -> Result[None]: ...

    @abstractmethod
    def screenshot(self, filepath: str) -> Result[bool]: ...

    @abstractmethod
    def close(self): ...
```

**責務**: ブラウザ操作の抽象インターフェース定義

**設計パターン**: Interface Segregation Principle（ISP）に準拠

### 3.2 Browser クラス（WebBrowser実装）

**責務**: Chrome WebDriverのラッパー、Circuit Breaker統合

**主要メソッド**:
- `__init__(headless: bool, download_dir: Optional[str])`: 初期化
- `navigate(url: str) -> Result[None]`: URL遷移
- `find_element(by: By, value: str, timeout: int) -> Result[WebElement]`: 要素検索
- `click(by: By, value: str, timeout: int) -> Result[None]`: クリック操作
- `input_text(by: By, value: str, text: str, timeout: int) -> Result[None]`: テキスト入力
- `screenshot(filepath: str) -> Result[bool]`: スクリーンショット保存
- `close()`: ブラウザクローズ

**設計パターン**:
- Context Manager（自動リソース管理）
- Facade パターン（Selenium API簡素化）
- Dependency Inversion Principle（DIP）

**新機能**: Circuit Breaker統合によるフォールトトレランス向上

### 3.3 TerakoyaAuthenticator クラス（認証専門）

**責務**: 認証とセッション管理のみを担当

**主要メソッド**:
```python
class TerakoyaAuthenticator:
    def __init__(self, browser: WebBrowser, logger: Logger):
        self.browser = browser
        self.logger = logger

    def login(self, email: str, password: str) -> Result[bool]:
        """ログイン処理"""

    def check_session_validity(self) -> Result[bool]:
        """セッション有効性チェック"""

    def ensure_logged_in(self, email: str, password: str) -> Result[bool]:
        """ログイン状態確保（必要時再ログイン）"""
```

**設計パターン**: Single Responsibility Principle（SRP）

### 3.4 TerakoyaDataRetriever クラス（データ取得専門）

**責務**: レッスンデータと既存請求データの取得のみ

**主要メソッド**:
```python
class TerakoyaDataRetriever:
    def __init__(
        self,
        browser: WebBrowser,
        authenticator: TerakoyaAuthenticator,
        scraper_factory: Callable[[str], Scraper]
    ):
        self.browser = browser
        self.authenticator = authenticator
        self.scraper_factory = scraper_factory

    def get_lessons_for_month(self, year: int, month: int) -> Result[List[LessonData]]:
        """指定月のレッスン一覧取得"""

    def get_existing_invoices(self) -> Result[List[InvoiceItemData]]:
        """既存請求申請取得"""
```

**設計パターン**:
- SRP（データ取得のみ）
- Factory Pattern（Scraper生成）

### 3.5 InvoiceSubmissionService クラス（請求処理専門）

**責務**: 請求項目の追加と送信のみ

**主要メソッド**:
```python
class InvoiceSubmissionService:
    def __init__(
        self,
        browser: WebBrowser,
        authenticator: TerakoyaAuthenticator,
        validator: InvoiceItemValidator
    ):
        self.browser = browser
        self.authenticator = authenticator
        self.validator = validator

    def navigate_to_invoice_page(self, year: int, month: int) -> Result[None]:
        """請求申請ページへ移動"""

    def add_invoice_item(self, lesson: LessonData) -> Result[InvoiceResult]:
        """請求項目追加（バリデーション付き）"""

    def add_invoice_item_with_retry(
        self,
        lesson: LessonData,
        max_retries: int = 3
    ) -> Result[InvoiceResult]:
        """リトライ機能付き請求項目追加"""

    def submit_invoice(self) -> Result[bool]:
        """請求申請送信"""
```

**設計パターン**:
- SRP（請求処理のみ）
- Template Method（リトライロジック）
- Strategy（バリデーション戦略）

### 3.6 DuplicateChecker クラス（重複チェック専門）

**責務**: 重複検出ロジックのみ

**主要メソッド**:
```python
class DuplicateChecker:
    def generate_duplicate_key(self, lesson: LessonData) -> str:
        """重複チェック用キー生成"""

    def is_duplicate(
        self,
        lesson: LessonData,
        existing: List[InvoiceItemData]
    ) -> bool:
        """重複判定"""

    def filter_duplicates(
        self,
        lessons: List[LessonData],
        existing: List[InvoiceItemData]
    ) -> Tuple[List[LessonData], List[LessonData]]:
        """重複をフィルタリング（新規、重複のタプルを返す）"""
```

**設計パターン**:
- SRP（重複チェックのみ）
- Strategy Pattern（異なる重複検出戦略を切り替え可能）

### 3.7 TerakoyaClient クラス（Facade）

**責務**: 後方互換性のための統一インターフェース提供

**主要メソッド**:
```python
class TerakoyaClient:
    """Facade providing unified interface to all Terakoya operations"""

    def __init__(self, browser: WebBrowser, container: DIContainer = None):
        # 依存性注入または自動生成
        if container:
            self.authenticator = container.resolve(TerakoyaAuthenticator)
            self.data_retriever = container.resolve(TerakoyaDataRetriever)
            self.invoice_service = container.resolve(InvoiceSubmissionService)
            self.duplicate_checker = container.resolve(DuplicateChecker)
        else:
            # デフォルト実装
            logger = setup_logger()
            self.authenticator = TerakoyaAuthenticator(browser, logger)
            self.data_retriever = TerakoyaDataRetriever(
                browser,
                self.authenticator,
                Scraper
            )
            self.invoice_service = InvoiceSubmissionService(
                browser,
                self.authenticator,
                InvoiceItemValidator()
            )
            self.duplicate_checker = DuplicateChecker()

    # Delegate methods
    def login(self, email: str, password: str) -> Result[bool]:
        return self.authenticator.login(email, password)

    def get_lessons_for_month(self, year: int, month: int) -> Result[List[LessonData]]:
        return self.data_retriever.get_lessons_for_month(year, month)

    # ... その他のデリゲートメソッド
```

**設計パターン**:
- Facade Pattern（複雑なサブシステムの統一インターフェース）
- Dependency Injection（柔軟な依存関係管理）

### 3.8 Scraper クラス

**責務**: HTML解析、データ抽出

**主要メソッド**:
- `__init__(html: str)`: 初期化（BeautifulSoup）
- `get_text(selector: str) -> str`: テキスト抽出
- `extract_table(selector: str) -> Optional[pd.DataFrame]`: 表データ抽出
- `extract_structured_data(item_selector: str, field_selectors: Dict[str, str]) -> List[Dict]`: 構造化データ抽出

**設計パターン**:
- Builder パターン（データ構造の構築）

### 3.9 Validation層（新規追加）

#### 3.9.1 Validatorインターフェース

```python
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """バリデーション結果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None

class Validator(ABC):
    """バリデーターの基底クラス"""
    @abstractmethod
    def validate(self, data: Any) -> ValidationResult: ...
```

#### 3.9.2 LessonValidator

```python
class LessonValidator(Validator):
    """レッスンデータのバリデーター"""

    def validate(self, lesson: Dict) -> ValidationResult:
        errors = []

        # 必須フィールドチェック
        required = ["id", "date", "student_id", "student_name", "status", "duration"]
        for field in required:
            if field not in lesson:
                errors.append(f"Missing required field: {field}")

        # 日付フォーマットチェック
        if "date" in lesson:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', lesson["date"]):
                errors.append(f"Invalid date format: {lesson['date']}")

        # Duration バリデーション
        if "duration" in lesson and lesson["duration"] <= 0:
            errors.append(f"Duration must be positive: {lesson['duration']}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

#### 3.9.3 InvoiceItemValidator

```python
class InvoiceItemValidator(Validator):
    """請求項目のバリデーター"""

    def validate(self, item: Dict) -> ValidationResult:
        errors = []
        warnings = []

        # 必須フィールド
        if not item.get("student_name"):
            errors.append("Student name is required")

        if not item.get("date"):
            errors.append("Date is required")

        # ビジネスルール
        if item.get("unit_price", 0) > 5000:
            warnings.append(f"Unit price seems high: {item['unit_price']}")

        if item.get("duration", 0) > 120:
            warnings.append(f"Duration seems long: {item['duration']} minutes")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

**責務**: データ整合性の検証

**設計パターン**: Strategy Pattern（異なる検証戦略）

### 3.10 AIExtractor クラス（新規追加）

**責務**: Claude APIを使用したレッスンデータの抽出

```python
from anthropic import AnthropicVertex
from typing import List, Optional, Dict, Any

class AIExtractor:
    """AI-powered extractor for lesson data using Claude API via Vertex AI"""

    def __init__(self):
        """Initialize AIExtractor with Vertex AI client

        Environment variables required:
        - ANTHROPIC_VERTEX_PROJECT_ID: GCP project ID
        - CLOUD_ML_REGION: Region (default: "global")
        - ANTHROPIC_MODEL: Model name (default: "claude-sonnet-4-5@20250929")
        """
        self.project_id = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID")
        self.region = os.getenv("CLOUD_ML_REGION", "global")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5@20250929")

        self.client = AnthropicVertex(
            project_id=self.project_id,
            region=self.region
        )

    def extract_lessons_batch(
        self,
        card_texts: List[str],
        target_year: int,
        batch_size: int = 10
    ) -> List[Optional[LessonData]]:
        """Extract lesson data from multiple card texts in batches

        Args:
            card_texts: List of lesson card texts
            target_year: Year for date context (e.g., 2025)
            batch_size: Number of cards to process in one API call

        Returns:
            List of extracted LessonData (or None if extraction failed)
        """

    def extract_lesson(
        self,
        card_text: str,
        target_year: int
    ) -> Optional[LessonData]:
        """Extract lesson data from a single card text

        Args:
            card_text: Lesson card text
            target_year: Year for date context

        Returns:
            LessonData or None if extraction failed
        """
```

**主要機能**:
1. **バッチ処理**: 複数のカードテキストをまとめて処理し、API呼び出しを最小化
2. **人名抽出**: 「最終レッ」「キャンセ」などのステータス語を生徒名と誤認しない
3. **日付解析**: MM/DD(曜) 形式から YYYY-MM-DD 形式への変換
4. **時間計算**: 開始・終了時刻から時間（分）を自動計算
5. **カテゴリ判定**: レッスン種別を正確に分類

**設計パターン**:
- Adapter Pattern（Claude API の統合）
- Batch Processing（効率的なAPI利用）

**利点**:
- 正規表現では困難な複雑なパターンに対応
- DOM構造の変更に強い（テキストベース抽出）
- 人名とステータス語の高精度な区別

### 3.11 Circuit Breaker（新規追加）

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"          # 正常動作
    OPEN = "open"              # 障害検出、リクエストブロック
    HALF_OPEN = "half_open"    # 回復テスト中

class CircuitBreaker:
    """カスケード障害を防ぐサーキットブレーカー"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: timedelta = timedelta(seconds=60),
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """サーキットブレーカー保護付きで関数実行"""

        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: Entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """成功時のリセット"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker: Back to CLOSED state")

    def _on_failure(self):
        """失敗時の処理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker: OPEN after {self.failure_count} failures"
            )
```

**責務**: 外部サービス障害時のフォールトトレランス

**使用箇所**: Browser クラス内でSelenium操作を保護

**設計パターン**: Circuit Breaker Pattern

### 3.11 DI Container（新規追加）

```python
from typing import Dict, Type, Callable, Any

class DIContainer:
    """シンプルな依存性注入コンテナ"""

    def __init__(self):
        self._services: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}

    def register(
        self,
        interface: Type,
        implementation: Callable,
        singleton: bool = False
    ):
        """サービスを登録"""
        self._services[interface] = implementation
        if singleton:
            self._singletons[interface] = None

    def resolve(self, interface: Type) -> Any:
        """サービスを解決"""
        if interface in self._singletons:
            if self._singletons[interface] is None:
                self._singletons[interface] = self._services[interface]()
            return self._singletons[interface]

        if interface in self._services:
            return self._services[interface]()

        raise ValueError(f"Service not registered: {interface}")

def configure_services(container: DIContainer, config: Config):
    """全アプリケーションサービスを設定"""

    # シングルトン登録
    container.register(Config, lambda: config, singleton=True)
    container.register(
        logging.Logger,
        lambda: setup_logger("terakoya", config.log_level),
        singleton=True
    )

    # ファクトリー登録
    container.register(Browser, lambda: Browser(headless=config.browser_headless))

    # 依存関係を持つサービス
    def create_authenticator():
        browser = container.resolve(Browser)
        logger = container.resolve(logging.Logger)
        return TerakoyaAuthenticator(browser, logger)

    container.register(TerakoyaAuthenticator, create_authenticator)

    # ... 他のサービス登録
```

**責務**: 依存関係の管理と注入

**利点**:
- 疎結合
- テスタビリティ向上
- 設定の一元管理

**設計パターン**: Dependency Injection, Service Locator

### 3.4 Utility クラス群

#### Logger (src/utils/logger.py)
```python
def setup_logger(
    name: str = "selenium_automation",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger
```

**責務**: ログ設定、ファイル出力、ローテーション

#### Config (src/utils/config.py)
```python
class Config:
    def __init__(self)
    def validate(self) -> bool

    # Properties
    @property
    def terakoya_email(self) -> str
    @property
    def terakoya_password(self) -> str
    @property
    def output_dir(self) -> Path
```

**責務**: 環境変数管理、設定の検証

#### FileUtils (src/utils/file_utils.py)
```python
def save_json(data: Dict, filepath: Path) -> bool
def load_json(filepath: Path) -> Optional[Dict]
def save_csv(df: pd.DataFrame, filepath: Path) -> bool
def generate_filename(prefix: str, extension: str) -> str
```

**責務**: ファイル入出力、パス生成

## 4. ディレクトリ構成

```
selenium-automation/
├── plans/
│   └── terakoya_invoice_automation.md    # 実装計画書
│
├── docs/                                   # 設計ドキュメント
│   ├── terakoya_system_design.md          # このファイル（リファクタリング後）
│   ├── terakoya_api_specification.md      # API仕様書
│   ├── terakoya_data_structure.md         # データ構造設計書
│   └── terakoya_security_design.md        # セキュリティ設計書
│
├── src/                                    # ソースコード
│   ├── automation/                         # 自動化モジュール
│   │   ├── __init__.py
│   │   ├── interfaces.py                   # WebBrowserインターフェース
│   │   ├── browser.py                      # Browser実装（Circuit Breaker統合）
│   │   ├── scraper.py                      # Scraperクラス
│   │   └── terakoya/                       # Terakoya固有モジュール（リファクタリング）
│   │       ├── __init__.py
│   │       ├── client.py                   # TerakoyaClient (Facade)
│   │       ├── authenticator.py            # TerakoyaAuthenticator
│   │       ├── data_retriever.py           # TerakoyaDataRetriever
│   │       ├── invoice_service.py          # InvoiceSubmissionService
│   │       └── duplicate_checker.py        # DuplicateChecker
│   │
│   ├── validation/                         # バリデーション層（新規）
│   │   ├── __init__.py
│   │   ├── validators.py                   # Validatorインターフェース
│   │   ├── lesson_validator.py             # LessonValidator
│   │   └── invoice_validator.py            # InvoiceItemValidator
│   │
│   ├── models/                             # データモデル（新規）
│   │   ├── __init__.py
│   │   ├── result.py                       # Result<T>パターン
│   │   ├── lesson.py                       # LessonData (TypedDict)
│   │   ├── invoice.py                      # InvoiceItemData, InvoiceResult
│   │   └── schema_version.py               # スキーマバージョニング
│   │
│   ├── resilience/                         # レジリエンスパターン（新規）
│   │   ├── __init__.py
│   │   ├── circuit_breaker.py              # CircuitBreaker実装
│   │   └── rate_limiter.py                 # RateLimiter実装
│   │
│   └── utils/                              # ユーティリティ
│       ├── __init__.py
│       ├── logger.py                       # ロギング設定（マスキング付き）
│       ├── config.py                       # 設定管理（バリデーション付き）
│       ├── file_utils.py                   # ファイル操作
│       ├── di_container.py                 # DIコンテナ（新規）
│       ├── encryption.py                   # 暗号化ユーティリティ（新規）
│       └── sanitization.py                 # 入力サニタイズ（新規）
│
├── examples/                               # サンプルスクリプト
│   └── terakoya_invoice.py                 # メインスクリプト（DI使用）
│
├── tests/                                  # テストコード
│   ├── unit/                               # ユニットテスト
│   │   ├── test_browser.py
│   │   ├── test_authenticator.py
│   │   ├── test_data_retriever.py
│   │   ├── test_invoice_service.py
│   │   ├── test_duplicate_checker.py
│   │   ├── test_validators.py
│   │   └── test_circuit_breaker.py
│   │
│   ├── integration/                        # 統合テスト
│   │   ├── test_terakoya_client.py
│   │   └── test_full_workflow.py
│   │
│   └── fixtures/                           # テストデータ
│       ├── mock_html/
│       └── sample_data.json
│
├── output/                                 # 実行結果（.gitignore）
│   ├── terakoya_logs/                      # ログファイル
│   ├── terakoya_screenshots/               # スクリーンショット
│   ├── terakoya_data/                      # データファイル
│   └── metrics/                            # メトリクスデータ（新規）
│
├── .env                                    # 環境変数（.gitignore）
├── .env.template                           # 環境変数テンプレート
├── .gitignore
├── Pipfile                                 # Python依存関係
├── Pipfile.lock
└── README.md
```

## 5. 処理フロー

### 5.1 メインフロー

```
[開始]
  │
  ├─ 1. 引数解析（対象月、ドライラン、ヘッドレス）
  │
  ├─ 2. 環境変数読み込み（Config）
  │
  ├─ 3. ロギング設定（Logger）
  │      └─ output/terakoya_logs/invoice_{timestamp}.log
  │
  ├─ 4. ブラウザ起動（Browser）
  │      └─ Chrome WebDriver初期化
  │
  ├─ 5. ログイン（TerakoyaClient.login）
  │      ├─ トップページアクセス
  │      ├─ JavaScriptレンダリング待機（3秒）
  │      ├─ ログインボタン（div要素）をJavaScriptでクリック
  │      ├─ ログインモーダル表示待機（2秒）
  │      ├─ 認証情報入力（email, password）
  │      ├─ ボタン有効化待機（1秒）
  │      ├─ ログインボタンクリック（XPath使用）
  │      ├─ ページ遷移待機
  │      ├─ エラーメッセージチェック
  │      └─ スクリーンショット保存
  │      ※ 技術的制約: クライアントサイドレンダリング対応、XPath使用、JS click必要
  │
  ├─ 6. レッスンデータ取得（get_lessons_for_month）
  │      ├─ レッスンメニューへ移動
  │      ├─ JavaScriptで「編集」ボタンを検出（最大100件、完全一致）
  │      ├─ 各レッスンカードのテキストを取得
  │      ├─ AI抽出 or 正規表現で情報を抽出
  │      │   ├─ 日付: MM/DD(曜) → YYYY-MM-DD
  │      │   ├─ 生徒名: 人名のみ（ステータス語を除外）
  │      │   ├─ カテゴリ: 専属レッスン/初回レッスン/エキスパートコース
  │      │   └─ 時間: 開始・終了時刻から計算
  │      ├─ 重複削除（date + student_nameの組み合わせ）
  │      ├─ データ保存（JSON, CSV）
  │      └─ ログ出力: "取得したレッスン数: X件（重複削除後）"
  │
  ├─ 7. 請求申請ページへ移動（navigate_to_invoice_page）
  │      ├─ 請求申請メニューをクリック
  │      └─ 対象月を選択
  │
  ├─ 8. 既存申請確認（get_existing_invoices）
  │      ├─ 既存申請項目を取得
  │      ├─ 重複チェック（is_duplicate）
  │      └─ ログ出力: "既存申請: X件、未申請: Y件"
  │
  ├─ 9. 請求項目追加ループ
  │      for each 未申請レッスン:
  │        ├─ add_invoice_item_with_retry（最大3回）
  │        │   ├─ モーダルを開く
  │        │   ├─ フォーム入力（日付、カテゴリー、受講生、時間、単価）
  │        │   ├─ 追加ボタンをクリック
  │        │   ├─ 成功/失敗を記録
  │        │   └─ スクリーンショット保存
  │        └─ エラー時はスキップして継続
  │
  ├─ 10. 追加結果サマリー表示
  │       ├─ 成功: X件
  │       ├─ 失敗: Y件
  │       └─ スキップ（既存）: Z件
  │
  ├─ 11. 最終確認プロンプト（ドライランでない場合）
  │       ├─ "申請を送信しますか？ (y/n): "
  │       ├─ y → 次へ
  │       └─ n → 終了
  │
  ├─ 12. 送信実行（submit_invoice）
  │       ├─ 送信ボタンをクリック
  │       ├─ 確認ダイアログ処理
  │       ├─ スクリーンショット保存
  │       └─ ログ出力: "送信完了"
  │
  └─ 13. ブラウザクローズ
         └─ [終了]
```

### 5.2 エラーフロー

```
[エラー発生]
  │
  ├─ TimeoutException
  │   ├─ ログ記録: "タイムアウトエラー"
  │   ├─ スクリーンショット保存
  │   ├─ リトライカウント確認
  │   │   ├─ 最大回数未満 → 2秒待機後リトライ
  │   │   └─ 最大回数到達 → InvoiceResult.FAILED
  │   └─ 次のレッスンへスキップ
  │
  ├─ NoSuchElementException
  │   ├─ ログ記録: "要素が見つかりません"
  │   ├─ スクリーンショット保存
  │   ├─ InvoiceResult.FAILED
  │   └─ 次のレッスンへスキップ
  │
  ├─ SessionExpiredError
  │   ├─ ログ記録: "セッション期限切れ"
  │   ├─ ensure_logged_in()で再ログイン
  │   │   ├─ 成功 → 処理継続
  │   │   └─ 失敗 → InvoiceResult.FAILED
  │   └─ 次のレッスンへスキップ
  │
  └─ 予期しないエラー
      ├─ ログ記録: "未知のエラー" + スタックトレース
      ├─ スクリーンショット保存
      ├─ InvoiceResult.FAILED
      └─ 次のレッスンへスキップ
```

### 5.3 セッション管理フロー

```
[操作実行前]
  │
  ├─ check_session_validity()
  │   ├─ ログイン状態確認要素を検索
  │   │   ├─ 見つかった → セッション有効
  │   │   └─ 見つからない → セッション無効
  │   └─ 結果を返却
  │
  ├─ ensure_logged_in()
  │   ├─ check_session_validity()
  │   │   ├─ True → 処理継続
  │   │   └─ False → 再ログイン試行
  │   │       ├─ login(email, password)
  │   │       │   ├─ 成功 → 処理継続
  │   │       │   └─ 失敗 → SessionExpiredError
  │   │       └─ ログ出力
  │   └─ 結果を返却
  │
  └─ [通常処理へ]
```

## 6. 非機能要件

### 6.1 パフォーマンス
- ブラウザ操作のタイムアウト: 10-30秒
- ページロード待機: 最大30秒
- リトライ間隔: 2秒
- 1レッスンあたりの処理時間: 約10-15秒

### 6.2 信頼性
- リトライ機能: 最大3回
- セッションタイムアウト対策: 自動再ログイン
- エラー時のグレースフルデグラデーション（一部失敗でも継続）
- 詳細ログとスクリーンショットによるトレーサビリティ

### 6.3 保守性
- モジュール化された構成（レイヤー分離）
- SOLID原則の遵守
- 型ヒントの使用
- 包括的なドキュメント

### 6.4 セキュリティ
- 認証情報の環境変数管理
- .envファイルの.gitignore登録
- 重複申請防止機能
- 監査証跡（ログ、スクリーンショット）

## 7. 依存関係

### 7.1 外部ライブラリ
```
selenium==4.x
webdriver-manager==3.x
beautifulsoup4==4.x
lxml==4.x
pandas==2.x
python-dotenv==1.x
anthropic[vertex]==0.x
google-cloud-aiplatform==1.x
```

### 7.2 実行環境
- Python 3.11+
- Google Chrome（最新版）
- ChromeDriver（webdriver-managerで自動管理）
- Vertex AI（Claude）

## 8. デプロイメント

### 8.1 インストール手順
```bash
# 1. リポジトリクローン
git clone <repository>
cd selenium-automation

# 2. 仮想環境セットアップ
pipenv install

# 3. 環境変数設定
cp .env.template .env
# .envファイルを編集（認証情報を設定）

# 4. Vertex AIセットアップ
./scripts/setup-vertex-ai.sh
```

### 8.2 実行方法
```bash
# ドライラン（送信しない）
pipenv run python examples/terakoya_invoice.py --month 2025-10 --dry-run

# 本番実行
pipenv run python examples/terakoya_invoice.py --month 2025-10

# ヘッドレスモード
pipenv run python examples/terakoya_invoice.py --month 2025-10 --headless
```

## 9. テスト戦略

### 9.1 単体テスト
- Browserクラス: モック使用、基本操作のテスト
- TerakoyaClientクラス: モックブラウザ使用、ビジネスロジックのテスト
- Utilityクラス: 入出力のテスト

### 9.2 統合テスト
- ドライランモードでの全体フロー確認
- ダミーデータを使用したエンドツーエンドテスト

### 9.3 本番前確認
- チェックリストに基づく手動確認
- ログとスクリーンショットのレビュー

## 10. 制約と前提条件

### 10.1 前提条件
- Samurai Terakoyaのアカウント保持
- Google Cloud プロジェクトとVertex AI有効化
- Chrome ブラウザインストール済み
- 対象月のレッスンが完了している

### 10.2 制約事項
- サイトのHTML構造変更時は要修正
- ネットワーク環境に依存
- 1セッションあたりの処理上限（サイト側の制限に準拠）

## 11. 今後の拡張性

### 11.1 Phase 2（予定）
- レポート生成機能
- PDF出力
- メール送信

### 11.2 Phase 3（検討中）
- AI活用の高度化（異常検知、最適化提案）
- 複数カテゴリー対応
- バッチ処理の並列化

### 11.3 Phase 4（検討中）
- CI/CD統合
- Slack通知
- ダッシュボード

## 12. 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-11-01 | 1.0 | 初版作成 | - |

## 13. 参考資料

- [実装計画書](../plans/terakoya_invoice_automation.md)
- [API仕様書](./terakoya_api_specification.md)
- [データ構造設計書](./terakoya_data_structure.md)
- [セキュリティ設計書](./terakoya_security_design.md)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Selenium with Python](https://selenium-python.readthedocs.io/)
