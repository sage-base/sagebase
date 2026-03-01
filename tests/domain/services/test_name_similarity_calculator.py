"""NameSimilarityCalculator の単体テスト。"""

import pytest

from src.domain.services.name_similarity_calculator import NameSimilarityCalculator


class TestJaccard:
    """jaccard メソッドのテスト。"""

    def test_exact_match(self) -> None:
        assert NameSimilarityCalculator.jaccard("山田太郎", "山田太郎") == 1.0

    def test_completely_different(self) -> None:
        assert NameSimilarityCalculator.jaccard("山田", "鈴木") == 0.0

    def test_partial_match(self) -> None:
        score = NameSimilarityCalculator.jaccard("山田太郎", "山田次郎")
        # intersection={山,田,郎}=3, union={山,田,太,次,郎}=5 → 3/5=0.6
        assert score == pytest.approx(0.6)

    def test_empty_both(self) -> None:
        assert NameSimilarityCalculator.jaccard("", "") == 1.0

    def test_empty_one(self) -> None:
        assert NameSimilarityCalculator.jaccard("山田", "") == 0.0
        assert NameSimilarityCalculator.jaccard("", "山田") == 0.0

    def test_symmetry(self) -> None:
        score1 = NameSimilarityCalculator.jaccard("佐藤花子", "佐藤太郎")
        score2 = NameSimilarityCalculator.jaccard("佐藤太郎", "佐藤花子")
        assert score1 == score2

    def test_subset_gives_less_than_one(self) -> None:
        # "党" は "自民党" に含まれるが、Jaccardでは1.0にはならない
        score = NameSimilarityCalculator.jaccard("党", "自民党")
        assert 0 < score < 1


class TestJaccardWithContainment:
    """jaccard_with_containment メソッドのテスト。"""

    def test_exact_match(self) -> None:
        assert (
            NameSimilarityCalculator.jaccard_with_containment("自民党", "自民党") == 1.0
        )

    def test_containment_forward(self) -> None:
        assert (
            NameSimilarityCalculator.jaccard_with_containment("自民党", "自民党議員団")
            == 0.9
        )

    def test_containment_reverse(self) -> None:
        assert (
            NameSimilarityCalculator.jaccard_with_containment("自民党議員団", "自民党")
            == 0.9
        )

    def test_custom_containment_score(self) -> None:
        assert (
            NameSimilarityCalculator.jaccard_with_containment(
                "山田", "山田太郎", containment_score=0.8
            )
            == 0.8
        )

    def test_no_containment_falls_to_jaccard(self) -> None:
        score = NameSimilarityCalculator.jaccard_with_containment(
            "自民党", "立憲民主党"
        )
        # 包含関係なし → Jaccard係数
        assert 0 < score < 0.9

    def test_empty_both(self) -> None:
        assert NameSimilarityCalculator.jaccard_with_containment("", "") == 1.0

    def test_empty_in_nonempty_is_containment(self) -> None:
        # Pythonでは "" in "山田" は True
        assert NameSimilarityCalculator.jaccard_with_containment("山田", "") == 0.9

    def test_completely_different(self) -> None:
        assert NameSimilarityCalculator.jaccard_with_containment("山田", "鈴木") == 0.0


class TestSequenceRatio:
    """sequence_ratio メソッドのテスト。"""

    def test_exact_match(self) -> None:
        assert NameSimilarityCalculator.sequence_ratio("山田太郎", "山田太郎") == 1.0

    def test_completely_different(self) -> None:
        score = NameSimilarityCalculator.sequence_ratio("あいう", "かきく")
        assert score == 0.0

    def test_empty_string(self) -> None:
        assert NameSimilarityCalculator.sequence_ratio("", "山田") == 0.0
        assert NameSimilarityCalculator.sequence_ratio("山田", "") == 0.0
        assert NameSimilarityCalculator.sequence_ratio("", "") == 0.0

    def test_order_matters(self) -> None:
        # SequenceMatcherは文字の順序を考慮する
        score_ordered = NameSimilarityCalculator.sequence_ratio(
            "山田太郎", "山田太郎次"
        )
        score_shuffled = NameSimilarityCalculator.sequence_ratio("山田太郎", "太郎山田")
        # 順序が近い方がスコアが高い
        assert score_ordered > score_shuffled

    def test_similar_names(self) -> None:
        score = NameSimilarityCalculator.sequence_ratio("山田太郎", "山田次郎")
        assert 0 < score < 1


class TestStagedMatch:
    """staged_match メソッドのテスト。"""

    def test_exact_match(self) -> None:
        score, match_type = NameSimilarityCalculator.staged_match(
            "田中太郎", "田中太郎"
        )
        assert score == 1.0
        assert match_type == "exact"

    def test_partial_containment(self) -> None:
        score, match_type = NameSimilarityCalculator.staged_match("田中", "田中太郎")
        assert score == 0.8
        assert match_type == "partial"

    def test_partial_reverse(self) -> None:
        score, match_type = NameSimilarityCalculator.staged_match("田中太郎", "田中")
        assert score == 0.8
        assert match_type == "partial"

    def test_word_match(self) -> None:
        # スペース区切りの単語が一致
        score, match_type = NameSimilarityCalculator.staged_match(
            "田中 太郎", "佐藤 太郎"
        )
        assert score == 0.6
        assert match_type == "fuzzy"

    def test_no_match(self) -> None:
        score, match_type = NameSimilarityCalculator.staged_match("山本", "田中太郎")
        assert score == 0.0
        assert match_type == "none"

    def test_custom_scores(self) -> None:
        score, match_type = NameSimilarityCalculator.staged_match(
            "田中", "田中太郎", partial_score=0.85
        )
        assert score == 0.85
        assert match_type == "partial"

    def test_fuzzy_char_overlap(self) -> None:
        # 共通文字が閾値を超える場合
        score, match_type = NameSimilarityCalculator.staged_match(
            "山田太郎", "山田次郎"
        )
        # common={山,田,郎}=3, max(4,4)=4, similarity=0.75 > 0.5 → 0.75*0.5=0.375
        assert match_type == "fuzzy"
        assert 0 < score < 0.5
