"""国会会議録APIからの発言バッチインポートユースケース.

meeting_list APIで対象会議を列挙し、各会議の発言を一括インポートする。
"""

from __future__ import annotations

import asyncio
import logging

from src.application.dtos.kokkai_speech_dto import (
    BatchImportKokkaiSpeechesInputDTO,
    BatchImportKokkaiSpeechesOutputDTO,
    BatchProgressCallback,
    ImportKokkaiSpeechesInputDTO,
    KokkaiMeetingDTO,
)
from src.application.usecases.import_kokkai_speeches_usecase import (
    ImportKokkaiSpeechesUseCase,
)
from src.domain.services.interfaces.kokkai_speech_service import IKokkaiSpeechService


logger = logging.getLogger(__name__)


class BatchImportKokkaiSpeechesUseCase:
    """meeting_list APIで対象会議を列挙し、各会議の発言を一括インポートする."""

    def __init__(
        self,
        kokkai_speech_service: IKokkaiSpeechService,
        import_usecase: ImportKokkaiSpeechesUseCase,
    ) -> None:
        self._speech_service = kokkai_speech_service
        self._import_usecase = import_usecase

    async def fetch_target_meetings(
        self, input_dto: BatchImportKokkaiSpeechesInputDTO
    ) -> list[KokkaiMeetingDTO]:
        """対象会議の列挙（プレビュー用）."""
        return await self._speech_service.fetch_meetings(
            name_of_house=input_dto.name_of_house,
            name_of_meeting=input_dto.name_of_meeting,
            from_date=input_dto.from_date,
            until_date=input_dto.until_date,
            session_from=input_dto.session_from,
            session_to=input_dto.session_to,
        )

    async def execute(
        self,
        input_dto: BatchImportKokkaiSpeechesInputDTO,
        progress_callback: BatchProgressCallback | None = None,
    ) -> BatchImportKokkaiSpeechesOutputDTO:
        """バッチインポート実行.

        1. meeting_list APIで対象会議を列挙
        2. 各会議に対してImportKokkaiSpeechesUseCaseを呼出
        3. 個別エラーは記録して続行
        """
        output = BatchImportKokkaiSpeechesOutputDTO()

        # 1. 対象会議を列挙
        meetings = await self.fetch_target_meetings(input_dto)
        output.total_meetings_found = len(meetings)

        if not meetings:
            logger.info("対象会議が見つかりません")
            return output

        logger.info("バッチインポート開始: %d 件の会議を処理します", len(meetings))

        # 2. 各会議を処理
        for i, meeting in enumerate(meetings):
            meeting_label = (
                f"{meeting.name_of_house}{meeting.name_of_meeting}"
                f" {meeting.issue} ({meeting.date})"
            )

            if progress_callback:
                progress_callback(i, len(meetings), meeting_label)

            try:
                single_input = ImportKokkaiSpeechesInputDTO(
                    issue_id=meeting.issue_id,
                )
                result = await self._import_usecase.execute(single_input)

                # 結果を集約
                output.total_speeches_imported += result.total_speeches_imported
                output.total_speeches_skipped += result.total_speeches_skipped
                output.total_speakers_created += result.total_speakers_created
                output.total_meetings_processed += 1

                if (
                    result.total_speeches_skipped > 0
                    and result.total_speeches_imported == 0
                ):
                    output.total_meetings_skipped += 1

                if result.errors:
                    output.errors.extend(result.errors)

            except Exception as e:
                error_msg = f"会議 {meeting_label} の処理中にエラー: {e}"
                logger.exception(error_msg)
                output.errors.append(error_msg)

            # API負荷軽減のためスリープ
            if i < len(meetings) - 1 and input_dto.sleep_interval > 0:
                await asyncio.sleep(input_dto.sleep_interval)

        # 完了通知
        if progress_callback:
            progress_callback(len(meetings), len(meetings), "完了")

        logger.info(
            "バッチインポート完了: %d会議処理, %d件インポート, %d件スキップ, %dエラー",
            output.total_meetings_processed,
            output.total_speeches_imported,
            output.total_speeches_skipped,
            len(output.errors),
        )
        return output
