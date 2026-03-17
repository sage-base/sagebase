"""Speaker分類統計を表すValue Object."""

from dataclasses import dataclass


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
    """

    total_speakers: int
    total_conversations: int
    politician_linked: ClassificationCount
    government_official_linked: ClassificationCount
    unclassified: ClassificationCount

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

        politician_count = ClassificationCount(**politician)
        government_official_count = ClassificationCount(**government_official)
        unclassified_count = ClassificationCount(**unclassified)

        total_speakers = (
            politician_count.speaker_count
            + government_official_count.speaker_count
            + unclassified_count.speaker_count
        )
        total_conversations = (
            politician_count.conversation_count
            + government_official_count.conversation_count
            + unclassified_count.conversation_count
        )

        return cls(
            total_speakers=total_speakers,
            total_conversations=total_conversations,
            politician_linked=politician_count,
            government_official_linked=government_official_count,
            unclassified=unclassified_count,
        )
