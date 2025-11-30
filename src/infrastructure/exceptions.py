"""インフラストラクチャ層の例外クラス定義

外部システムとの連携、データベース、ファイルシステムなど
インフラストラクチャ層で発生する例外を定義
"""

from typing import Any

from src.domain.exceptions import PolibaseException


class InfrastructureException(PolibaseException):
    """インフラストラクチャ層の基底例外クラス

    外部システムや技術的な実装に関連する例外の基底クラス
    """

    pass


class DatabaseError(InfrastructureException):
    """データベース関連エラー（後方互換性のため）

    旧来のDatabaseErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="INF-DB",
            details=details or {},
        )


class DatabaseException(InfrastructureException):
    """データベース関連エラー

    データベースへのアクセスや操作で発生するエラー
    """

    def __init__(
        self,
        operation: str,
        reason: str,
        table: str | None = None,
        query: str | None = None,
        original_error: Exception | None = None,
    ):
        """
        Args:
            operation: 実行した操作（SELECT, INSERT, UPDATE, DELETE等）
            reason: エラーの理由
            table: 対象テーブル名
            query: 実行したクエリ（デバッグ用）
            original_error: 元の例外
        """
        message = f"データベースエラー ({operation}): {reason}"
        if table:
            message += f" - テーブル: {table}"

        super().__init__(
            message=message,
            error_code="INF-001",
            details={
                "operation": operation,
                "reason": reason,
                "table": table,
                "query": query[:200] if query else None,
                "original_error": str(original_error) if original_error else None,
            },
        )


class ConnectionError(InfrastructureException):
    """接続エラー（後方互換性のため）

    旧来のConnectionErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="INF-CONN",
            details=details or {},
        )


class ConnectionException(InfrastructureException):
    """接続エラー

    外部システムへの接続に失敗した場合のエラー
    """

    def __init__(
        self,
        service: str,
        endpoint: str | None = None,
        reason: str | None = None,
        retry_after: int | None = None,
    ):
        """
        Args:
            service: サービス名（PostgreSQL, Redis, GCS等）
            endpoint: 接続先エンドポイント
            reason: 接続失敗の理由
            retry_after: リトライまでの待機時間（秒）
        """
        message = f"サービス '{service}' への接続に失敗しました"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            error_code="INF-002",
            details={
                "service": service,
                "endpoint": endpoint,
                "reason": reason,
                "retry_after": retry_after,
            },
        )


class ExternalServiceException(InfrastructureException):
    """外部サービスエラー

    外部API呼び出しやサービス連携で発生するエラー
    """

    def __init__(
        self,
        service: str,
        operation: str,
        status_code: int | None = None,
        response_body: str | None = None,
        reason: str | None = None,
    ):
        """
        Args:
            service: サービス名（Gemini API, GCS等）
            operation: 実行した操作
            status_code: HTTPステータスコード
            response_body: レスポンスボディ
            reason: エラーの理由
        """
        message = f"外部サービス '{service}' でエラー ({operation})"
        if status_code:
            message += f" - ステータス: {status_code}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            error_code="INF-003",
            details={
                "service": service,
                "operation": operation,
                "status_code": status_code,
                "response_body": response_body[:500] if response_body else None,
                "reason": reason,
            },
        )


class AuthenticationError(InfrastructureException):
    """認証エラー

    外部サービスへの認証に失敗した場合のエラー
    """

    def __init__(
        self,
        service: str,
        reason: str | None = None,
        solution: str | None = None,
    ):
        """
        Args:
            service: サービス名（Google Cloud Storage, AWS S3等）
            reason: 認証失敗の理由
            solution: 解決方法（再認証コマンドなど）
        """
        message = f"サービス '{service}' の認証に失敗しました"
        if reason:
            message += f": {reason}"
        if solution:
            message += f"\n\n解決方法: {solution}"

        super().__init__(
            message=message,
            error_code="INF-AUTH",
            details={
                "service": service,
                "reason": reason,
                "solution": solution,
            },
        )


