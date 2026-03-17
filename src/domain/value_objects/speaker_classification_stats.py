"""Speaker分類統計を表すValue Object."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ClassificationCount:
    """分類別の件数を表すValue Object."""

    speaker_count: int
    conversation_count: int


@dataclass(frozen=True)
class SpeakerClassificationStats:
    """Speaker分類統計のValue Object.

    politician_id / government_official_id の有無に基づく
    Speaker分類別の件数と発言数、身元特定率を保持する。

    total_speakers, total_conversations, identity_rate は
    3分類の値から導出されるプロパティ。
    """

    politician_linked: ClassificationCount
    government_official_linked: ClassificationCount
    unclassified: ClassificationCount

    @property
    def total_speakers(self) -> int:
        """全Speaker数."""
        return (
            self.politician_linked.speaker_count
            + self.government_official_linked.speaker_count
            + self.unclassified.speaker_count
        )

    @property
    def total_conversations(self) -> int:
        """全発言数."""
        return (
            self.politician_linked.conversation_count
            + self.government_official_linked.conversation_count
            + self.unclassified.conversation_count
        )

    @property
    def identity_rate(self) -> float:
        """身元特定率（発言ベース）を算出する.

        (politician + government_official)の発言数 / 全発言数 * 100
        """
        if self.total_conversations == 0:
            return 0.0
        identified = (
            self.politician_linked.conversation_count
            + self.government_official_linked.conversation_count
        )
        return identified / self.total_conversations * 100

    def to_dict(self) -> dict[str, Any]:
        """プロパティを含む完全な辞書表現を返す."""
        result = asdict(self)
        result["total_speakers"] = self.total_speakers
        result["total_conversations"] = self.total_conversations
        result["identity_rate"] = self.identity_rate
        return result

    @classmethod
    def from_classification_rows(
        cls, rows: dict[str, dict[str, int]]
    ) -> "SpeakerClassificationStats":
        """分類別集計結果からインスタンスを生成する.

        Args:
            rows: 分類名をキー、speaker_count/conversation_countを値とする辞書
        """
        politician = rows.get(
            "politician", {"speaker_count": 0, "conversation_count": 0}
        )
        government_official = rows.get(
            "government_official", {"speaker_count": 0, "conversation_count": 0}
        )
        unclassified = rows.get(
            "unclassified", {"speaker_count": 0, "conversation_count": 0}
        )

        return cls(
            politician_linked=ClassificationCount(**politician),
            government_official_linked=ClassificationCount(**government_official),
            unclassified=ClassificationCount(**unclassified),
        )
