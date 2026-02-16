"""KokkaiSpeechServiceImpl のユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.external.kokkai_api.client import KokkaiApiClient
from src.infrastructure.external.kokkai_api.service import KokkaiSpeechServiceImpl
from src.infrastructure.external.kokkai_api.types import MeetingRecord


class TestFetchMeetings:
    """fetch_meetings のテスト."""

    @pytest.fixture()
    def mock_client(self) -> AsyncMock:
        return AsyncMock(spec=KokkaiApiClient)

    @pytest.fixture()
    def service(self, mock_client: AsyncMock) -> KokkaiSpeechServiceImpl:
        return KokkaiSpeechServiceImpl(client=mock_client)

    @pytest.mark.asyncio()
    async def test_converts_meeting_records_to_dtos(
        self, service: KokkaiSpeechServiceImpl, mock_client: AsyncMock
    ) -> None:
        """MeetingRecordがKokkaiMeetingDTOに変換される."""
        mock_client.get_all_meetings.return_value = [
            MeetingRecord(
                issue_id="121705253X00320250423",
                session=213,
                name_of_house="衆議院",
                name_of_meeting="本会議",
                issue="第3号",
                date="2025-04-23",
                meeting_url="https://kokkai.ndl.go.jp/meeting/1",
            )
        ]

        result = await service.fetch_meetings(
            name_of_house="衆議院", session_from=213, session_to=213
        )

        assert len(result) == 1
        dto = result[0]
        assert dto.issue_id == "121705253X00320250423"
        assert dto.session == 213
        assert dto.name_of_house == "衆議院"
        assert dto.name_of_meeting == "本会議"
        assert dto.issue == "第3号"
        assert dto.date == "2025-04-23"
        assert dto.meeting_url == "https://kokkai.ndl.go.jp/meeting/1"

    @pytest.mark.asyncio()
    async def test_passes_all_params_to_client(
        self, service: KokkaiSpeechServiceImpl, mock_client: AsyncMock
    ) -> None:
        """全パラメータがクライアントに正しく渡される."""
        mock_client.get_all_meetings.return_value = []

        await service.fetch_meetings(
            name_of_house="参議院",
            name_of_meeting="予算委員会",
            from_date="2025-01-01",
            until_date="2025-12-31",
            session_from=213,
            session_to=214,
        )

        mock_client.get_all_meetings.assert_called_once_with(
            name_of_house="参議院",
            name_of_meeting="予算委員会",
            from_date="2025-01-01",
            until_date="2025-12-31",
            session_from=213,
            session_to=214,
        )

    @pytest.mark.asyncio()
    async def test_empty_result(
        self, service: KokkaiSpeechServiceImpl, mock_client: AsyncMock
    ) -> None:
        """結果が空の場合は空リストを返す."""
        mock_client.get_all_meetings.return_value = []

        result = await service.fetch_meetings(session_from=999, session_to=999)

        assert result == []
