"""総務省比例代表XLSパーサーのテスト."""

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
)
from src.infrastructure.importers.soumu_proportional_xls_parser import (
    _clean_cell,
    _detect_block_name,
    _find_column_layout,
    _parse_float,
    _parse_int,
    get_elected_candidates,
)


class TestCleanCell:
    """セル値クリーンアップのテスト."""

    def test_none(self) -> None:
        assert _clean_cell(None) == ""

    def test_empty_string(self) -> None:
        assert _clean_cell("") == ""

    def test_whitespace(self) -> None:
        assert _clean_cell("  ") == ""

    def test_normal_string(self) -> None:
        assert _clean_cell("北海道") == "北海道"

    def test_full_width_numbers(self) -> None:
        assert _clean_cell("１２３") == "123"


class TestParseFloat:
    """float変換のテスト."""

    def test_none(self) -> None:
        assert _parse_float(None) is None

    def test_int_value(self) -> None:
        assert _parse_float(92) == 92.0

    def test_float_value(self) -> None:
        assert _parse_float(92.714) == 92.714

    def test_zero(self) -> None:
        assert _parse_float(0) is None

    def test_string_with_percent(self) -> None:
        assert _parse_float("92.714%") == 92.714

    def test_full_width_percent(self) -> None:
        assert _parse_float("９２．７１４％") == 92.714


class TestParseInt:
    """int変換のテスト."""

    def test_none(self) -> None:
        assert _parse_int(None) is None

    def test_int_value(self) -> None:
        assert _parse_int(3) == 3

    def test_float_value(self) -> None:
        assert _parse_int(3.0) == 3

    def test_zero(self) -> None:
        assert _parse_int(0) is None

    def test_string_with_comma(self) -> None:
        assert _parse_int("1,234") == 1234


class TestDetectBlockName:
    """ブロック名検出のテスト."""

    def test_block_with_suffix(self) -> None:
        row = ("北海道ブロック", None, None)
        assert _detect_block_name(row) == "北海道"

    def test_block_name_only(self) -> None:
        row = ("東北", None, None)
        assert _detect_block_name(row) == "東北"

    def test_block_with_space(self) -> None:
        row = ("北関東 ブロック", None, None)
        assert _detect_block_name(row) == "北関東"

    def test_no_block(self) -> None:
        row = ("自由民主党", "3", None)
        assert _detect_block_name(row) is None

    def test_empty_row(self) -> None:
        row = (None, None, None)
        assert _detect_block_name(row) is None

    def test_kyushu_block(self) -> None:
        row = ("九州ブロック", None, None)
        assert _detect_block_name(row) == "九州"


class TestFindColumnLayout:
    """カラムレイアウト検出のテスト."""

    def test_standard_layout(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("名簿順位", "氏名", "小選挙区", "惜敗率"),
        ]
        layout = _find_column_layout(rows, 0)
        assert layout is not None
        assert "list_order" in layout
        assert "name" in layout
        assert "smd_result" in layout
        assert "loss_ratio" in layout

    def test_no_header(self) -> None:
        rows: list[tuple[object, ...]] = [
            (1, "田中太郎", "落", 92.0),
        ]
        layout = _find_column_layout(rows, 0)
        assert layout is None

    def test_partial_layout(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("順位", "候補者名"),
        ]
        layout = _find_column_layout(rows, 0)
        assert layout is not None
        assert "list_order" in layout
        assert "name" in layout


class TestGetElectedCandidates:
    """当選者フィルタリングのテスト."""

    def test_filter_elected(self) -> None:
        candidates = [
            ProportionalCandidateRecord(
                name="当選者A",
                party_name="テスト党",
                block_name="東京",
                list_order=1,
                smd_result="",
                loss_ratio=None,
                is_elected=True,
            ),
            ProportionalCandidateRecord(
                name="落選者B",
                party_name="テスト党",
                block_name="東京",
                list_order=2,
                smd_result="",
                loss_ratio=None,
                is_elected=False,
            ),
        ]
        elected = get_elected_candidates(candidates)
        assert len(elected) == 1
        assert elected[0].name == "当選者A"

    def test_empty_list(self) -> None:
        assert get_elected_candidates([]) == []