class FileSystemException(InfrastructureException):
    """ファイルシステムエラー

    ファイルの読み書きや操作で発生するエラー
    """

    def __init__(
        self,
        operation: str,
        file_path: str,
        reason: str,
        original_error: Exception | None = None,
    ):
        """
        Args:
            operation: 実行した操作（read, write, delete等）
            file_path: 対象ファイルパス
            reason: エラーの理由
            original_error: 元の例外
        """
        message = f"ファイル操作エラー ({operation}): {file_path} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-004",
            details={
                "operation": operation,
                "file_path": file_path,
                "reason": reason,
                "original_error": str(original_error) if original_error else None,
            },
        )


class StorageError(InfrastructureException):
    """ストレージエラー（後方互換性のため）

    旧来のStorageErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="INF-STORAGE",
            details=details or {},
        )


class StorageException(InfrastructureException):
    """ストレージエラー

    クラウドストレージやオブジェクトストレージ関連のエラー
    """

    def __init__(
        self,
        storage_type: str,
        operation: str,
        resource: str,
        reason: str,
        bucket: str | None = None,
    ):
        """
        Args:
            storage_type: ストレージタイプ（GCS, S3等）
            operation: 実行した操作（upload, download, delete等）
            resource: 対象リソース（ファイル名等）
            reason: エラーの理由
            bucket: バケット名
        """
        message = f"{storage_type}ストレージエラー ({operation}): {resource} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-005",
            details={
                "storage_type": storage_type,
                "operation": operation,
                "resource": resource,
                "bucket": bucket,
                "reason": reason,
            },
        )


class CacheException(InfrastructureException):
    """キャッシュエラー

    キャッシュシステムに関連するエラー
    """

    def __init__(
        self,
        operation: str,
        cache_key: str,
        reason: str,
        cache_type: str | None = None,
    ):
        """
        Args:
            operation: 実行した操作（get, set, delete等）
            cache_key: キャッシュキー
            reason: エラーの理由
            cache_type: キャッシュタイプ（Redis, Memcached等）
        """
        message = f"キャッシュエラー ({operation}): {cache_key} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-006",
            details={
                "operation": operation,
                "cache_key": cache_key,
                "reason": reason,
                "cache_type": cache_type,
            },
        )


class NetworkException(InfrastructureException):
    """ネットワークエラー

    ネットワーク通信に関連するエラー
    """

    def __init__(
        self,
        operation: str,
        url: str,
        reason: str,
        timeout: int | None = None,
        retry_count: int | None = None,
    ):
        """
        Args:
            operation: 実行した操作（GET, POST等）
            url: URL
            reason: エラーの理由
            timeout: タイムアウト時間（秒）
            retry_count: リトライ回数
        """
        message = f"ネットワークエラー ({operation}): {url} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-007",
            details={
                "operation": operation,
                "url": url,
                "reason": reason,
                "timeout": timeout,
                "retry_count": retry_count,
            },
        )


class SerializationException(InfrastructureException):
    """シリアライゼーションエラー

    データのシリアライズ/デシリアライズで発生するエラー
    """

    def __init__(
        self,
        operation: str,
        data_format: str,
        reason: str,
        data_sample: str | None = None,
    ):
        """
        Args:
            operation: 実行した操作（serialize, deserialize）
            data_format: データフォーマット（JSON, XML, YAML等）
            reason: エラーの理由
            data_sample: データサンプル（デバッグ用）
        """
        message = f"シリアライゼーションエラー ({operation}): {data_format} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-008",
            details={
                "operation": operation,
                "data_format": data_format,
                "reason": reason,
                "data_sample": data_sample[:200] if data_sample else None,
            },
        )


class TimeoutException(InfrastructureException):
    """タイムアウトエラー

    処理がタイムアウトした場合のエラー
    """

    def __init__(
        self, operation: str, timeout_seconds: int, resource: str | None = None
    ):
        """
        Args:
            operation: タイムアウトした操作
            timeout_seconds: タイムアウト時間（秒）
            resource: 対象リソース
        """
        message = f"操作 '{operation}' がタイムアウトしました ({timeout_seconds}秒)"
        if resource:
            message += f" - リソース: {resource}"

        super().__init__(
            message=message,
            error_code="INF-009",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                "resource": resource,
            },
        )


class RateLimitException(InfrastructureException):
    """レート制限エラー

    APIのレート制限に達した場合のエラー
    """

    def __init__(
        self,
        service: str,
        limit: int,
        reset_at: str | None = None,
        retry_after: int | None = None,
    ):
        """
        Args:
            service: サービス名
            limit: レート制限値
            reset_at: 制限がリセットされる時刻
            retry_after: リトライまでの待機時間（秒）
        """
        message = f"サービス '{service}' のレート制限に達しました (制限: {limit})"
        super().__init__(
            message=message,
            error_code="INF-010",
            details={
                "service": service,
                "limit": limit,
                "reset_at": reset_at,
                "retry_after": retry_after,
            },
        )


# LLM Service Exceptions


class LLMError(InfrastructureException):
    """LLM関連エラー（後方互換性のため）

    旧来のLLMErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="INF-LLM",
            details=details or {},
        )


