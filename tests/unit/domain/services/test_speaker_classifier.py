"""発言者分類サービスのテスト."""

import pytest

from src.domain.services.speaker_classifier import (
    NON_POLITICIAN_EXACT_NAMES,
    is_non_politician_name,
)


class TestIsNonPoliticianName:
    """is_non_politician_name()のテスト."""

    @pytest.mark.parametrize(
        "name",
        [
            "委員長",
            "副委員長",
            "議長",
            "副議長",
            "仮議長",
            "事務局長",
            "事務局次長",
            "書記",
            "速記者",
            "参考人",
            "証人",
            "公述人",
            "説明員",
            "政府委員",
            "政府参考人",
            "幹事",
            "会議録情報",
        ],
    )
    def test_returns_true_for_non_politician_patterns(self, name: str) -> None:
        """NON_POLITICIAN_EXACT_NAMESに含まれる名前はTrueを返す."""
        assert is_non_politician_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "田中太郎",
            "山田花子",
            "鈴木一郎",
            "安倍晋三",
            "委員長代理",  # 完全一致しない
            "副議長（仮）",  # 余計な文字
            "参考人A",  # 部分一致しない
        ],
    )
    def test_returns_false_for_politician_names(self, name: str) -> None:
        """通常の人名や完全一致しないパターンはFalseを返す."""
        assert is_non_politician_name(name) is False

    def test_strips_whitespace_before_matching(self) -> None:
        """前後に空白がある場合もstrip後に判定する."""
        assert is_non_politician_name(" 委員長 ") is True
        assert is_non_politician_name("　議長　") is True

    def test_returns_false_for_empty_string(self) -> None:
        """空文字列はFalseを返す."""
        assert is_non_politician_name("") is False

    def test_constant_is_frozenset(self) -> None:
        """定数がfrozensetであることを確認."""
        assert isinstance(NON_POLITICIAN_EXACT_NAMES, frozenset)

    def test_constant_is_not_empty(self) -> None:
        """パターンが少なくとも1つ以上定義されている."""
        assert len(NON_POLITICIAN_EXACT_NAMES) > 0
