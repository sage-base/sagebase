"""KokkaiApiClient のユニットテスト."""

import httpx
import pytest

from src.infrastructure.external.kokkai_api.client import (
    KokkaiApiClient,
    KokkaiApiError,
)


def _make_speech_response(
    records: list[dict],
    total: int | None = None,
    next_pos: int | None = None,
) -> dict:
    """テスト用の発言APIレスポンスを生成."""
    return {
        "numberOfRecords": total or len(records),
        "numberOfReturn": len(records),
        "startRecord": 1,
        "nextRecordPosition": next_pos,
        "speechRecord": records,
    }


def _make_speech_record(**overrides: object) -> dict:
    """テスト用の発言レコードを生成."""
    defaults = {
        "speechID": "121705253X00320250423001",
        "issueID": "121705253X00320250423",
        "session": 213,
        "nameOfHouse": "衆議院",
        "nameOfMeeting": "本会議",
        "issue": "第3号",
        "date": "2025-04-23",
        "speechOrder": 1,
        "speaker": "岸田文雄君",
        "speakerYomi": "きしだふみおくん",
        "speech": "テスト発言内容です。",
        "speechURL": "https://kokkai.ndl.go.jp/...",
        "meetingURL": "https://kokkai.ndl.go.jp/...",
        "pdfURL": "https://kokkai.ndl.go.jp/...",
    }
    defaults.update(overrides)
    return defaults


def _make_meeting_response(
    records: list[dict],
    total: int | None = None,
    next_pos: int | None = None,
) -> dict:
    """テスト用の会議一覧APIレスポンスを生成."""
    return {
        "numberOfRecords": total or len(records),
        "numberOfReturn": len(records),
        "startRecord": 1,
        "nextRecordPosition": next_pos,
        "meetingRecord": records,
    }


def _make_meeting_record(**overrides: object) -> dict:
    """テスト用の会議レコードを生成."""
    defaults = {
        "issueID": "121705253X00320250423",
        "session": 213,
        "nameOfHouse": "衆議院",
        "nameOfMeeting": "本会議",
        "issue": "第3号",
        "date": "2025-04-23",
        "meetingURL": "https://kokkai.ndl.go.jp/...",
        "pdfURL": "https://kokkai.ndl.go.jp/...",
    }
    defaults.update(overrides)
    return defaults


