"""アプリケーション層の例外クラス定義

ユースケース実行時に発生する例外を定義
"""

from typing import Any

from src.domain.exceptions import PolibaseException


class ApplicationException(PolibaseException):
    """アプリケーション層の基底例外クラス

    ユースケースやアプリケーションサービスで発生する例外の基底クラス
    """

    pass


class UseCaseException(ApplicationException):
    """ユースケース実行エラー

    ユースケースの実行中に発生する一般的なエラー
    """

    def __init__(
        self,
        use_case: str,
        operation: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ):
        """
        Args:
            use_case: ユースケース名
            operation: 実行中の操作
            reason: エラーの理由
            details: 追加の詳細情報
        """
        message = (
            f"ユースケース '{use_case}' の操作 '{operation}' が失敗しました: {reason}"
        )
        super().__init__(
            message=message,
            error_code="APP-001",
            details={
                "use_case": use_case,
                "operation": operation,
                "reason": reason,
                **(details or {}),
            },
        )


class ValidationException(ApplicationException):
    """バリデーションエラー

    入力データのバリデーションに失敗した場合に発生
    """

    def __init__(
        self, field: str, value: Any, constraint: str, message: str | None = None
    ):
        """
        Args:
            field: バリデーションエラーが発生したフィールド
            value: 不正な値
            constraint: 違反した制約
            message: カスタムエラーメッセージ
        """
        error_message = message or f"フィールド '{field}' の値が不正です: {constraint}"
        super().__init__(
            message=error_message,
            error_code="APP-002",
            details={"field": field, "value": value, "constraint": constraint},
        )


class AuthorizationException(ApplicationException):
    """認可エラー

    権限不足により操作が実行できない場合に発生
    """

    def __init__(
        self, resource: str, action: str, required_permission: str | None = None
    ):
        """
        Args:
            resource: アクセスしようとしたリソース
            action: 実行しようとしたアクション
            required_permission: 必要な権限
        """
        message = f"リソース '{resource}' に対する操作 '{action}' の権限がありません"
        super().__init__(
            message=message,
            error_code="APP-003",
            details={
                "resource": resource,
                "action": action,
                "required_permission": required_permission,
            },
        )


class ResourceNotFoundException(ApplicationException):
    """リソースが見つからないエラー

    アプリケーション層でリソースが見つからない場合に発生
    """

    def __init__(
        self, resource_type: str, identifier: Any, search_context: str | None = None
    ):
        """
        Args:
            resource_type: リソースの種類
            identifier: リソースの識別子
            search_context: 検索コンテキスト
        """
        message = f"リソース '{resource_type}' (ID: {identifier}) が見つかりません"
        if search_context:
            message += f" (コンテキスト: {search_context})"

        super().__init__(
            message=message,
            error_code="APP-004",
            details={
                "resource_type": resource_type,
                "identifier": identifier,
                "search_context": search_context,
            },
        )


class WorkflowException(ApplicationException):
    """ワークフローエラー

    ワークフローの実行中に発生するエラー
    """

    def __init__(self, workflow: str, step: str, reason: str, can_retry: bool = False):
        """
        Args:
            workflow: ワークフロー名
            step: 失敗したステップ
            reason: エラーの理由
            can_retry: リトライ可能かどうか
        """
        message = f"ワークフロー '{workflow}' のステップ '{step}' で失敗: {reason}"
        super().__init__(
            message=message,
            error_code="APP-005",
            details={
                "workflow": workflow,
                "step": step,
                "reason": reason,
                "can_retry": can_retry,
            },
        )


class ConcurrencyException(ApplicationException):
    """並行実行エラー

    並行処理における競合状態が発生した場合のエラー
    """

    def __init__(self, resource: str, operation: str, conflict_details: str):
        """
        Args:
            resource: 競合が発生したリソース
            operation: 実行しようとした操作
            conflict_details: 競合の詳細
        """
        message = (
            f"リソース '{resource}' への並行アクセスで競合が発生: {conflict_details}"
        )
        super().__init__(
            message=message,
            error_code="APP-006",
            details={
                "resource": resource,
                "operation": operation,
                "conflict": conflict_details,
            },
        )


