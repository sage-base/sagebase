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

    def test_total_speakers_derived(self) -> None:
        """total_speakersが3分類の合計として導出される."""
        stats = SpeakerClassificationStats(
            politician_linked=ClassificationCount(
                speaker_count=100, conversation_count=0
            ),
            government_official_linked=ClassificationCount(
                speaker_count=20, conversation_count=0
            ),
            unclassified=ClassificationCount(speaker_count=30, conversation_count=0),
        )

        assert stats.total_speakers == 150

    def test_total_conversations_derived(self) -> None:
        """total_conversationsが3分類の合計として導出される."""
        stats = SpeakerClassificationStats(
            politician_linked=ClassificationCount(
                speaker_count=0, conversation_count=5000
            ),
            government_official_linked=ClassificationCount(
                speaker_count=0, conversation_count=200
            ),
            unclassified=ClassificationCount(speaker_count=0, conversation_count=800),
        )

        assert stats.total_conversations == 6000

    def test_identity_rate_zero_conversations(self) -> None:
        """発言0件時にidentity_rateが0.0."""
        stats = SpeakerClassificationStats(
            politician_linked=ClassificationCount(
                speaker_count=0, conversation_count=0
            ),
            government_official_linked=ClassificationCount(
                speaker_count=0, conversation_count=0
            ),
            unclassified=ClassificationCount(speaker_count=10, conversation_count=0),
        )

        assert stats.identity_rate == 0.0

    def test_to_dict_includes_properties(self) -> None:
        """to_dict()がプロパティを含む完全な辞書を返す."""
        stats = SpeakerClassificationStats(
            politician_linked=ClassificationCount(
                speaker_count=100, conversation_count=5000
            ),
            government_official_linked=ClassificationCount(
                speaker_count=5, conversation_count=200
            ),
            unclassified=ClassificationCount(
                speaker_count=400, conversation_count=3000
            ),
        )

        result = stats.to_dict()

        assert result["total_speakers"] == 505
        assert result["total_conversations"] == 8200
        assert result["identity_rate"] == pytest.approx(63.41, abs=0.01)
        assert result["politician_linked"]["speaker_count"] == 100

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
            politician_linked=ClassificationCount(
                speaker_count=5, conversation_count=50
            ),
            government_official_linked=ClassificationCount(
                speaker_count=0, conversation_count=0
            ),
            unclassified=ClassificationCount(speaker_count=5, conversation_count=50),
        )

        with pytest.raises(AttributeError):
            stats.politician_linked = ClassificationCount(  # type: ignore[misc]
                speaker_count=999, conversation_count=999
            )
