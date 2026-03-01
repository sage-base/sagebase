"""発言者分類サービスのテスト."""

import pytest

from src.domain.services.speaker_classifier import (
    NON_POLITICIAN_EXACT_NAMES,
    NON_POLITICIAN_PREFIX_PATTERNS,
    SkipReason,
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
            "事務総長",
            "法制局長",
            "書記官長",
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
            "参考人A",  # 「（」で始まらない接尾辞
        ],
    )
    def test_returns_false_for_politician_names(self, name: str) -> None:
        """通常の人名や完全一致しないパターンはFalseを返す."""
        assert is_non_politician_name(name) is False

    @pytest.mark.parametrize(
        "name",
        [
            "政府参考人（山田太郎君）",
            "参考人（鈴木花子君）",
            "証人（田中一郎）",
            "公述人（佐藤二郎）",
            "説明員（高橋三郎君）",
            "政府委員（伊藤四郎）",
            "事務総長（渡辺五郎君）",
            "事務局長（中村六郎）",
            "事務局次長（小林七郎君）",
            "法制局長（加藤八郎）",
            "書記官長（松本九郎君）",
        ],
    )
    def test_returns_true_for_prefix_patterns(self, name: str) -> None:
        """「役職名（人名）」形式のプレフィックスパターンはTrueを返す."""
        assert is_non_politician_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "内閣総理大臣（岸田文雄君）",
            "外務大臣（林芳正君）",
            "議長（西村義直君）",
            "委員長（田中太郎君）",
            "副議長（山田花子君）",
        ],
    )
    def test_returns_false_for_politician_role_with_name(self, name: str) -> None:
        """政治家の役職（議長・委員長・大臣等）の括弧付き形式はFalseを返す."""
        assert is_non_politician_name(name) is False

    def test_strips_whitespace_before_matching(self) -> None:
        """前後に空白がある場合もstrip後に判定する."""
        assert is_non_politician_name(" 委員長 ") is True
        assert is_non_politician_name("　議長　") is True
        assert is_non_politician_name(" 政府参考人（山田太郎君） ") is True

    def test_returns_false_for_empty_string(self) -> None:
        """空文字列はFalseを返す."""
        assert is_non_politician_name("") is False

    def test_exact_names_constant_is_frozenset(self) -> None:
        """完全一致定数がfrozensetであることを確認."""
        assert isinstance(NON_POLITICIAN_EXACT_NAMES, frozenset)

    def test_prefix_patterns_constant_is_frozenset(self) -> None:
        """プレフィックス定数がfrozensetであることを確認."""
        assert isinstance(NON_POLITICIAN_PREFIX_PATTERNS, frozenset)

    def test_exact_names_constant_is_not_empty(self) -> None:
        """完全一致パターンが少なくとも1つ以上定義されている."""
        assert len(NON_POLITICIAN_EXACT_NAMES) > 0

    def test_prefix_patterns_constant_is_not_empty(self) -> None:
        """プレフィックスパターンが少なくとも1つ以上定義されている."""
        assert len(NON_POLITICIAN_PREFIX_PATTERNS) > 0


class TestClassifySpeakerSkipReason:
    """classify_speaker_skip_reason()のテスト."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("議長", SkipReason.ROLE_ONLY),
            ("副議長", SkipReason.ROLE_ONLY),
            ("委員長", SkipReason.ROLE_ONLY),
            ("副委員長", SkipReason.ROLE_ONLY),
            ("仮議長", SkipReason.ROLE_ONLY),
        ],
    )
    def test_role_only_classification(self, name: str, expected: SkipReason) -> None:
        """議会役職名がROLE_ONLYに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("参考人", SkipReason.REFERENCE_PERSON),
            ("証人", SkipReason.REFERENCE_PERSON),
            ("公述人", SkipReason.REFERENCE_PERSON),
        ],
    )
    def test_reference_person_classification(
        self, name: str, expected: SkipReason
    ) -> None:
        """参考人等がREFERENCE_PERSONに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("説明員", SkipReason.GOVERNMENT_OFFICIAL),
            ("政府委員", SkipReason.GOVERNMENT_OFFICIAL),
            ("政府参考人", SkipReason.GOVERNMENT_OFFICIAL),
        ],
    )
    def test_government_official_classification(
        self, name: str, expected: SkipReason
    ) -> None:
        """政府側出席者がGOVERNMENT_OFFICIALに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("事務局長", SkipReason.OTHER_NON_POLITICIAN),
            ("事務局次長", SkipReason.OTHER_NON_POLITICIAN),
            ("事務総長", SkipReason.OTHER_NON_POLITICIAN),
            ("法制局長", SkipReason.OTHER_NON_POLITICIAN),
            ("書記官長", SkipReason.OTHER_NON_POLITICIAN),
            ("書記", SkipReason.OTHER_NON_POLITICIAN),
            ("速記者", SkipReason.OTHER_NON_POLITICIAN),
            ("幹事", SkipReason.OTHER_NON_POLITICIAN),
            ("会議録情報", SkipReason.OTHER_NON_POLITICIAN),
        ],
    )
    def test_other_non_politician_classification(
        self, name: str, expected: SkipReason
    ) -> None:
        """その他の非政治家がOTHER_NON_POLITICIANに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("参考人（山田太郎君）", SkipReason.REFERENCE_PERSON),
            ("証人（田中花子）", SkipReason.REFERENCE_PERSON),
            ("公述人（佐藤一郎君）", SkipReason.REFERENCE_PERSON),
            ("政府参考人（鈴木次郎君）", SkipReason.GOVERNMENT_OFFICIAL),
            ("政府委員（高橋三郎）", SkipReason.GOVERNMENT_OFFICIAL),
            ("説明員（伊藤四郎君）", SkipReason.GOVERNMENT_OFFICIAL),
            ("事務総長（渡辺五郎君）", SkipReason.OTHER_NON_POLITICIAN),
            ("事務局長（中村六郎）", SkipReason.OTHER_NON_POLITICIAN),
            ("法制局長（加藤七郎君）", SkipReason.OTHER_NON_POLITICIAN),
            ("書記官長（松本八郎）", SkipReason.OTHER_NON_POLITICIAN),
        ],
    )
    def test_prefix_pattern_classification(
        self, name: str, expected: SkipReason
    ) -> None:
        """「役職名（人名）」形式が正しいカテゴリに分類される."""
        assert classify_speaker_skip_reason(name) == expected

    def test_normal_name_returns_none(self) -> None:
        """通常の人名はNoneを返す（政治家の可能性あり）."""
        assert classify_speaker_skip_reason("田中太郎") is None
        assert classify_speaker_skip_reason("岸田文雄") is None

    def test_politician_role_with_name_returns_none(self) -> None:
        """政治家の役職（議長・大臣等）の括弧付き形式はNoneを返す."""
        assert classify_speaker_skip_reason("議長（西村義直君）") is None
        assert classify_speaker_skip_reason("内閣総理大臣（岸田文雄君）") is None
        assert classify_speaker_skip_reason("委員長（田中太郎君）") is None

    def test_strips_whitespace(self) -> None:
        """前後空白をstripして判定する."""
        assert classify_speaker_skip_reason(" 議長 ") == SkipReason.ROLE_ONLY
        assert (
            classify_speaker_skip_reason(" 政府参考人（山田太郎君） ")
            == SkipReason.GOVERNMENT_OFFICIAL
        )