class LLMServiceException(ExternalServiceException):
    """LLMサービス関連エラー

    LLM APIとの連携で発生するエラー
    """

    def __init__(
        self,
        operation: str,
        reason: str,
        model: str | None = None,
        status_code: int | None = None,
    ):
        """
        Args:
            operation: 実行した操作
            reason: エラーの理由
            model: 使用したモデル名
            status_code: HTTPステータスコード
        """
        super().__init__(
            service="LLM",
            operation=operation,
            status_code=status_code,
            reason=reason,
        )
        if model:
            self.details["model"] = model


class APIKeyError(LLMServiceException):
    """APIキーエラー（後方互換性のため）

    旧来のAPIKeyErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            operation="認証",
            reason=message,
        )
        if details:
            self.details.update(details)


class APIKeyException(LLMServiceException):
    """APIキーエラー

    APIキーが不正または不足している場合のエラー
    """

    def __init__(self, service: str = "LLM", reason: str | None = None):
        """
        Args:
            service: サービス名
            reason: エラーの理由
        """
        default_reason = "APIキーが設定されていないか、無効です"
        super().__init__(
            operation="認証",
            reason=reason or default_reason,
        )


class ModelException(LLMServiceException):
    """モデルエラー

    LLMモデルの実行中に発生するエラー
    """

    def __init__(self, model: str, reason: str):
        """
        Args:
            model: モデル名
            reason: エラーの理由
        """
        super().__init__(
            operation="モデル実行",
            reason=reason,
            model=model,
        )


class TokenLimitException(LLMServiceException):
    """トークン制限エラー

    トークン数の制限を超過した場合のエラー
    """

    def __init__(self, limit: int, actual: int, model: str | None = None):
        """
        Args:
            limit: トークン制限
            actual: 実際のトークン数
            model: モデル名
        """
        super().__init__(
            operation="トークン処理",
            reason=f"トークン数が制限を超過 (制限: {limit}, 実際: {actual})",
            model=model,
        )
        self.details["token_limit"] = limit
        self.details["actual_tokens"] = actual


class ResponseParsingException(LLMServiceException):
    """レスポンスパースエラー

    LLMレスポンスのパース中に発生するエラー
    """

    def __init__(self, reason: str, response_sample: str | None = None):
        """
        Args:
            reason: エラーの理由
            response_sample: レスポンスのサンプル
        """
        super().__init__(
            operation="レスポンスパース",
            reason=reason,
        )
        if response_sample:
            self.details["response_sample"] = response_sample[:200]


# Web Scraping Exceptions


class ScrapingError(InfrastructureException):
    """Webスクレイピング関連エラー（後方互換性のため）

    旧来のScrapingErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="INF-SCRAPE",
            details=details or {},
        )


class WebScrapingException(InfrastructureException):
    """Webスクレイピング関連エラー

    Webスクレイピング中に発生するエラー
    """

    def __init__(self, operation: str, url: str, reason: str):
        """
        Args:
            operation: 実行した操作
            url: 対象URL
            reason: エラーの理由
        """
        message = f"Webスクレイピングエラー ({operation}): {url} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-011",
            details={"operation": operation, "url": url, "reason": reason},
        )


class URLException(WebScrapingException):
    """URL関連エラー

    URLが無効またはアクセスできない場合のエラー
    """

    def __init__(self, url: str, reason: str):
        """
        Args:
            url: 問題のあるURL
            reason: エラーの理由
        """
        super().__init__(
            operation="URLアクセス",
            url=url,
            reason=reason,
        )


