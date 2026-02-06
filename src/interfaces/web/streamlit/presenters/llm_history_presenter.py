"""LLM processing history presenter for Streamlit web interface."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from src.common.logging import get_logger
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.interfaces.web.streamlit.dto.base import WebResponseDTO
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class LLMHistoryPresenter(BasePresenter[list[LLMProcessingHistory]]):
    """Presenter for LLM processing history management."""

    def __init__(self, container: Any = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        # DIコンテナ経由でリポジトリを取得
        self.history_repo = (
            self.container.repositories.llm_processing_history_repository()
        )
        self.session = SessionManager(namespace="llm_history")
        self.logger = get_logger(self.__class__.__name__)

    def load_data(self) -> list[LLMProcessingHistory]:
        """Load all LLM processing histories.

        Returns:
            List of LLM processing histories
        """
        return self._run_async(self.history_repo.get_all())

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions from the view.

        Args:
            action: The action to perform
            **kwargs: Additional parameters for the action

        Returns:
            Result of the action
        """
        if action == "search":
            return self.search_histories(**kwargs)
        elif action == "get_statistics":
            return self.get_statistics(**kwargs)
        elif action == "export_csv":
            return self.export_to_csv(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def search_histories(
        self,
        processing_type: str | None = None,
        model_name: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> WebResponseDTO[dict[str, Any]]:
        """Search LLM processing histories with filters.

        Args:
            processing_type: Processing type filter
            model_name: Model name filter
            status: Status filter
            start_date: Start date filter
            end_date: End date filter
            limit: Number of items per page
            offset: Offset for pagination

        Returns:
            Response with search results and metadata
        """
        try:
            # Convert string filters to enums
            proc_type = (
                ProcessingType(processing_type)
                if processing_type and processing_type != "すべて"
                else None
            )
            proc_status = (
                ProcessingStatus(status) if status and status != "すべて" else None
            )
            model = None if model_name == "すべて" else model_name

            # Search histories
            histories = self._run_async(
                self.history_repo.search(
                    processing_type=proc_type,
                    model_name=model,
                    status=proc_status,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                )
            )

            # Get total count for pagination
            total_count = self._run_async(
                self.history_repo.count_by_status(
                    status=proc_status if proc_status else ProcessingStatus.COMPLETED,
                    processing_type=proc_type,
                )
            )

            return WebResponseDTO.success_response(
                data={
                    "histories": histories,
                    "total_count": total_count,
                    "page_size": limit,
                    "current_offset": offset,
                }
            )

        except Exception as e:
            self.logger.error(f"Error searching histories: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"履歴の検索に失敗しました: {str(e)}")

    def get_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> WebResponseDTO[dict[str, Any]]:
        """Get statistics for LLM processing histories.

        Args:
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Response with statistics data
        """
        try:
            # Default date range (last 30 days)
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            # Get all histories in date range
            histories = self._run_async(
                self.history_repo.search(
                    start_date=start_date,
                    end_date=end_date,
                    limit=10000,  # Large limit to get all
                    offset=0,
                )
            )

            # Calculate statistics
            total_count = len(histories)
            completed_count = sum(
                1 for h in histories if h.status == ProcessingStatus.COMPLETED
            )
            failed_count = sum(
                1 for h in histories if h.status == ProcessingStatus.FAILED
            )
            pending_count = sum(
                1 for h in histories if h.status == ProcessingStatus.PENDING
            )

            # Processing type breakdown
            type_breakdown = {}
            for proc_type in ProcessingType:
                count = sum(1 for h in histories if h.processing_type == proc_type)
                type_breakdown[proc_type.value] = count

            # Model usage breakdown
            model_breakdown = {}
            for history in histories:
                model = history.model_name or "Unknown"
                model_breakdown[model] = model_breakdown.get(model, 0) + 1

            # Token usage statistics
            total_input_tokens = sum(h.token_count_input or 0 for h in histories)
            total_output_tokens = sum(h.token_count_output or 0 for h in histories)
            total_tokens = total_input_tokens + total_output_tokens

            # Success rate by processing type
            success_rate_by_type = {}
            for proc_type in ProcessingType:
                type_histories = [
                    h for h in histories if h.processing_type == proc_type
                ]
                if type_histories:
                    completed = sum(
                        1
                        for h in type_histories
                        if h.status == ProcessingStatus.COMPLETED
                    )
                    success_rate = (completed / len(type_histories)) * 100
                    success_rate_by_type[proc_type.value] = round(success_rate, 1)

            return WebResponseDTO.success_response(
                data={
                    "total_count": total_count,
                    "completed_count": completed_count,
                    "failed_count": failed_count,
                    "pending_count": pending_count,
                    "success_rate": (
                        round((completed_count / total_count) * 100, 1)
                        if total_count > 0
                        else 0
                    ),
                    "type_breakdown": type_breakdown,
                    "model_breakdown": model_breakdown,
                    "total_input_tokens": total_input_tokens,
                    "total_output_tokens": total_output_tokens,
                    "total_tokens": total_tokens,
                    "success_rate_by_type": success_rate_by_type,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }
            )

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"統計情報の取得に失敗しました: {str(e)}"
            )

    def export_to_csv(self, histories: list[LLMProcessingHistory]) -> str:
        """Export histories to CSV format.

        Args:
            histories: List of histories to export

        Returns:
            CSV string data
        """
        if not histories:
            return ""

        # Convert to DataFrame
        data = []
        for history in histories:
            data.append(
                {
                    "ID": history.id,
                    "処理タイプ": history.processing_type.value,
                    "処理日時": (
                        history.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if history.created_at
                        else ""
                    ),
                    "ステータス": history.status.value,
                    "モデル": history.model_name or "",
                    "入力トークン": history.token_count_input or 0,
                    "出力トークン": history.token_count_output or 0,
                    "合計トークン": (
                        (history.token_count_input or 0)
                        + (history.token_count_output or 0)
                    ),
                    "モデルバージョン": history.model_version or "",
                    "エラーメッセージ": history.error_message or "",
                }
            )

        df = pd.DataFrame(data)
        return df.to_csv(index=False, encoding="utf-8-sig")

    def get_processing_types(self) -> list[str]:
        """Get all processing type options.

        Returns:
            List of processing type values including 'すべて'
        """
        return ["すべて"] + [pt.value for pt in ProcessingType]

    def get_model_names(self) -> list[str]:
        """Get common model name options.

        Returns:
            List of model names including 'すべて'
        """
        return ["すべて", "gemini-2.0-flash", "gemini-1.5-flash", "その他"]

    def get_statuses(self) -> list[str]:
        """Get all status options.

        Returns:
            List of status values including 'すべて'
        """
        return ["すべて"] + [s.value for s in ProcessingStatus]

    def get_history_detail(self, history_id: int) -> WebResponseDTO[dict[str, Any]]:
        """Get detailed information for a specific history.

        Args:
            history_id: ID of the history to retrieve

        Returns:
            Response with history details
        """
        try:
            history = self._run_async(self.history_repo.get_by_id(history_id))
            if not history:
                return WebResponseDTO.error_response(
                    f"履歴ID {history_id} が見つかりません"
                )

            # Format detail data
            detail_data = {
                "id": history.id,
                "processing_type": history.processing_type.value,
                "status": history.status.value,
                "model_name": history.model_name,
                "model_version": history.model_version,
                "input_tokens": history.token_count_input,
                "output_tokens": history.token_count_output,
                "error_message": history.error_message,
                "created_at": history.created_at,
                "started_at": history.started_at,
                "completed_at": history.completed_at,
                "prompt_template": history.prompt_template,
                "prompt_variables": history.prompt_variables,
                "result": history.result,
                "processing_metadata": history.processing_metadata,
            }

            return WebResponseDTO.success_response(detail_data)

        except Exception as e:
            self.logger.error(f"Error getting history detail: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"履歴詳細の取得に失敗しました: {str(e)}"
            )
