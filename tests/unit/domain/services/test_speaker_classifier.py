"""発言者分類サービスのテスト."""

import pytest

from src.domain.services.speaker_classifier import (
    NON_POLITICIAN_EXACT_NAMES,
    classify_speaker_skip_reason,
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


class TestClassifySpeakerSkipReason:
    """classify_speaker_skip_reason()のテスト."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("議長", "role_only"),
            ("副議長", "role_only"),
            ("委員長", "role_only"),
            ("副委員長", "role_only"),
            ("仮議長", "role_only"),
        ],
    )
    def test_role_only_classification(self, name: str, expected: str) -> None:
        """議会役職名がrole_onlyに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("参考人", "reference_person"),
            ("証人", "reference_person"),
            ("公述人", "reference_person"),
        ],
    )
    def test_reference_person_classification(self, name: str, expected: str) -> None:
        """参考人等がreference_personに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("説明員", "government_official"),
            ("政府委員", "government_official"),
            ("政府参考人", "government_official"),
        ],
    )
    def test_government_official_classification(self, name: str, expected: str) -> None:
        """政府側出席者がgovernment_officialに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("事務局長", "other_non_politician"),
            ("書記", "other_non_politician"),
            ("幹事", "other_non_politician"),
            ("会議録情報", "other_non_politician"),
        ],
    )
    def test_other_non_politician_classification(
        self, name: str, expected: str
    ) -> None:
        """その他の非政治家がother_non_politicianに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    def test_normal_name_returns_none(self) -> None:
        """通常の人名はNoneを返す（政治家の可能性あり）."""
        assert classify_speaker_skip_reason("田中太郎") is None
        assert classify_speaker_skip_reason("岸田文雄") is None

    def test_strips_whitespace(self) -> None:
        """前後空白をstripして判定する."""
        assert classify_speaker_skip_reason(" 議長 ") == "role_only"