class PageLoadException(WebScrapingException):
    """ページロードエラー

    ページの読み込みに失敗した場合のエラー
    """

    def __init__(self, url: str, reason: str, timeout: int | None = None):
        """
        Args:
            url: ページURL
            reason: エラーの理由
            timeout: タイムアウト時間（秒）
        """
        super().__init__(
            operation="ページロード",
            url=url,
            reason=reason,
        )
        if timeout:
            self.details["timeout"] = timeout


class ElementNotFoundException(WebScrapingException):
    """要素未検出エラー

    期待される要素がページ上に見つからない場合のエラー
    """

    def __init__(self, selector: str, page_url: str):
        """
        Args:
            selector: セレクタ
            page_url: ページURL
        """
        super().__init__(
            operation="要素検索",
            url=page_url,
            reason=f"セレクタ '{selector}' に一致する要素が見つかりません",
        )
        self.details["selector"] = selector


class DownloadException(WebScrapingException):
    """ダウンロードエラー

    ファイルのダウンロードに失敗した場合のエラー
    """

    def __init__(self, url: str, file_type: str, reason: str):
        """
        Args:
            url: ダウンロードURL
            file_type: ファイルタイプ
            reason: エラーの理由
        """
        super().__init__(
            operation=f"{file_type}ダウンロード",
            url=url,
            reason=reason,
        )


# Repository Exceptions


class RepositoryException(InfrastructureException):
    """リポジトリ関連エラー

    データリポジトリ操作で発生するエラー
    """

    def __init__(
        self,
        operation: str,
        entity_type: str,
        reason: str,
        entity_id: int | None = None,
    ):
        """
        Args:
            operation: 実行した操作（save, update, delete等）
            entity_type: エンティティタイプ
            reason: エラーの理由
            entity_id: エンティティID（あれば）
        """
        message = f"リポジトリエラー ({operation}): {entity_type} - {reason}"
        if entity_id:
            message += f" (ID: {entity_id})"

        super().__init__(
            message=message,
            error_code="INF-012",
            details={
                "operation": operation,
                "entity_type": entity_type,
                "reason": reason,
                "entity_id": entity_id,
            },
        )


class SaveError(RepositoryException):
    """保存エラー（後方互換性のため）

    旧来のSaveErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            operation="保存",
            entity_type=details.get("entity_type", "Unknown") if details else "Unknown",
            reason=message,
        )
        # Merge input details with the standard details from RepositoryException
        if details:
            self.details.update(details)


class SaveException(RepositoryException):
    """保存エラー

    エンティティの保存に失敗した場合のエラー
    """

    def __init__(self, entity_type: str, reason: str):
        """
        Args:
            entity_type: エンティティタイプ
            reason: エラーの理由
        """
        super().__init__(
            operation="保存",
            entity_type=entity_type,
            reason=reason,
        )


class UpdateError(RepositoryException):
    """更新エラー（後方互換性のため）

    旧来のUpdateErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        entity_id = details.get("entity_id") if details else None
        super().__init__(
            operation="更新",
            entity_type=details.get("entity_type", "Unknown") if details else "Unknown",
            entity_id=entity_id if isinstance(entity_id, int) else None,
            reason=message,
        )


class UpdateException(RepositoryException):
    """更新エラー

    エンティティの更新に失敗した場合のエラー
    """

    def __init__(self, entity_type: str, entity_id: int, reason: str):
        """
        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID
            reason: エラーの理由
        """
        super().__init__(
            operation="更新",
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
        )


class DeleteException(RepositoryException):
    """削除エラー

    エンティティの削除に失敗した場合のエラー
    """

    def __init__(self, entity_type: str, entity_id: int, reason: str):
        """
        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID
            reason: エラーの理由
        """
        super().__init__(
            operation="削除",
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
        )


