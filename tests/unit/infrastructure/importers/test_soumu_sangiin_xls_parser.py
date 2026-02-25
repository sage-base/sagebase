"""総務省参議院選挙XLSパーサーのテスト."""

import tempfile

from pathlib import Path

import pytest

from src.infrastructure.importers.soumu_sangiin_xls_parser import (
    _clean_cell_value,
    _extract_prefecture,
    _find_total_row_index,
    _get_seats_for_district,
    _is_skip_column,
    _parse_sangiin_rows,
    _parse_votes,
    parse_sangiin_xls_file,
)


class TestCleanCellValue:
    """セル値クリーンアップのテスト."""

    def test_none(self) -> None:
        assert _clean_cell_value(None) is None

    def test_empty_string(self) -> None:
        assert _clean_cell_value("") is None

    def test_whitespace_only(self) -> None:
        assert _clean_cell_value("  ") is None

    def test_normal_string(self) -> None:
        assert _clean_cell_value("テスト") == "テスト"

    def test_strips_whitespace(self) -> None:
        assert _clean_cell_value("  テスト  ") == "テスト"

    def test_number(self) -> None:
        assert _clean_cell_value(42) == "42"


class TestParseVotes:
    """得票数パースのテスト."""

    def test_integer(self) -> None:
        assert _parse_votes(12345) == 12345

    def test_float(self) -> None:
        assert _parse_votes(12345.0) == 12345

    def test_string_number(self) -> None:
        assert _parse_votes("12345") == 12345

    def test_string_with_commas(self) -> None:
        assert _parse_votes("12,345") == 12345

    def test_zen_to_han(self) -> None:
        assert _parse_votes("１２３４５") == 12345

    def test_none(self) -> None:
        assert _parse_votes(None) is None

    def test_empty_string(self) -> None:
        assert _parse_votes("") is None

    def test_non_numeric(self) -> None:
        assert _parse_votes("abc") is None


class TestExtractPrefecture:
    """都道府県名抽出のテスト."""

    def test_hokkaido(self) -> None:
        assert _extract_prefecture("北海道") == "北海道"

    def test_tokyo(self) -> None:
        assert _extract_prefecture("東京都") == "東京都"

    def test_osaka(self) -> None:
        assert _extract_prefecture("大阪府") == "大阪府"

    def test_gouku(self) -> None:
        """合区の場合はそのまま返す."""
        assert _extract_prefecture("鳥取県・島根県") == "鳥取県・島根県"

    def test_unknown(self) -> None:
        assert _extract_prefecture("不明") == "不明"


class TestIsSkipColumn:
    """スキップ列判定のテスト."""

    def test_candidate_header(self) -> None:
        assert _is_skip_column("候補者名") is True

    def test_total_votes(self) -> None:
        assert _is_skip_column("得票数計") is True

    def test_total(self) -> None:
        assert _is_skip_column("合計") is True

    def test_candidate_name(self) -> None:
        assert _is_skip_column("山田太郎") is False


class TestFindTotalRowIndex:
    """合計行検索のテスト."""

    def test_goukei_in_first_cell(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("header",),
            ("data1",),
            ("北海道 合計", 100),
        ]
        assert _find_total_row_index(rows, 0) == 2

    def test_kei_in_first_cell(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("header",),
            ("data1",),
            ("計", 100),
        ]
        assert _find_total_row_index(rows, 0) == 2

    def test_no_total_row(self) -> None:
        rows: list[tuple[object, ...]] = [
            ("header",),
            ("data1", 50),
            ("data2", 50),
        ]
        assert _find_total_row_index(rows, 0) is None


class TestGetSeatsForDistrict:
    """定数取得のテスト."""

    def test_hokkaido_26(self) -> None:
        assert _get_seats_for_district(26, "北海道") == 3

    def test_tokyo_26(self) -> None:
        assert _get_seats_for_district(26, "東京都") == 6

    def test_aomori_26(self) -> None:
        assert _get_seats_for_district(26, "青森県") == 1

    def test_hokkaido_27(self) -> None:
        """第27回の北海道定数."""
        assert _get_seats_for_district(27, "北海道") == 2

    def test_tokyo_27(self) -> None:
        """第27回の東京都定数."""
        assert _get_seats_for_district(27, "東京都") == 6

    def test_gouku_27(self) -> None:
        """第27回の合区定数."""
        assert _get_seats_for_district(27, "鳥取県・島根県") == 1

    def test_gouku_25(self) -> None:
        """合区の定数取得."""
        assert _get_seats_for_district(25, "鳥取県・島根県") == 1

    def test_unknown_election(self) -> None:
        assert _get_seats_for_district(99, "北海道") is None

    def test_unknown_district(self) -> None:
        assert _get_seats_for_district(26, "存在しない県") is None


