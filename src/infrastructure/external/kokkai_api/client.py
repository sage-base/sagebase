"""国会会議録検索システムAPIクライアント.

httpx asyncベースのHTTPクライアントで、/api/speech と /api/meeting_list
エンドポイントに対応。ページネーション自動ハンドリング付き。
"""

from __future__ import annotations

import logging

from typing import Any

import httpx

from .types import (
    MeetingListApiResponse,
    MeetingRecord,
    SpeechApiResponse,
    SpeechRecord,
)


logger = logging.getLogger(__name__)

# APIのキャメルケースとPython側のスネークケースのマッピング
_SPEECH_PARAM_MAP: dict[str, str] = {
    "name_of_house": "nameOfHouse",
    "name_of_meeting": "nameOfMeeting",
    "from_date": "from",
    "until_date": "until",
    "session_from": "sessionFrom",
    "session_to": "sessionTo",
    "speaker": "speaker",
    "any_keyword": "any",
    "maximum_records": "maximumRecords",
    "start_record": "startRecord",
    "issue_id": "issueID",
}

_MEETING_PARAM_MAP: dict[str, str] = {
    "name_of_house": "nameOfHouse",
    "name_of_meeting": "nameOfMeeting",
    "from_date": "from",
    "until_date": "until",
    "session_from": "sessionFrom",
    "session_to": "sessionTo",
    "maximum_records": "maximumRecords",
    "start_record": "startRecord",
}


