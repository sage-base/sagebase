"""国会会議録API発言インポート関連のDTO."""

from __future__ import annotations

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