class TestParseSangiinRows:
    """行データパースのテスト."""

    def _make_rows(
        self,
        district: str = "北海道",
        candidates: list[str] | None = None,
        parties: list[str] | None = None,
        votes: list[int] | None = None,
    ) -> list[tuple[object, ...]]:
        """テスト用の行データを生成する."""
        if candidates is None:
            candidates = ["候補A", "候補B", "候補C"]
        if parties is None:
            parties = ["政党A", "政党B", "政党C"]
        if votes is None:
            votes = [1000, 2000, 3000]

        rows: list[tuple[object, ...]] = [
            ("令和4年7月10日執行",),
            ("", "参議院議員通常選挙（選挙区）\u3000候補者別市区町村別得票数一覧"),
            (district,),
            ("候補者名", *candidates, "得票数計"),
            ("市区町村名＼政党等名", *parties, ""),
            ("市A", *votes, sum(votes)),
            (f"{district} 合計", *votes, sum(votes)),
        ]
        return rows

    def test_basic_parsing(self) -> None:
        """基本的なパースが正しく動作する."""
        rows = self._make_rows()
        candidates, election_info = _parse_sangiin_rows(rows, 26)

        assert len(candidates) == 3
        assert election_info is not None
        assert election_info.election_date.year == 2022

    def test_candidate_names(self) -> None:
        """候補者名が正しく抽出される."""
        rows = self._make_rows(candidates=["山田太郎", "佐藤花子"])
        candidates, _ = _parse_sangiin_rows(rows, 26)

        names = {c.name for c in candidates}
        assert "山田太郎" in names
        assert "佐藤花子" in names

    def test_party_names(self) -> None:
        """政党名が正しく抽出される."""
        rows = self._make_rows(
            candidates=["候補A", "候補B"],
            parties=["自由民主党", "立憲民主党"],
        )
        candidates, _ = _parse_sangiin_rows(rows, 26)

        party_names = {c.party_name for c in candidates}
        assert "自由民主党" in party_names
        assert "立憲民主党" in party_names

    def test_ranking_by_votes(self) -> None:
        """得票数順にランク付けされる."""
        rows = self._make_rows(
            candidates=["候補A", "候補B", "候補C"],
            votes=[1000, 3000, 2000],
        )
        candidates, _ = _parse_sangiin_rows(rows, 26)

        # 得票数降順でソート済み
        assert candidates[0].name == "候補B"
        assert candidates[0].rank == 1
        assert candidates[0].total_votes == 3000

        assert candidates[1].name == "候補C"
        assert candidates[1].rank == 2

        assert candidates[2].name == "候補A"
        assert candidates[2].rank == 3

    def test_elected_with_seats(self) -> None:
        """定数に基づいて当選判定される（北海道: 定数3）."""
        rows = self._make_rows(
            district="北海道",
            candidates=["候補A", "候補B", "候補C", "候補D", "候補E"],
            parties=["A", "B", "C", "D", "E"],
            votes=[5000, 4000, 3000, 2000, 1000],
        )
        candidates, _ = _parse_sangiin_rows(rows, 26)

        assert len(candidates) == 5
        assert candidates[0].is_elected is True  # 1位
        assert candidates[1].is_elected is True  # 2位
        assert candidates[2].is_elected is True  # 3位 (定数3)
        assert candidates[3].is_elected is False  # 4位
        assert candidates[4].is_elected is False  # 5位

    def test_elected_single_seat(self) -> None:
        """定数1の選挙区では最多得票1名のみ当選."""
        rows = self._make_rows(
            district="青森県",
            candidates=["候補A", "候補B"],
            parties=["A", "B"],
            votes=[3000, 2000],
        )
        candidates, _ = _parse_sangiin_rows(rows, 26)

        assert candidates[0].is_elected is True
        assert candidates[1].is_elected is False

    def test_skip_tokuhyousukei_column(self) -> None:
        """「得票数計」列がスキップされる."""
        rows = self._make_rows()
        candidates, _ = _parse_sangiin_rows(rows, 26)

        # "得票数計" は候補者として抽出されない
        names = [c.name for c in candidates]
        assert "得票数計" not in names

    def test_skip_hirei_data(self) -> None:
        """比例代表データはスキップされる."""
        rows: list[tuple[object, ...]] = [
            ("令和4年7月10日執行",),
            ("", "参議院議員通常選挙（比例代表）\u3000名簿登載者別得票数"),
            ("政党名",),
            ("整理番号", "1", "2"),
            ("名簿登載者名", "候補A", "候補B"),
        ]
        candidates, _ = _parse_sangiin_rows(rows, 26)
        assert len(candidates) == 0

    def test_empty_rows(self) -> None:
        """データ行が不足の場合は空を返す."""
        rows: list[tuple[object, ...]] = [
            ("header",),
        ]
        candidates, election_info = _parse_sangiin_rows(rows, 26)
        assert len(candidates) == 0
        assert election_info is None

    def test_without_election_number(self) -> None:
        """election_numberなしでもパースできる（全員1位のみ当選）."""
        rows = self._make_rows(
            candidates=["候補A", "候補B"],
            parties=["A", "B"],
            votes=[3000, 2000],
        )
        candidates, _ = _parse_sangiin_rows(rows, None)

        assert len(candidates) == 2
        assert candidates[0].is_elected is True
        assert candidates[1].is_elected is False

    def test_district_name_from_content(self) -> None:
        """選挙区名がファイル内容から正しく取得される."""
        rows = self._make_rows(district="東京都")
        candidates, _ = _parse_sangiin_rows(rows, 26)

        assert all(c.district_name == "東京都" for c in candidates)
        assert all(c.prefecture == "東京都" for c in candidates)


