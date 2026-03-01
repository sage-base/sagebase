"""Wikipedia参議院選挙Wikitextパーサーのユニットテスト."""

# pyright: reportPrivateUsage=false
from src.infrastructure.importers._utils import normalize_prefecture
from src.infrastructure.importers.wikipedia_sangiin_election_wikitext_parser import (
    _extract_prefecture_from_sangiin_district,
    _normalize_sangiin_district,
    _parse_district_template,
    _parse_district_wikitable,
    _parse_proportional_template,
    _parse_proportional_wikitable,
    parse_sangiin_wikitext,
)


class TestParseSangiinDistrictTemplate:
    """{{参院選挙区当選者}}テンプレートのパーステスト."""

    WIKITEXT_TEMPLATE = """
{{colorbox|#9e9|自由民主党}} {{colorbox|#0ff|日本社会党}} {{colorbox|#9AF|緑風会}}
{{参院選挙区当選者
|北海道=
0ff:[[米田勲]]
9e9:[[堀末治]]
9e9:[[井川伊平]]
0ff:[[千葉信]]
|青森=9AF:[[佐藤尚武]]
|岩手=9e9:[[谷村貞治]]
|東京=
9e9:[[山本利壽]]
0ff:[[椿繁夫]]
|大阪=
9e9:[[田村文吉]]
0ff:[[藤田進]]
}}
"""

    def test_parse_hokkaido(self) -> None:
        """北海道の複数当選者が正しく抽出される."""
        result = _parse_district_template(
            self.WIKITEXT_TEMPLATE,
            {"9E9": "自由民主党", "0FF": "日本社会党", "9AF": "緑風会"},
        )
        hokkaido = [c for c in result if "北海道" in c.district_name]
        assert len(hokkaido) == 4
        assert hokkaido[0].name == "米田勲"
        assert hokkaido[0].party_name == "日本社会党"
        assert hokkaido[0].district_name == "北海道選挙区"
        assert hokkaido[0].prefecture == "北海道"

    def test_parse_inline_entry(self) -> None:
        """ヘッダと同一行のエントリが正しく抽出される（例: |青森=9AF:[[佐藤尚武]]）."""
        result = _parse_district_template(
            self.WIKITEXT_TEMPLATE,
            {"9E9": "自由民主党", "0FF": "日本社会党", "9AF": "緑風会"},
        )
        aomori = [c for c in result if "青森" in c.district_name]
        assert len(aomori) == 1
        assert aomori[0].name == "佐藤尚武"
        assert aomori[0].party_name == "緑風会"
        assert aomori[0].district_name == "青森県選挙区"

    def test_parse_tokyo(self) -> None:
        """東京都の当選者が正しく抽出される."""
        result = _parse_district_template(
            self.WIKITEXT_TEMPLATE,
            {"9E9": "自由民主党", "0FF": "日本社会党", "9AF": "緑風会"},
        )
        tokyo = [c for c in result if "東京" in c.district_name]
        assert len(tokyo) == 2
        assert tokyo[0].name == "山本利壽"
        assert tokyo[0].district_name == "東京都選挙区"

    def test_total_count(self) -> None:
        """全体の当選者数が正しい（北海道4+青森1+岩手1+東京2+大阪2=10）."""
        result = _parse_district_template(
            self.WIKITEXT_TEMPLATE,
            {"9E9": "自由民主党", "0FF": "日本社会党", "9AF": "緑風会"},
        )
        assert len(result) == 10

    def test_all_elected(self) -> None:
        """全員が当選フラグ=Trueである."""
        result = _parse_district_template(
            self.WIKITEXT_TEMPLATE,
            {"9E9": "自由民主党", "0FF": "日本社会党", "9AF": "緑風会"},
        )
        assert all(c.is_elected for c in result)

    def test_gouku_district(self) -> None:
        """合区（鳥取・島根）が正しく処理される."""
        wikitext = """
{{参院選挙区当選者
|鳥取・島根=9e9:[[青木一彦]]
}}
"""
        result = _parse_district_template(wikitext, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "青木一彦"
        assert result[0].district_name == "鳥取県・島根県選挙区"
        assert result[0].prefecture == "鳥取県"

    def test_supplementary_election(self) -> None:
        """補欠当選者の:補欠マーカーが除去される."""
        wikitext = """
{{参院選挙区当選者
|北海道=
9e9:[[テスト太郎]]:補欠
}}
"""
        result = _parse_district_template(wikitext, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "テスト太郎"

    def test_empty_template(self) -> None:
        """テンプレートが存在しない場合は空リストを返す."""
        result = _parse_district_template("何もないテキスト", {})
        assert result == []


class TestParseSangiinDistrictWikitable:
    """wikitable形式の選挙区パーステスト."""

    WIKITEXT_WIKITABLE = (
        "=== 選挙区当選者 ===\n"
        "{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}\n"
        '{| class="wikitable" style="margin-right:0px"\n'
        "|-\n"
        "!colspan=4|[[北海道選挙区|北海道]]"
        "!![[青森県選挙区|青森県]]"
        "!!colspan=2|[[東京都選挙区|東京都]]\n"
        "|-\n"
        '|style="background-color:#9e9" |[[板谷順助]]'
        '||style="background-color:#0ff" |[[千葉信]]'
        '||style="background-color:#9e9" |[[井川伊平]]'
        '||style="background-color:#0ff" |[[米田勲]]'
        '||style="background-color:#9e9" |[[佐藤尚武]]'
        '||style="background-color:#9e9" |[[山本利壽]]'
        '||style="background-color:#0ff" |[[椿繁夫]]\n'
        "|}\n"
    )

    def test_parse_hokkaido(self) -> None:
        """北海道の4名が正しく抽出される."""
        result = _parse_district_wikitable(
            self.WIKITEXT_WIKITABLE,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        hokkaido = [c for c in result if "北海道" in c.district_name]
        assert len(hokkaido) == 4
        assert hokkaido[0].name == "板谷順助"
        assert hokkaido[0].district_name == "北海道選挙区"
        assert hokkaido[0].prefecture == "北海道"

    def test_parse_aomori(self) -> None:
        """青森県の1名が正しく抽出される."""
        result = _parse_district_wikitable(
            self.WIKITEXT_WIKITABLE,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        aomori = [c for c in result if "青森" in c.district_name]
        assert len(aomori) == 1
        assert aomori[0].name == "佐藤尚武"
        assert aomori[0].district_name == "青森県選挙区"

    def test_parse_tokyo(self) -> None:
        """東京都の2名が正しく抽出される."""
        result = _parse_district_wikitable(
            self.WIKITEXT_WIKITABLE,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        tokyo = [c for c in result if "東京" in c.district_name]
        assert len(tokyo) == 2
        assert tokyo[0].name == "山本利壽"
        assert tokyo[0].district_name == "東京都選挙区"

    def test_total_count(self) -> None:
        """全体の当選者数が正しい."""
        result = _parse_district_wikitable(
            self.WIKITEXT_WIKITABLE,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        assert len(result) == 7

    def test_section_not_found(self) -> None:
        """セクションが見つからない場合は空リストを返す."""
        result = _parse_district_wikitable(
            "=== 無関係なセクション ===\nテキスト",
            {},
        )
        assert result == []

    def test_alternative_section_headers(self) -> None:
        """「地方区当選者」など別のセクション見出しにも対応する."""
        wikitext = """
=== 地方区当選者 ===
{| class="wikitable"
|-
![[北海道選挙区|北海道]]
|-
|style="background-color:#9e9" |[[テスト太郎]]
|}
"""
        result = _parse_district_wikitable(wikitext, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "テスト太郎"
        assert result[0].district_name == "北海道選挙区"


class TestParseSangiinProportionalTemplate:
    """{{参院比例当選者}}テンプレートのパーステスト."""

    WIKITEXT_PROPORTIONAL = """
=== 比例区当選者 ===
{{政党箱|自由民主党}} {{政党箱|ccf|立憲民主党}}
{{参院比例当選者|
9e9:[[藤井一博]]:特定枠
9e9:[[梶原大介]]:特定枠
0c9:[[石井章]]
ccf:[[辻元清美]]
fdf:[[竹内真二]]
9e9:[[赤松健]]
}}
"""

    def test_parse_proportional_template(self) -> None:
        """比例当選者テンプレートが正しくパースされる."""
        result = _parse_proportional_template(
            self.WIKITEXT_PROPORTIONAL,
            26,
            {
                "9E9": "自由民主党",
                "0C9": "日本維新の会",
                "CCF": "立憲民主党",
                "FDF": "公明党",
            },
        )
        assert len(result) == 6
        assert result[0].name == "藤井一博"
        assert result[0].party_name == "自由民主党"
        assert result[0].district_name == "比例区"
        assert result[0].rank == 1

    def test_rank_order(self) -> None:
        """順位が連番で付与される."""
        result = _parse_proportional_template(
            self.WIKITEXT_PROPORTIONAL,
            26,
            {
                "9E9": "自由民主党",
                "0C9": "日本維新の会",
                "CCF": "立憲民主党",
                "FDF": "公明党",
            },
        )
        ranks = [c.rank for c in result]
        assert ranks == [1, 2, 3, 4, 5, 6]

    def test_tokutei_waku_removed(self) -> None:
        """特定枠マーカーが名前から除去される."""
        result = _parse_proportional_template(
            self.WIKITEXT_PROPORTIONAL,
            26,
            {
                "9E9": "自由民主党",
                "0C9": "日本維新の会",
                "CCF": "立憲民主党",
                "FDF": "公明党",
            },
        )
        assert result[0].name == "藤井一博"
        # 特定枠は名前に含まれない
        assert "特定枠" not in result[0].name

    def test_empty_template(self) -> None:
        """テンプレートが存在しない場合は空リストを返す."""
        result = _parse_proportional_template("テキスト", 26, {})
        assert result == []

    def test_zenkoku_label_for_old_elections(self) -> None:
        """第12回以前はdistrictが「全国区」になる."""
        wikitext = """
{{参院比例当選者|
9e9:[[テスト太郎]]
}}
"""
        result = _parse_proportional_template(wikitext, 5, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].district_name == "全国区"


class TestParseSangiinProportionalWikitable:
    """wikitable形式の全国区/比例区パーステスト."""

    WIKITEXT_ZENKOKU = (
        "=== 全国区当選者 ===\n"
        "{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}\n"
        '{| class="wikitable"\n'
        "|-\n"
        "!1-10\n"
        '|style="background-color:#9e9" |[[田中太郎]]'
        '||style="background-color:#0ff" |[[山田花子]]'
        '||style="background-color:#9e9" |[[佐藤一郎]]'
        '||style="background-color:#0ff" |[[鈴木二郎]]'
        '||style="background-color:#9e9" |[[高橋三郎]]'
        '||style="background-color:#0ff" |[[渡辺四郎]]'
        '||style="background-color:#9e9" |[[伊藤五郎]]'
        '||style="background-color:#0ff" |[[中村六郎]]'
        '||style="background-color:#9e9" |[[小林七郎]]'
        '||style="background-color:#0ff" |[[加藤八郎]]\n'
        "|-\n"
        "!11-20\n"
        '|style="background-color:#9e9" |[[吉田九郎]]'
        '||style="background-color:#0ff" |[[山口十郎]]\n'
        "|}\n"
    )

    def test_parse_first_row(self) -> None:
        """1-10行の当選者が正しく抽出される."""
        result = _parse_proportional_wikitable(
            self.WIKITEXT_ZENKOKU,
            1,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        # 10名 + 2名 = 12名
        assert len(result) == 12
        assert result[0].name == "田中太郎"
        assert result[0].rank == 1
        assert result[0].district_name == "全国区"

    def test_rank_calculation(self) -> None:
        """順位が正しく計算される."""
        result = _parse_proportional_wikitable(
            self.WIKITEXT_ZENKOKU,
            1,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        assert result[0].rank == 1
        assert result[9].rank == 10
        assert result[10].rank == 11
        assert result[11].rank == 12

    def test_hirei_label_for_new_elections(self) -> None:
        """第13回以降はdistrictが「比例区」になる."""
        wikitext = """
=== 比例代表選出議員 ===
{| class="wikitable"
|-
!1-10
|style="background-color:#9e9" |[[テスト太郎]]
|}
"""
        result = _parse_proportional_wikitable(wikitext, 13, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].district_name == "比例区"

    def test_section_not_found(self) -> None:
        """セクションが見つからない場合は空リストを返す."""
        result = _parse_proportional_wikitable(
            "=== 無関係 ===\nテキスト",
            1,
            {},
        )
        assert result == []


class TestParseSangiinWikitext:
    """統合テスト: parse_sangiin_wikitext."""

    WIKITEXT_COMBINED = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}

=== 選挙区当選者 ===
{{参院選挙区当選者
|北海道=
9e9:[[北海太郎]]
|東京=
0ff:[[東京花子]]
}}

=== 比例区当選者 ===
{{参院比例当選者|
9e9:[[比例一郎]]
0ff:[[比例二郎]]
}}
"""

    def test_parse_combined(self) -> None:
        """選挙区+比例区を統合して返す."""
        result = parse_sangiin_wikitext(self.WIKITEXT_COMBINED, 26)
        assert len(result) == 4

        district = [c for c in result if "選挙区" in c.district_name]
        proportional = [c for c in result if c.district_name == "比例区"]
        assert len(district) == 2
        assert len(proportional) == 2

    def test_district_names(self) -> None:
        """選挙区名が正しく設定される."""
        result = parse_sangiin_wikitext(self.WIKITEXT_COMBINED, 26)
        district = [c for c in result if "選挙区" in c.district_name]
        names = {c.district_name for c in district}
        assert "北海道選挙区" in names
        assert "東京都選挙区" in names


class TestParseSangiinEdgeCases:
    """エッジケースのテスト."""

    def test_refnest_in_name(self) -> None:
        """{{Refnest|...}}が名前に含まれる場合は除去される."""
        wikitext = """
{{参院選挙区当選者
|北海道=
9e9:[[板谷順助]]{{Refnest|group="自"|name="自"|text}}
}}
"""
        result = _parse_district_template(wikitext, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "板谷順助"

    def test_ref_tag_in_name(self) -> None:
        """<ref>タグが名前に含まれる場合は除去される."""
        wikitext = """
{{参院選挙区当選者
|北海道=
9e9:[[板谷順助]]<ref>脚注</ref>
}}
"""
        result = _parse_district_template(wikitext, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "板谷順助"

    def test_display_name_wikilink(self) -> None:
        """[[リンク先|表示名]]形式のwikilinkで表示名が使用される."""
        wikitext = """
{{参院選挙区当選者
|北海道=
9e9:[[板谷順助 (政治家)|板谷順助]]
}}
"""
        result = _parse_district_template(wikitext, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "板谷順助"

    def test_fallback_party_resolution(self) -> None:
        """凡例にない色コードはフォールバックで解決される."""
        wikitext = """
{{参院選挙区当選者
|北海道=
F66:[[共産太郎]]
}}
"""
        # 凡例なし → フォールバックから解決
        result = _parse_district_template(wikitext, {})
        assert len(result) == 1
        assert result[0].party_name == "日本共産党"

    def test_unknown_color_code(self) -> None:
        """不明な色コードは「不明(XXX)」と表示される."""
        wikitext = """
{{参院選挙区当選者
|北海道=
ABC:[[不明太郎]]
}}
"""
        result = _parse_district_template(wikitext, {})
        assert len(result) == 1
        assert result[0].party_name == "不明(ABC)"

    def test_wikitable_with_text_align_style(self) -> None:
        """text-align付きのstyle属性が正しく処理される."""
        wikitext = """
=== 全国区当選者 ===
{| class="wikitable"
|-
!1-10
|style="background-color:#9e9;text-align:center;" |[[テスト太郎]]
|}
"""
        result = _parse_proportional_wikitable(wikitext, 1, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "テスト太郎"


class TestNormalizeSangiinDistrict:
    """参議院選挙区名正規化のテスト."""

    def test_hokkaido(self) -> None:
        assert _normalize_sangiin_district("北海道") == "北海道選挙区"

    def test_tokyo(self) -> None:
        assert _normalize_sangiin_district("東京") == "東京都選挙区"

    def test_tokyo_with_suffix(self) -> None:
        assert _normalize_sangiin_district("東京都") == "東京都選挙区"

    def test_aomori(self) -> None:
        assert _normalize_sangiin_district("青森") == "青森県選挙区"

    def test_aomori_with_suffix(self) -> None:
        assert _normalize_sangiin_district("青森県") == "青森県選挙区"

    def test_osaka(self) -> None:
        assert _normalize_sangiin_district("大阪") == "大阪府選挙区"

    def test_kyoto(self) -> None:
        assert _normalize_sangiin_district("京都") == "京都府選挙区"

    def test_gouku(self) -> None:
        assert _normalize_sangiin_district("鳥取・島根") == "鳥取県・島根県選挙区"

    def test_gouku_tokushima_kochi(self) -> None:
        assert _normalize_sangiin_district("徳島・高知") == "徳島県・高知県選挙区"

    def test_already_normalized(self) -> None:
        assert _normalize_sangiin_district("北海道選挙区") == "北海道選挙区"


class TestExtractPrefectureFromSangiinDistrict:
    """都道府県名抽出のテスト."""

    def test_hokkaido(self) -> None:
        assert _extract_prefecture_from_sangiin_district("北海道") == "北海道"

    def test_tokyo(self) -> None:
        assert _extract_prefecture_from_sangiin_district("東京") == "東京都"

    def test_aomori(self) -> None:
        assert _extract_prefecture_from_sangiin_district("青森") == "青森県"

    def test_gouku_returns_first(self) -> None:
        """合区は最初の都道府県を返す."""
        assert _extract_prefecture_from_sangiin_district("鳥取・島根") == "鳥取県"

    def test_with_senkyo_ku_suffix(self) -> None:
        assert _extract_prefecture_from_sangiin_district("北海道選挙区") == "北海道"


class TestNormalizePrefecture:
    """都道府県接尾辞補完のテスト."""

    def test_hokkaido(self) -> None:
        assert normalize_prefecture("北海道") == "北海道"

    def test_tokyo(self) -> None:
        assert normalize_prefecture("東京") == "東京都"

    def test_osaka(self) -> None:
        assert normalize_prefecture("大阪") == "大阪府"

    def test_kyoto(self) -> None:
        assert normalize_prefecture("京都") == "京都府"

    def test_aomori(self) -> None:
        assert normalize_prefecture("青森") == "青森県"

    def test_already_has_suffix(self) -> None:
        assert normalize_prefecture("青森県") == "青森県"
