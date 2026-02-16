"""国会会議録API発言取得サービスのインターフェース."""

from __future__ import annotations

from typing import Protocol

from src.application.dtos.kokkai_speech_dto import KokkaiMeetingDTO, KokkaiSpeechDTO


class IKokkaiSpeechService(Protocol):
    """国会会議録APIから発言データを取得するサービスのインターフェース."""

    async def fetch_speeches(
        self,
        *,
        issue_id: str | None = None,
        name_of_house: str | None = None,
        from_date: str | None = None,
        until_date: str | None = None,
    ) -> list[KokkaiSpeechDTO]:
        """発言データを取得する.

        issue_id 指定時は単一会議の全発言を取得。
        name_of_house + from_date + until_date 指定時は日付範囲で取得。
        """
        ...

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
        """会議一覧を取得する.

        回次範囲または日付範囲で対象会議を列挙する。
        """
        ...
