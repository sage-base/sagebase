"""IKokkaiSpeechService のインフラストラクチャ実装.

KokkaiApiClient をラップし、APIレスポンスをApplication DTOに変換する。
"""

from __future__ import annotations

from src.application.dtos.kokkai_speech_dto import KokkaiMeetingDTO, KokkaiSpeechDTO
from src.infrastructure.external.kokkai_api.client import KokkaiApiClient
from src.infrastructure.external.kokkai_api.types import MeetingRecord, SpeechRecord


class KokkaiSpeechServiceImpl:
    """IKokkaiSpeechService の具象実装."""

    def __init__(self, client: KokkaiApiClient | None = None) -> None:
        self._client = client or KokkaiApiClient()

    async def fetch_speeches(
        self,
        *,
        issue_id: str | None = None,
        name_of_house: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
    ) -> list[KokkaiSpeechDTO]:
        """発言データを取得しDTOに変換して返す."""
        if issue_id:
            records = await self._client.get_all_speeches(issue_id=issue_id)
        elif name_of_house and from_date and until_date:
            records = await self._client.get_all_speeches(
                name_of_house=name_of_house,
                from_date=from_date,
                until_date=until_date,
            )
        else:
            return []

        return [self._to_dto(r) for r in records]

    async def fetch_meetings(
        self,
        *,
        name_of_house: str | None = None,
        name_of_meeting: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
        session_from: int | None = None,
        session_to: int | None = None,
    ) -> list[KokkaiMeetingDTO]:
        """会議一覧を取得しDTOに変換して返す."""
        records = await self._client.get_all_meetings(
            name_of_house=name_of_house,
            name_of_meeting=name_of_meeting,
            from_date=from_date,
            until_date=until_date,
            session_from=session_from,
            session_to=session_to,
        )
        return [self._meeting_to_dto(r) for r in records]

    @staticmethod
    def _meeting_to_dto(record: MeetingRecord) -> KokkaiMeetingDTO:
        """MeetingRecord → KokkaiMeetingDTO 変換."""
        return KokkaiMeetingDTO(
            issue_id=record.issue_id,
            session=record.session,
            name_of_house=record.name_of_house,
            name_of_meeting=record.name_of_meeting,
            issue=record.issue,
            date=record.date,
            meeting_url=record.meeting_url,
        )

    @staticmethod
    def _to_dto(record: SpeechRecord) -> KokkaiSpeechDTO:
        """APIレスポンス型をApplication DTOに変換."""
        return KokkaiSpeechDTO(
            speech_id=record.speech_id,
            issue_id=record.issue_id,
            session=record.session,
            name_of_house=record.name_of_house,
            name_of_meeting=record.name_of_meeting,
            issue=record.issue,
            date=record.date,
            speech_order=record.speech_order,
            speaker=record.speaker,
            speaker_yomi=record.speaker_yomi,
            speech=record.speech,
            speech_url=record.speech_url,
            meeting_url=record.meeting_url,
            pdf_url=record.pdf_url,
        )
