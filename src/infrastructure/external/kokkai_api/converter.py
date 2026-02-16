"""国会APIレスポンスをドメインエンティティに変換するコンバーター.

純粋な変換ロジックのみ担当。Conference解決などDB操作を伴う処理は
ユースケース側で行う。
"""

from __future__ import annotations

import re

from .types import SpeechRecord

from src.domain.entities.conversation import Conversation
from src.domain.entities.speaker import Speaker


# 発言者名末尾の敬称パターン
_HONORIFIC_PATTERN = re.compile(r"(君|くん|さん|殿|氏)$")


class KokkaiSpeechConverter:
    """国会APIレスポンスの純粋変換ロジック."""

    @staticmethod
    def normalize_speaker_name(name: str) -> str:
        """発言者名を正規化する.

        末尾の「君」「さん」等の敬称を除去し、全角/半角スペースをトリムする。
        """
        normalized = name.strip()
        normalized = _HONORIFIC_PATTERN.sub("", normalized)
        return normalized.strip()

    @staticmethod
    def build_conference_name(name_of_house: str, name_of_meeting: str) -> str:
        """院名 + 会議名から Conference name を構築する.

        例: "衆議院" + "本会議" → "衆議院本会議"
        """
        return f"{name_of_house}{name_of_meeting}"

    @staticmethod
    def speech_to_conversation(
        speech: SpeechRecord,
        minutes_id: int,
        speaker_id: int | None = None,
    ) -> Conversation:
        """speechRecord → Conversation エンティティに変換する.

        公式データのため is_manually_verified=True で Gold 層に直接格納。
        """
        speaker_name = KokkaiSpeechConverter.normalize_speaker_name(speech.speaker)
        return Conversation(
            comment=speech.speech,
            sequence_number=speech.speech_order,
            minutes_id=minutes_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            is_manually_verified=True,
        )

    @staticmethod
    def speech_to_speaker(speech: SpeechRecord) -> Speaker:
        """speechRecord → Speaker エンティティに変換する.

        発言者名と読みがなの敬称を除去して保存。
        """
        name = KokkaiSpeechConverter.normalize_speaker_name(speech.speaker)
        name_yomi = KokkaiSpeechConverter.normalize_speaker_name(speech.speaker_yomi)
        return Speaker(
            name=name,
            name_yomi=name_yomi if name_yomi else None,
        )

    @staticmethod
    def build_meeting_name(session: int, issue: str) -> str:
        """会議名を構築する.

        例: session=213, issue="第3号" → "第213回国会 第3号"
        """
        return f"第{session}回国会 {issue}"
