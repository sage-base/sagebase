"""SpeakerClassificationStats Value Objectのテスト."""

import pytest

from src.domain.value_objects.speaker_classification_stats import (
    ClassificationCount,
    SpeakerClassificationStats,
)


class TestSpeakerClassificationStats:
    """SpeakerClassificationStatsのテスト."""

    def test_identity_rate_normal(self) -> None:
        """正常系: 身元特定率が正しく計算される."""
        stats = SpeakerClassificationStats(
            total_speakers=1000,
            total_conversations=50000,
            politician_linked=ClassificationCount(
                speaker_count=200, conversation_count=40000
            ),
            government_official_linked=ClassificationCount(
                speaker_count=10, conversation_count=500
            ),
            unclassified=ClassificationCount(
                speaker_count=790, conversation_count=9500
            ),
        )

        assert stats.identity_rate == pytest.approx(81.0)

    def test_identity_rate_zero_conversations(self) -> None:
        """発言0件時にidentity_rateが0.0."""
        stats = SpeakerClassificationStats(
            total_speakers=10,
            total_conversations=0,
            politician_linked=ClassificationCount(
                speaker_count=0, conversation_count=0
            ),
            government_official_linked=ClassificationCount(
                speaker_count=0, conversation_count=0
            ),
            unclassified=ClassificationCount(speaker_count=10, conversation_count=0),
        )

        assert stats.identity_rate == 0.0

    def test_from_classification_rows_all_classifications(self) -> None:
        """全分類が揃っている場合のファクトリメソッド."""
        rows = {
            "politician": {"speaker_count": 100, "conversation_count": 5000},
            "government_official": {"speaker_count": 5, "conversation_count": 200},
            "unclassified": {"speaker_count": 400, "conversation_count": 3000},
        }

        stats = SpeakerClassificationStats.from_classification_rows(rows)

        assert stats.total_speakers == 505
        assert stats.total_conversations == 8200
        assert stats.politician_linked.speaker_count == 100
        assert stats.government_official_linked.speaker_count == 5
        assert stats.unclassified.speaker_count == 400

    def test_from_classification_rows_partial(self) -> None:
        """一部分類のみ存在する場合、残りは0でデフォルト."""
        rows = {
            "politician": {"speaker_count": 50, "conversation_count": 1000},
        }

        stats = SpeakerClassificationStats.from_classification_rows(rows)

        assert stats.total_speakers == 50
        assert stats.politician_linked.speaker_count == 50
        assert stats.government_official_linked.speaker_count == 0
        assert stats.unclassified.speaker_count == 0

    def test_from_classification_rows_empty(self) -> None:
        """空の辞書の場合、全て0."""
        stats = SpeakerClassificationStats.from_classification_rows({})

        assert stats.total_speakers == 0
        assert stats.total_conversations == 0
        assert stats.identity_rate == 0.0

    def test_frozen_dataclass(self) -> None:
        """frozenであること（イミュータブル）."""
        stats = SpeakerClassificationStats(
            total_speakers=10,
            total_conversations=100,
            politician_linked=ClassificationCount(
                speaker_count=5, conversation_count=50
            ),
            government_official_linked=ClassificationCount(
                speaker_count=0, conversation_count=0
            ),
            unclassified=ClassificationCount(speaker_count=5, conversation_count=50),
        )

        with pytest.raises(AttributeError):
            stats.total_speakers = 999  # type: ignore[misc]