class TestParseSangiinXlsFile:
    """XLSファイルパースの統合テスト."""

    def test_unsupported_extension(self) -> None:
        """未対応の拡張子はエラーを返す."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"dummy")
            path = Path(f.name)

        election_info, candidates = parse_sangiin_xls_file(path)
        assert election_info is None
        assert len(candidates) == 0

    def test_xlsx_parsing(self) -> None:
        """XLSXファイルが正しくパースされる."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = "北海道"

        # Row 1: 選挙日
        ws.append(["令和4年7月10日執行"])
        # Row 2: タイトル
        ws.append(
            ["", "参議院議員通常選挙（選挙区）\u3000候補者別市区町村別得票数一覧"]
        )
        # Row 3: 選挙区名
        ws.append(["北海道"])
        # Row 4: 候補者名
        ws.append(["候補者名", "候補A", "候補B", "候補C", "得票数計"])
        # Row 5: 政党名
        ws.append(["市区町村名＼政党等名", "政党A", "政党B", "政党C", ""])
        # Row 6: データ行
        ws.append(["札幌市", 5000, 4000, 3000, 12000])
        # Row 7: 合計行
        ws.append(["北海道 合計", 5000, 4000, 3000, 12000])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            wb.save(f.name)
            path = Path(f.name)

        wb.close()

        election_info, candidates = parse_sangiin_xls_file(path, 26)

        assert election_info is not None
        assert election_info.election_date.year == 2022
        assert election_info.election_date.month == 7
        assert election_info.election_date.day == 10

        assert len(candidates) == 3
        # 得票数降順
        assert candidates[0].name == "候補A"
        assert candidates[0].total_votes == 5000
        assert candidates[0].rank == 1
        assert candidates[0].is_elected is True  # 北海道定数3

        assert candidates[1].name == "候補B"
        assert candidates[1].total_votes == 4000
        assert candidates[1].is_elected is True

        assert candidates[2].name == "候補C"
        assert candidates[2].total_votes == 3000
        assert candidates[2].is_elected is True

    @pytest.mark.parametrize(
        ("election_number", "district", "expected_seats"),
        [
            (26, "北海道", 3),
            (26, "東京都", 6),
            (25, "鳥取県・島根県", 1),
        ],
    )
    def test_seats_lookup(
        self, election_number: int, district: str, expected_seats: int
    ) -> None:
        """定数ルックアップが正しく動作する."""
        seats = _get_seats_for_district(election_number, district)
        assert seats == expected_seats
