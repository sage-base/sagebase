"""総務省比例代表XLSパーサーのテスト."""

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
)
from src.infrastructure.importers.soumu_proportional_xls_parser import (
    _clean_cell,
    _clean_name,
    _detect_block_name,
    _parse_float,
    _parse_int,
    _parse_proportional_rows,
    _parse_winners_count,
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


class TestCleanName:
    """XLS氏名クリーンアップのテスト."""

    def test_standard_name(self) -> None:
        assert _clean_name("佐\u3000藤\u3000\u3000英\u3000道") == "佐藤 英道"

    def test_hiragana_sei(self) -> None:
        assert _clean_name("はたやま\u3000\u3000和\u3000也") == "はたやま 和也"

    def test_long_mei(self) -> None:
        assert _clean_name("鈴\u3000木\u3000\u3000た\u3000か\u3000こ") == "鈴木 たかこ"

    def test_three_char_sei(self) -> None:
        assert (
            _clean_name("佐\u3000々\u3000木\u3000\u3000あ\u3000け\u3000み")
            == "佐々木 あけみ"
        )

    def test_empty(self) -> None:
        assert _clean_name("") == ""

    def test_none_string(self) -> None:
        assert _clean_name("  ") == ""


class TestParseWinnersCount:
    """当選人数パースのテスト."""

    def test_standard(self) -> None:
        assert _parse_winners_count("3 人\u3000\u3000") == 3

    def test_one(self) -> None:
        assert _parse_winners_count("1 人\u3000\u3000") == 1

    def test_zero(self) -> None:
        assert _parse_winners_count("0 人\u3000\u3000") == 0

    def test_empty(self) -> None:
        assert _parse_winners_count("") == 0

    def test_none(self) -> None:
        assert _parse_winners_count(None) == 0


def _make_empty_row(ncols: int = 28) -> tuple[object, ...]:
    return tuple("" for _ in range(ncols))


def _make_section_rows(
    block_name: str,
    parties: list[tuple[str, int, list[tuple[str, int, str, float | None]]]],
) -> list[tuple[object, ...]]:
    """テスト用のXLSセクション行データを生成する.

    parties: [(party_name, winners_count, [(name, order, smd, loss), ...])]
    """
    ncols = 28
    rows: list[tuple[object, ...]] = []

    # 行+0: ブロック名
    block_row = [""] * ncols
    block_row[0] = f"{block_name}選挙区"
    rows.append(tuple(block_row))

    # 行+1: 空行
    rows.append(_make_empty_row(ncols))

    # 行+2: 政党名
    party_row = [""] * ncols
    for idx, (pname, _, _) in enumerate(parties):
        if idx < 4:
            col = idx * 7 + 2
            party_row[col] = pname
    rows.append(tuple(party_row))

    # 行+3: 空行
    rows.append(_make_empty_row(ncols))

    # 行+4: 得票数（テストでは省略）
    rows.append(_make_empty_row(ncols))

    # 行+5: 当選人数
    winners_row = [""] * ncols
    for idx, (_, wc, _) in enumerate(parties):
        if idx < 4:
            col = idx * 7 + 2
            winners_row[col] = f"{wc} 人\u3000\u3000"
    rows.append(tuple(winners_row))

    # 行+6: 男女（省略）
    rows.append(_make_empty_row(ncols))

    # 行+7: ヘッダー
    rows.append(_make_empty_row(ncols))

    # 行+8〜: 候補者データ
    max_cands = max((len(cands) for _, _, cands in parties), default=0)
    for c_idx in range(max_cands):
        data_row = [""] * ncols
        for p_idx, (_, _, cands) in enumerate(parties):
            if p_idx >= 4:
                break
            if c_idx >= len(cands):
                continue
            offset = p_idx * 7
            name_raw, order, smd, loss = cands[c_idx]
            data_row[offset + 0] = float(order)
            data_row[offset + 1] = name_raw
            data_row[offset + 5] = smd if smd else " "
            data_row[offset + 6] = loss if loss is not None else ""
        rows.append(tuple(data_row))

    return rows


class TestParseProportionalRows:
    """_parse_proportional_rowsのテスト."""

    def test_single_block_single_party(self) -> None:
        """1ブロック1政党の基本パターン."""
        rows = _make_section_rows(
            "北海道",
            [
                (
                    "自由民主党",
                    2,
                    [
                        ("渡\u3000辺\u3000\u3000孝\u3000一", 1, "", None),
                        ("鈴\u3000木\u3000\u3000た\u3000か\u3000こ", 2, "", None),
                        ("船\u3000橋\u3000\u3000利\u3000実", 3, "落", 86.972),
                    ],
                ),
            ],
        )
        candidates = _parse_proportional_rows(rows, 48)

        assert len(candidates) == 3
        assert candidates[0].name == "渡辺 孝一"
        assert candidates[0].party_name == "自由民主党"
        assert candidates[0].block_name == "北海道"
        assert candidates[0].list_order == 1
        assert candidates[0].is_elected is True

        assert candidates[1].name == "鈴木 たかこ"
        assert candidates[1].is_elected is True

        assert candidates[2].name == "船橋 利実"
        assert candidates[2].smd_result == "落"
        assert candidates[2].loss_ratio == 86.972
        assert candidates[2].is_elected is False

    def test_multiple_parties(self) -> None:
        """複数政党の検出."""
        rows = _make_section_rows(
            "東京",
            [
                (
                    "自由民主党",
                    1,
                    [("佐\u3000藤\u3000\u3000太\u3000郎", 1, "", None)],
                ),
                (
                    "立憲民主党",
                    1,
                    [("田\u3000中\u3000\u3000花\u3000子", 1, "落", 95.5)],
                ),
            ],
        )
        candidates = _parse_proportional_rows(rows, 48)

        assert len(candidates) == 2
        assert candidates[0].party_name == "自由民主党"
        assert candidates[0].is_elected is True
        assert candidates[1].party_name == "立憲民主党"
        assert candidates[1].smd_result == "落"
        assert candidates[1].loss_ratio == 95.5

    def test_smd_result_elected(self) -> None:
        """小選挙区当選の候補者."""
        rows = _make_section_rows(
            "近畿",
            [
                (
                    "公明党",
                    2,
                    [
                        ("よしかわ\u3000\u3000貴\u3000盛", 1, "当", 100.0),
                        ("山\u3000田\u3000\u3000次\u3000郎", 2, "", None),
                    ],
                ),
            ],
        )
        candidates = _parse_proportional_rows(rows, 48)

        assert len(candidates) == 2
        assert candidates[0].smd_result == "当"
        assert candidates[0].loss_ratio == 100.0
        assert candidates[0].is_elected is True
        assert candidates[1].smd_result == ""
        assert candidates[1].is_elected is True

    def test_zero_winners(self) -> None:
        """当選者0の政党."""
        rows = _make_section_rows(
            "四国",
            [
                (
                    "テスト党",
                    0,
                    [("候\u3000補\u3000\u3000太\u3000郎", 1, "", None)],
                ),
            ],
        )
        candidates = _parse_proportional_rows(rows, 48)

        assert len(candidates) == 1
        assert candidates[0].is_elected is False

    def test_multiple_sections_same_block(self) -> None:
        """同じブロックの複数セクション."""
        section1 = _make_section_rows(
            "北海道",
            [
                (
                    "自由民主党",
                    1,
                    [("佐\u3000藤\u3000\u3000一\u3000郎", 1, "", None)],
                ),
            ],
        )
        section2 = _make_section_rows(
            "北海道",
            [
                (
                    "立憲民主党",
                    1,
                    [("鈴\u3000木\u3000\u3000二\u3000郎", 1, "落", 90.0)],
                ),
            ],
        )
        rows = section1 + section2
        candidates = _parse_proportional_rows(rows, 48)

        assert len(candidates) == 2
        assert candidates[0].party_name == "自由民主党"
        assert candidates[1].party_name == "立憲民主党"

    def test_empty_rows(self) -> None:
        """空のデータ."""
        candidates = _parse_proportional_rows([], 48)
        assert candidates == []

    def test_detect_block_from_senkyoku_format(self) -> None:
        """'東京都選挙区'形式のブロック名検出."""
        rows = _make_section_rows(
            "東京都",
            [
                (
                    "テスト党",
                    1,
                    [("テ\u3000ス\u3000ト\u3000\u3000太\u3000郎", 1, "", None)],
                ),
            ],
        )
        # '東京都選挙区'に修正
        block_row = list(rows[0])
        block_row[0] = "東京都選挙区"
        rows[0] = tuple(block_row)

        candidates = _parse_proportional_rows(rows, 48)
        assert len(candidates) == 1
        assert candidates[0].block_name == "東京"
