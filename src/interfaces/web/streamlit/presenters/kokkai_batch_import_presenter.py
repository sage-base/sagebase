"""国会発言バッチ取得のPresenter."""

from __future__ import annotations

from typing import Any

from src.application.dtos.kokkai_speech_dto import (
    BatchImportKokkaiSpeechesInputDTO,
    BatchImportKokkaiSpeechesOutputDTO,
    ImportKokkaiSpeechesInputDTO,
    ImportKokkaiSpeechesOutputDTO,
    KokkaiMeetingDTO,
)
from src.common.logging import get_logger
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.base import BasePresenter


logger = get_logger(__name__)


class KokkaiBatchImportPresenter(BasePresenter[list[KokkaiMeetingDTO]]):
    """国会発言バッチ取得のPresenter."""

    def __init__(self, container: Container | None = None) -> None:
        super().__init__(container)
        self._batch_usecase = (
            self.container.use_cases.batch_import_kokkai_speeches_usecase()
        )
        self._import_usecase = self.container.use_cases.import_kokkai_speeches_usecase()

    def load_data(self) -> list[KokkaiMeetingDTO]:
        """未使用（BasePresenter抽象メソッドの実装）."""
        return []

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """未使用（BasePresenter抽象メソッドの実装）."""
        return None

    def fetch_meetings(
        self,
        input_dto: BatchImportKokkaiSpeechesInputDTO,
    ) -> list[KokkaiMeetingDTO]:
        """対象会議の列挙（プレビュー用）."""
        return self._run_async(self._batch_usecase.fetch_target_meetings(input_dto))

    def import_single_meeting(self, issue_id: str) -> ImportKokkaiSpeechesOutputDTO:
        """単一会議のインポート."""
        input_dto = ImportKokkaiSpeechesInputDTO(issue_id=issue_id)
        return self._run_async(self._import_usecase.execute(input_dto))

    def execute_batch_import(
        self,
        input_dto: BatchImportKokkaiSpeechesInputDTO,
    ) -> BatchImportKokkaiSpeechesOutputDTO:
        """バッチインポート全体を実行（進捗管理なし）."""
        return self._run_async(self._batch_usecase.execute(input_dto))
