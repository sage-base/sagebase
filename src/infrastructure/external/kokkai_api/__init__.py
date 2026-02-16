"""国会会議録検索システムAPIクライアントパッケージ."""

from .client import KokkaiApiClient
from .types import (
    MeetingListApiResponse,
    MeetingRecord,
    SpeechApiResponse,
    SpeechRecord,
)


__all__ = [
    "KokkaiApiClient",
    "MeetingListApiResponse",
    "MeetingRecord",
    "SpeechApiResponse",
    "SpeechRecord",
]