class KokkaiApiError(Exception):
    """国会APIクライアントのエラー."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class KokkaiApiClient:
    """国会会議録検索システムAPIクライアント (httpx async)."""

    BASE_URL = "https://kokkai.ndl.go.jp/api"
    MAX_RECORDS_PER_REQUEST = 100

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._external_client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアントを取得（外部注入 or 自動生成）."""
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=30.0)

    async def search_speeches(
        self,
        *,
        name_of_house: str | None = None,
        name_of_meeting: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
        session_from: int | None = None,
        session_to: int | None = None,
        speaker: str | None = None,
        any_keyword: str | None = None,
        issue_id: str | None = None,
        maximum_records: int = 100,
        start_record: int = 1,
    ) -> SpeechApiResponse:
        """発言検索（1ページ分）."""
        params = self._build_params(
            _SPEECH_PARAM_MAP,
            name_of_house=name_of_house,
            name_of_meeting=name_of_meeting,
            from_date=from_date,
            until_date=until_date,
            session_from=session_from,
            session_to=session_to,
            speaker=speaker,
            any_keyword=any_keyword,
            issue_id=issue_id,
            maximum_records=maximum_records,
            start_record=start_record,
        )
        params["recordPacking"] = "json"

        data = await self._request("speech", params)
        return self._parse_speech_response(data)

    async def get_all_speeches(
        self,
        *,
        name_of_house: str | None = None,
        name_of_meeting: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
        session_from: int | None = None,
        session_to: int | None = None,
        speaker: str | None = None,
        any_keyword: str | None = None,
        issue_id: str | None = None,
    ) -> list[SpeechRecord]:
        """全件取得（ページネーション自動ハンドリング）."""
        all_records: list[SpeechRecord] = []
        start = 1

        while True:
            response = await self.search_speeches(
                name_of_house=name_of_house,
                name_of_meeting=name_of_meeting,
                from_date=from_date,
                until_date=until_date,
                session_from=session_from,
                session_to=session_to,
                speaker=speaker,
                any_keyword=any_keyword,
                issue_id=issue_id,
                start_record=start,
            )
            all_records.extend(response.speech_record)

            if (
                response.next_record_position is None
                or response.next_record_position == 0
            ):
                break

            start = response.next_record_position
            logger.info(
                "ページネーション: %d/%d件取得済み",
                len(all_records),
                response.number_of_records,
            )

        return all_records

    async def search_meetings(
        self,
        *,
        name_of_house: str | None = None,
        name_of_meeting: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
        session_from: int | None = None,
        session_to: int | None = None,
        maximum_records: int = 100,
        start_record: int = 1,
    ) -> MeetingListApiResponse:
        """会議一覧検索（1ページ分）."""
        params = self._build_params(
            _MEETING_PARAM_MAP,
            name_of_house=name_of_house,
            name_of_meeting=name_of_meeting,
            from_date=from_date,
            until_date=until_date,
            session_from=session_from,
            session_to=session_to,
            maximum_records=maximum_records,
            start_record=start_record,
        )
        params["recordPacking"] = "json"

        data = await self._request("meeting_list", params)
        return self._parse_meeting_response(data)

    async def get_all_meetings(
        self,
        *,
        name_of_house: str | None = None,
        name_of_meeting: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
        session_from: int | None = None,
        session_to: int | None = None,
    ) -> list[MeetingRecord]:
        """会議一覧全件取得（ページネーション自動ハンドリング）."""
        all_records: list[MeetingRecord] = []
        start = 1

        while True:
            response = await self.search_meetings(
                name_of_house=name_of_house,
                name_of_meeting=name_of_meeting,
                from_date=from_date,
                until_date=until_date,
                session_from=session_from,
                session_to=session_to,
                start_record=start,
            )
            all_records.extend(response.meeting_record)

            if (
                response.next_record_position is None
                or response.next_record_position == 0
            ):
                break

            start = response.next_record_position

        return all_records

    async def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """APIリクエスト実行."""
        url = f"{self.BASE_URL}/{endpoint}"
        client = await self._get_client()

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except httpx.HTTPStatusError as e:
            raise KokkaiApiError(
                f"APIリクエストエラー: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except httpx.TimeoutException as e:
            raise KokkaiApiError("APIリクエストタイムアウト") from e
        except httpx.HTTPError as e:
            raise KokkaiApiError(f"HTTPエラー: {e}") from e
        finally:
            if self._owns_client:
                await client.aclose()

    @staticmethod
    def _build_params(param_map: dict[str, str], **kwargs: Any) -> dict[str, Any]:
        """スネークケースのkwargsをAPIパラメータに変換."""
        params: dict[str, Any] = {}
        for py_name, api_name in param_map.items():
            value = kwargs.get(py_name)
            if value is not None:
                params[api_name] = value
        return params

    @staticmethod
    def _parse_speech_response(data: dict[str, Any]) -> SpeechApiResponse:
        """APIレスポンスJSONをSpeechApiResponseに変換."""
        raw_records = data.get("speechRecord") or []
        records = [
            SpeechRecord(
                speech_id=r.get("speechID", ""),
                issue_id=r.get("issueID", ""),
                session=int(r.get("session", 0)),
                name_of_house=r.get("nameOfHouse", ""),
                name_of_meeting=r.get("nameOfMeeting", ""),
                issue=r.get("issue", ""),
                date=r.get("date", ""),
                speech_order=int(r.get("speechOrder", 0)),
                speaker=r.get("speaker", ""),
                speaker_yomi=r.get("speakerYomi", ""),
                speech=r.get("speech", ""),
                speech_url=r.get("speechURL", ""),
                meeting_url=r.get("meetingURL", ""),
                pdf_url=r.get("pdfURL", ""),
            )
            for r in raw_records
        ]

        return SpeechApiResponse(
            number_of_records=int(data.get("numberOfRecords", 0)),
            number_of_return=int(data.get("numberOfReturn", 0)),
            start_record=int(data.get("startRecord", 1)),
            next_record_position=_parse_optional_int(data.get("nextRecordPosition")),
            speech_record=records,
        )

    @staticmethod
    def _parse_meeting_response(data: dict[str, Any]) -> MeetingListApiResponse:
        """APIレスポンスJSONをMeetingListApiResponseに変換."""
        raw_records = data.get("meetingRecord") or []
        records = [
            MeetingRecord(
                issue_id=r.get("issueID", ""),
                session=int(r.get("session", 0)),
                name_of_house=r.get("nameOfHouse", ""),
                name_of_meeting=r.get("nameOfMeeting", ""),
                issue=r.get("issue", ""),
                date=r.get("date", ""),
                meeting_url=r.get("meetingURL", ""),
                pdf_url=r.get("pdfURL"),
            )
            for r in raw_records
        ]

        return MeetingListApiResponse(
            number_of_records=int(data.get("numberOfRecords", 0)),
            number_of_return=int(data.get("numberOfReturn", 0)),
            start_record=int(data.get("startRecord", 1)),
            next_record_position=_parse_optional_int(data.get("nextRecordPosition")),
            meeting_record=records,
        )


def _parse_optional_int(value: Any) -> int | None:
    """値をint | Noneに変換."""
    if value is None or value == "":
        return None
    try:
        result = int(value)
        return result if result > 0 else None
    except (ValueError, TypeError):
        return None
