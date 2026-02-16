"""国会会議録検索システムAPIクライアントパッケージ."""

from .client import KokkaiApiClient
from .service import KokkaiSpeechServiceImpl
from .types import (
    MeetingListApiResponse,
    MeetingRecord,
    SpeechApiResponse,
    SpeechRecord,
)


__all__ = [
    "KokkaiApiClient",
    "KokkaiSpeechServiceImpl",
    "MeetingListApiResponse",
    "MeetingRecord",
    "SpeechApiResponse",
    "SpeechRecord",
]