class RecordNotFoundError(RepositoryException):
    """レコード未検出エラー（後方互換性のため）

    旧来のRecordNotFoundErrorとの互換性を保つための例外クラス
    """

    def __init__(self, entity_type: str, entity_id: Any):
        """
        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID
        """
        super().__init__(
            operation="検索",
            entity_type=entity_type,
            entity_id=entity_id if isinstance(entity_id, int) else None,
            reason=f"ID {entity_id} のレコードが見つかりません",
        )


class RecordNotFoundException(RepositoryException):
    """レコード未検出エラー

    指定されたレコードが見つからない場合のエラー
    """

    def __init__(self, entity_type: str, entity_id: int):
        """
        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID
        """
        super().__init__(
            operation="検索",
            entity_type=entity_type,
            entity_id=entity_id,
            reason=f"ID {entity_id} のレコードが見つかりません",
        )


class DuplicateRecordException(RepositoryException):
    """重複レコードエラー

    重複するレコードを作成しようとした場合のエラー
    """

    def __init__(self, entity_type: str, identifier: str):
        """
        Args:
            entity_type: エンティティタイプ
            identifier: 重複を検出した識別子
        """
        super().__init__(
            operation="保存",
            entity_type=entity_type,
            reason=f"重複するレコードが存在します: {identifier}",
        )
        self.details["identifier"] = identifier


# Additional Database Exceptions


class QueryException(DatabaseException):
    """クエリ実行エラー

    SQLクエリの実行に失敗した場合のエラー
    """

    def __init__(self, query: str, reason: str, table: str | None = None):
        """
        Args:
            query: 実行したクエリ
            reason: エラーの理由
            table: 対象テーブル
        """
        super().__init__(
            operation="クエリ実行",
            reason=reason,
            table=table,
            query=query,
        )


class IntegrityError(DatabaseException):
    """整合性制約エラー（後方互換性のため）

    旧来のIntegrityErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            operation="整合性チェック",
            reason=message,
            table=details.get("table") if details else None,
        )


class IntegrityException(DatabaseException):
    """整合性制約エラー

    データベースの整合性制約違反が発生した場合のエラー
    """

    def __init__(
        self,
        constraint: str,
        table: str,
        reason: str,
        original_error: Exception | None = None,
    ):
        """
        Args:
            constraint: 違反した制約名
            table: 対象テーブル
            reason: エラーの理由
            original_error: 元の例外
        """
        super().__init__(
            operation="整合性チェック",
            reason=f"制約 '{constraint}' 違反: {reason}",
            table=table,
            original_error=original_error,
        )
        self.details["constraint"] = constraint


# Additional Storage Exceptions


class FileNotFoundException(FileSystemException):
    """ファイル未検出エラー

    指定されたファイルが見つからない場合のエラー
    """

    def __init__(self, file_path: str):
        """
        Args:
            file_path: ファイルパス
        """
        super().__init__(
            operation="ファイル読み取り",
            file_path=file_path,
            reason="ファイルが存在しません",
        )


class UploadException(StorageException):
    """アップロードエラー

    ファイルのアップロードに失敗した場合のエラー
    """

    def __init__(
        self, storage_type: str, resource: str, reason: str, bucket: str | None = None
    ):
        """
        Args:
            storage_type: ストレージタイプ
            resource: リソース名
            reason: エラーの理由
            bucket: バケット名
        """
        super().__init__(
            storage_type=storage_type,
            operation="アップロード",
            resource=resource,
            reason=reason,
            bucket=bucket,
        )


class PermissionError(StorageException):
    """権限エラー（後方互換性のため）

    旧来のPermissionErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            storage_type=details.get("storage_type", "Storage")
            if details
            else "Storage",
            operation=details.get("operation", "access") if details else "access",
            resource=details.get("resource", "") if details else "",
            reason=message,
        )


class PermissionException(StorageException):
    """権限エラー

    ストレージリソースへのアクセス権限がない場合のエラー
    """

    def __init__(
        self,
        storage_type: str,
        resource: str,
        operation: str,
        bucket: str | None = None,
    ):
        """
        Args:
            storage_type: ストレージタイプ
            resource: リソース名
            operation: 実行しようとした操作
            bucket: バケット名
        """
        super().__init__(
            storage_type=storage_type,
            operation=operation,
            resource=resource,
            reason="アクセス権限がありません",
            bucket=bucket,
        )
