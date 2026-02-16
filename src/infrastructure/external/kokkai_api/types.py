"""国会会議録検索システムAPIのレスポンス型定義."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpeechRecord:
    """発言検索APIレスポンスの個別レコード."""

    speech_id: str
    issue_id: str
    session: int
    name_of_house: str
    name_of_meeting: str
    issue: str
    date: str
    speech_order: int
    speaker: str
    speaker_yomi: str
    speech: str
    speech_url: str
    meeting_url: str
    pdf_url: str


@dataclass(frozen=True)
class MeetingRecord:
    """会議一覧APIレスポンスの個別レコード."""

    issue_id: str
    session: int
    name_of_house: str
    name_of_meeting: str
    issue: str
    date: str
    meeting_url: str
    pdf_url: str | None = None


@dataclass(frozen=True)
class SpeechApiResponse:
    """発言検索APIのレスポンス全体."""

    number_of_records: int
    number_of_return: int
    start_record: int
    next_record_position: int | None
    speech_record: list[SpeechRecord] = field(default_factory=list)


@dataclass(frozen=True)
class MeetingListApiResponse:
    """会議一覧APIのレスポンス全体."""

    number_of_records: int
    number_of_return: int
    start_record: int
    next_record_position: int | None
    meeting_record: list[MeetingRecord] = field(default_factory=list)