class ConfigurationError(ApplicationException):
    """設定エラー（後方互換性のため）

    旧来のConfigurationErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="APP-CFG",
            details=details or {},
        )


class ConfigurationException(ApplicationException):
    """設定エラー

    アプリケーションの設定に関するエラー
    """

    def __init__(
        self,
        config_key: str,
        reason: str,
        expected_value: Any | None = None,
        actual_value: Any | None = None,
    ):
        """
        Args:
            config_key: 設定キー
            reason: エラーの理由
            expected_value: 期待される値
            actual_value: 実際の値
        """
        message = f"設定 '{config_key}' のエラー: {reason}"
        super().__init__(
            message=message,
            error_code="APP-007",
            details={
                "config_key": config_key,
                "reason": reason,
                "expected_value": expected_value,
                "actual_value": actual_value,
            },
        )


class MissingConfigException(ConfigurationException):
    """必須設定が不足しているエラー

    必要な設定値が見つからない場合に発生
    """

    def __init__(self, config_key: str, message: str | None = None):
        """
        Args:
            config_key: 不足している設定キー
            message: カスタムエラーメッセージ
        """
        reason = message or f"必須設定 '{config_key}' が設定されていません"
        super().__init__(
            config_key=config_key,
            reason=reason,
        )


class InvalidConfigException(ConfigurationException):
    """設定値が不正なエラー

    設定値が期待される形式や値でない場合に発生
    """

    def __init__(
        self,
        config_key: str,
        actual_value: Any,
        reason: str,
        expected_value: Any | None = None,
    ):
        """
        Args:
            config_key: 設定キー
            actual_value: 実際の値
            reason: 不正な理由
            expected_value: 期待される値
        """
        super().__init__(
            config_key=config_key,
            reason=reason,
            expected_value=expected_value,
            actual_value=actual_value,
        )


class DataProcessingException(ApplicationException):
    """データ処理エラー

    データの変換や処理中に発生するエラー
    """

    def __init__(
        self,
        process: str,
        data_type: str,
        reason: str,
        input_data: Any | None = None,
    ):
        """
        Args:
            process: 処理名
            data_type: データタイプ
            reason: エラーの理由
            input_data: 処理対象のデータ（デバッグ用）
        """
        message = f"データ処理 '{process}' でエラー ({data_type}): {reason}"
        super().__init__(
            message=message,
            error_code="APP-008",
            details={
                "process": process,
                "data_type": data_type,
                "reason": reason,
                "input_data": str(input_data)[:200] if input_data else None,
            },
        )


class ProcessingError(ApplicationException):
    """一般的な処理エラー（後方互換性のため）

    旧来のProcessingErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="APP-PROC",
            details=details or {},
        )


class ProcessingException(ApplicationException):
    """一般的な処理エラー

    ユースケース内での処理中に発生する一般的なエラー
    """

    def __init__(
        self, process: str, reason: str, details: dict[str, Any] | None = None
    ):
        """
        Args:
            process: 処理名
            reason: エラーの理由
            details: 追加の詳細情報
        """
        message = f"処理 '{process}' でエラーが発生: {reason}"
        super().__init__(
            message=message,
            error_code="APP-009",
            details={"process": process, "reason": reason, **(details or {})},
        )


class PDFProcessingError(DataProcessingException):
    """PDF処理エラー（後方互換性のため）

    旧来のPDFProcessingErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            process="PDF処理",
            data_type="PDF",
            reason=message,
            input_data=details.get("file_path") if details else None,
        )


class PDFProcessingException(DataProcessingException):
    """PDF処理エラー

    PDF文書の処理中に発生するエラー
    """

    def __init__(self, file_path: str, reason: str):
        """
        Args:
            file_path: PDFファイルのパス
            reason: エラーの理由
        """
        super().__init__(
            process="PDF処理",
            data_type="PDF",
            reason=reason,
            input_data=file_path,
        )


class TextExtractionError(DataProcessingException):
    """テキスト抽出エラー（後方互換性のため）

    旧来のTextExtractionErrorとの互換性を保つための例外クラス
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            process="テキスト抽出",
            data_type="テキスト",
            reason=message,
            input_data=details.get("source") if details else None,
        )


class TextExtractionException(DataProcessingException):
    """テキスト抽出エラー

    文書からのテキスト抽出中に発生するエラー
    """

    def __init__(self, source: str, reason: str):
        """
        Args:
            source: 抽出元
            reason: エラーの理由
        """
        super().__init__(
            process="テキスト抽出",
            data_type="テキスト",
            reason=reason,
            input_data=source,
        )


class ParsingException(DataProcessingException):
    """パース処理エラー

    データのパース中に発生するエラー
    """

    def __init__(self, data_format: str, reason: str, raw_data: Any | None = None):
        """
        Args:
            data_format: データフォーマット（JSON, XML等）
            reason: エラーの理由
            raw_data: パース対象の生データ
        """
        super().__init__(
            process="パース",
            data_type=data_format,
            reason=reason,
            input_data=raw_data,
        )


class AuthenticationFailedException(ApplicationException):
    """認証失敗例外

    外部サービスへの認証に失敗した場合のApplication層表現
    Infrastructure層のAuthenticationErrorをラップして使用
    """

    def __init__(self, service: str, reason: str, solution: str | None = None):
        """
        Args:
            service: サービス名（Google Cloud Storage, AWS S3等）
            reason: 認証失敗の理由
            solution: 解決方法（再認証コマンドなど）
        """
        message = f"サービス '{service}' の認証に失敗しました: {reason}"
        if solution:
            message += f"\n\n解決方法:\n{solution}"

        super().__init__(
            message=message,
            error_code="APP-010",
            details={
                "service": service,
                "reason": reason,
                "solution": solution,
            },
        )