class TestSearchSpeeches:
    """search_speeches メソッドのテスト."""

    @pytest.mark.asyncio
    async def test_parse_normal_response(self) -> None:
        record = _make_speech_record()
        response_json = _make_speech_response([record])

        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json=response_json)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            result = await api.search_speeches(name_of_house="衆議院")

        assert result.number_of_records == 1
        assert len(result.speech_record) == 1
        assert result.speech_record[0].speech_id == "121705253X00320250423001"
        assert result.speech_record[0].name_of_house == "衆議院"
        assert result.speech_record[0].speech_order == 1
        assert result.speech_record[0].speaker == "岸田文雄君"

    @pytest.mark.asyncio
    async def test_params_converted_to_camel_case(self) -> None:
        captured_params: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json=_make_speech_response([]))

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            await api.search_speeches(
                name_of_house="参議院",
                from_date="2025-01-01",
                until_date="2025-12-31",
                maximum_records=50,
            )

        assert captured_params["nameOfHouse"] == "参議院"
        assert captured_params["from"] == "2025-01-01"
        assert captured_params["until"] == "2025-12-31"
        assert captured_params["maximumRecords"] == "50"
        assert captured_params["recordPacking"] == "json"

    @pytest.mark.asyncio
    async def test_none_params_not_sent(self) -> None:
        captured_params: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(200, json=_make_speech_response([]))

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            await api.search_speeches(name_of_house="衆議院")

        assert "from" not in captured_params
        assert "speaker" not in captured_params

    @pytest.mark.asyncio
    async def test_parse_empty_response(self) -> None:
        response_json = _make_speech_response([])

        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json=response_json)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            result = await api.search_speeches(name_of_house="衆議院")

        assert result.number_of_records == 0
        assert len(result.speech_record) == 0

    @pytest.mark.asyncio
    async def test_search_by_issue_id(self) -> None:
        captured_params: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(
                200, json=_make_speech_response([_make_speech_record()])
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            await api.search_speeches(issue_id="121705253X00320250423")

        assert captured_params["issueID"] == "121705253X00320250423"


class TestGetAllSpeeches:
    """get_all_speeches ページネーションのテスト."""

    @pytest.mark.asyncio
    async def test_auto_paginate_multiple_pages(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            start = int(request.url.params.get("startRecord", "1"))

            if start == 1:
                return httpx.Response(
                    200,
                    json=_make_speech_response(
                        [_make_speech_record(speechOrder=1)],
                        total=2,
                        next_pos=2,
                    ),
                )
            else:
                return httpx.Response(
                    200,
                    json=_make_speech_response(
                        [_make_speech_record(speechOrder=2)],
                        total=2,
                        next_pos=None,
                    ),
                )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            records = await api.get_all_speeches(name_of_house="衆議院")

        assert len(records) == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_single_page_no_loop(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                200,
                json=_make_speech_response(
                    [_make_speech_record()], total=1, next_pos=None
                ),
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            records = await api.get_all_speeches(name_of_house="衆議院")

        assert len(records) == 1
        assert call_count == 1


class TestSearchMeetings:
    """search_meetings メソッドのテスト."""

    @pytest.mark.asyncio
    async def test_parse_normal_response(self) -> None:
        record = _make_meeting_record()
        response_json = _make_meeting_response([record])

        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json=response_json)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client)
            result = await api.search_meetings(name_of_house="衆議院")

        assert result.number_of_records == 1
        assert len(result.meeting_record) == 1
        assert result.meeting_record[0].issue_id == "121705253X00320250423"


class TestErrorHandling:
    """エラーハンドリングのテスト（リトライ無効で高速化）."""

    @pytest.mark.asyncio
    async def test_handle_http_status_error(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(500, text="Internal Server Error")
        )
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client, max_retries=0)
            with pytest.raises(KokkaiApiError) as exc_info:
                await api.search_speeches(name_of_house="衆議院")

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_handle_404_error(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(404, text="Not Found")
        )
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client, max_retries=0)
            with pytest.raises(KokkaiApiError) as exc_info:
                await api.search_speeches(name_of_house="衆議院")

        assert exc_info.value.status_code == 404


class TestRetry:
    """リトライロジックのテスト."""

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self) -> None:
        """500→500→200 で最終的に成功."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return httpx.Response(500, text="Internal Server Error")
            return httpx.Response(
                200, json=_make_speech_response([_make_speech_record()])
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client, max_retries=3)
            result = await api.search_speeches(name_of_house="衆議院")

        assert call_count == 3
        assert result.number_of_records == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self) -> None:
        """400が即座にKokkaiApiErrorを送出（リトライしない）."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(400, text="Bad Request")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client, max_retries=3)
            with pytest.raises(KokkaiApiError) as exc_info:
                await api.search_speeches(name_of_house="衆議院")

        assert call_count == 1
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        """タイムアウト→200 で成功."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ReadTimeout("read timeout")
            return httpx.Response(
                200, json=_make_speech_response([_make_speech_record()])
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client, max_retries=3)
            result = await api.search_speeches(name_of_house="衆議院")

        assert call_count == 2
        assert result.number_of_records == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted(self) -> None:
        """500が4回続くとKokkaiApiErrorを送出."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, text="Internal Server Error")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            api = KokkaiApiClient(client=client, max_retries=3)
            with pytest.raises(KokkaiApiError) as exc_info:
                await api.search_speeches(name_of_house="衆議院")

        assert call_count == 4  # 初回 + 3回リトライ
        assert exc_info.value.status_code == 500
