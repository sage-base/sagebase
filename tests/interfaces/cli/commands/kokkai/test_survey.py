"""kokkai survey コマンドのテスト."""

from unittest.mock import AsyncMock, patch

import pytest

from click.testing import CliRunner

from src.infrastructure.external.kokkai_api.client import KokkaiApiClient
from src.infrastructure.external.kokkai_api.types import (
    MeetingListApiResponse,
    SpeechApiResponse,
)
from src.interfaces.cli.commands.kokkai.survey import _detect_latest_session, survey


_API_PATH = "src.infrastructure.external.kokkai_api.client.KokkaiApiClient"
_DETECT_PATH = "src.interfaces.cli.commands.kokkai.survey._detect_latest_session"


def _make_meeting_response(
    number_of_records: int,
) -> MeetingListApiResponse:
    return MeetingListApiResponse(
        number_of_records=number_of_records,
        number_of_return=0,
        start_record=1,
        next_record_position=None,
        meeting_record=[],
    )


def _make_speech_response(
    number_of_records: int,
) -> SpeechApiResponse:
    return SpeechApiResponse(
        number_of_records=number_of_records,
        number_of_return=0,
        start_record=1,
        next_record_position=None,
        speech_record=[],
    )


class TestSurveyCommand:
    @patch(_API_PATH)
    def test_survey_shows_results(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)
        mock_client_cls.return_value = mock_client
        mock_client.search_meetings = AsyncMock(return_value=_make_meeting_response(10))
        mock_client.search_speeches = AsyncMock(return_value=_make_speech_response(500))

        runner = CliRunner()
        result = runner.invoke(
            survey,
            ["--session-from", "1", "--session-to", "2", "--sleep", "0"],
        )

        assert result.exit_code == 0
        assert "合計" in result.output
        assert "20" in result.output
        assert "1,000" in result.output

    @patch(_API_PATH)
    def test_survey_with_name_of_house(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)
        mock_client_cls.return_value = mock_client
        mock_client.search_meetings = AsyncMock(return_value=_make_meeting_response(5))
        mock_client.search_speeches = AsyncMock(return_value=_make_speech_response(100))

        runner = CliRunner()
        result = runner.invoke(
            survey,
            [
                "--session-from",
                "1",
                "--session-to",
                "1",
                "--name-of-house",
                "衆議院",
                "--sleep",
                "0",
            ],
        )

        assert result.exit_code == 0
        assert "衆議院" in result.output
        mock_client.search_meetings.assert_called_with(
            session_from=1,
            session_to=1,
            name_of_house="衆議院",
            maximum_records=1,
        )

    @patch(_API_PATH)
    def test_survey_empty_session(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)
        mock_client_cls.return_value = mock_client
        mock_client.search_meetings = AsyncMock(return_value=_make_meeting_response(0))
        mock_client.search_speeches = AsyncMock(return_value=_make_speech_response(0))

        runner = CliRunner()
        result = runner.invoke(
            survey,
            ["--session-from", "999", "--session-to", "999", "--sleep", "0"],
        )

        assert result.exit_code == 0
        assert "合計" in result.output

    @patch(_DETECT_PATH)
    @patch(_API_PATH)
    def test_survey_auto_detects_latest_session(
        self, mock_client_cls: AsyncMock, mock_detect: AsyncMock
    ) -> None:
        mock_detect.return_value = 3
        mock_client = AsyncMock(spec=KokkaiApiClient)
        mock_client_cls.return_value = mock_client
        mock_client.search_meetings = AsyncMock(return_value=_make_meeting_response(5))
        mock_client.search_speeches = AsyncMock(return_value=_make_speech_response(100))

        runner = CliRunner()
        result = runner.invoke(survey, ["--session-from", "1", "--sleep", "0"])

        assert result.exit_code == 0
        mock_detect.assert_called_once()


class TestDetectLatestSession:
    @pytest.mark.asyncio
    async def test_finds_latest_session_in_middle(self) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)

        async def side_effect(
            *, session_from: int, session_to: int, maximum_records: int
        ) -> MeetingListApiResponse:
            if session_from <= 150:
                return _make_meeting_response(10)
            return _make_meeting_response(0)

        mock_client.search_meetings = AsyncMock(side_effect=side_effect)

        result = await _detect_latest_session(mock_client, sleep_interval=0)
        assert result == 150

    @pytest.mark.asyncio
    async def test_finds_latest_session_at_minimum(self) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)

        async def side_effect(
            *, session_from: int, session_to: int, maximum_records: int
        ) -> MeetingListApiResponse:
            if session_from == 1:
                return _make_meeting_response(5)
            return _make_meeting_response(0)

        mock_client.search_meetings = AsyncMock(side_effect=side_effect)

        result = await _detect_latest_session(mock_client, sleep_interval=0)
        assert result == 1

    @pytest.mark.asyncio
    async def test_finds_latest_session_at_maximum(self) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)
        mock_client.search_meetings = AsyncMock(return_value=_make_meeting_response(10))

        result = await _detect_latest_session(mock_client, sleep_interval=0)
        assert result == 220

    @pytest.mark.asyncio
    async def test_returns_1_when_no_sessions_exist(self) -> None:
        mock_client = AsyncMock(spec=KokkaiApiClient)
        mock_client.search_meetings = AsyncMock(return_value=_make_meeting_response(0))

        result = await _detect_latest_session(mock_client, sleep_interval=0)
        assert result == 1
