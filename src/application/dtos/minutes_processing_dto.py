"""議事録処理関連のDTO"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProcessMinutesDTO:
    """議事録処理リクエストDTO"""

    meeting_id: int
    force_reprocess: bool = False
    pdf_url: str | None = None
    gcs_text_uri: str | None = None


@dataclass
class ExtractedSpeechDTO:
    """抽出された発言DTO"""

    speaker_name: str
    content: str
    sequence_number: int


@dataclass
class MinutesProcessingResultDTO:
    """議事録処理結果DTO"""

    minutes_id: int
    meeting_id: int
    total_conversations: int
    unique_speakers: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None
    role_name_mappings: dict[str, str] | None = None
