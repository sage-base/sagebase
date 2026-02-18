"""国会会議録API発言インポート関連のDTO."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class KokkaiSpeechDTO:
    """国会APIから取得した発言データのDTO.

    Infrastructure層のAPIレスポンス型からApplication層で扱う形に変換済みのデータ。
    """

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


@dataclass
class ImportKokkaiSpeechesInputDTO:
    """発言インポート入力DTO."""

    # 方法1: issueID指定（単一会議）
    issue_id: str | None = None
    # 方法2: 日付範囲 + 院名指定
    name_of_house: str | None = None
    from_date: str | None = None
    until_date: str | None = None


@dataclass
class ImportKokkaiSpeechesOutputDTO:
    """発言インポート出力DTO."""

    total_speeches_imported: int = 0
    total_speeches_skipped: int = 0
    total_meetings_created: int = 0
    total_speakers_created: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class KokkaiMeetingDTO:
    """国会APIから取得した会議データのDTO."""

    issue_id: str
    session: int
    name_of_house: str
    name_of_meeting: str
    issue: str
    date: str
    meeting_url: str


# バッチインポートの進捗コールバック型
# (処理済み件数, 全体件数, 現在処理中の会議名)
BatchProgressCallback = Callable[[int, int, str], None]


@dataclass
class SessionProgress:
    """回次ごとの進捗情報."""

    session: int
    meetings_processed: int = 0
    meetings_skipped: int = 0
    speeches_imported: int = 0
    speeches_skipped: int = 0


@dataclass(frozen=True)
class FailedMeetingInfo:
    """エラーが発生した会議の情報（後で再取得可能に）."""

    issue_id: str
    session: int
    name_of_house: str
    name_of_meeting: str
    date: str
    error_message: str


@dataclass
class BatchImportKokkaiSpeechesInputDTO:
    """バッチ発言インポート入力DTO."""

    # 検索条件
    name_of_house: str | None = None
    name_of_meeting: str | None = None
    from_date: str | None = None
    until_date: str | None = None
    session_from: int | None = None
    session_to: int | None = None
    # バッチ設定
    sleep_interval: float = 2.0


@dataclass
class BatchImportKokkaiSpeechesOutputDTO:
    """バッチ発言インポート出力DTO."""

    total_meetings_found: int = 0
    total_meetings_processed: int = 0
    total_meetings_skipped: int = 0
    total_speeches_imported: int = 0
    total_speeches_skipped: int = 0
    total_speakers_created: int = 0
    errors: list[str] = field(default_factory=list)
    session_progress: list[SessionProgress] = field(default_factory=list)
    failed_meetings: list[FailedMeetingInfo] = field(default_factory=list)
