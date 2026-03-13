"""Wikipedia参議院選挙Wikitextパーサーのユニットテスト."""

# pyright: reportPrivateUsage=false
from src.infrastructure.importers._utils import normalize_prefecture
from src.infrastructure.importers.wikipedia_sangiin_election_wikitext_parser import (
    _extract_prefecture_from_sangiin_district,
    _normalize_sangiin_district,
    _parse_district_template,
    _parse_district_wikitable,
    _parse_hoketsu_list,
    _parse_hoketsu_winners,
    _parse_kuriage_winners,
    _parse_proportional_template,
    _parse_proportional_wikitable,
    _split_template_entries,
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


class TestParseKaisenTeisuTable:
    """改選定数別テーブル形式のパーステスト."""

    WIKITEXT_KAISEN_TEISU = (
        "=== 選挙区当選者 ===\n"
        "{{colorbox|#9E9|自由民主党}} {{colorbox|#fdf|公明党}} "
        "{{colorbox|#f9b|民主党}} {{colorbox|#F66|日本共産党}}\n"
        '{| class="wikitable"\n'
        "|-\n"
        '! colspan="6" | 改選定数3以上\n'
        "|-\n"
        "! [[東京都選挙区|東京都]]\n"
        '| style="background-color:#9E9" | [[保坂三蔵]]\n'
        '| style="background-color:#fdf" | [[山口那津男]]\n'
        '| style="background-color:#f9b" | [[鈴木寛]]\n'
        '| style="background-color:#F66" | [[緒方靖夫]]\n'
        "|-\n"
        "! [[埼玉県選挙区|埼玉県]]\n"
        '| style="background-color:#9E9" | [[関口昌一]]\n'
        '| style="background-color:#f9b" | [[山根隆治]]\n'
        '| style="background-color:#9E9" | [[山本保]]\n'
        "|}\n"
        '{| class="wikitable"\n'
        "|-\n"
        '! colspan="9" | 改選定数2\n'
        "|-\n"
        "! [[北海道選挙区|北海道]]\n"
        '| style="background-color:#9E9" | [[伊達忠一]]\n'
        '| style="background-color:#f9b" | [[小川勝也]]\n'
        "! [[宮城県選挙区|宮城県]]\n"
        '| style="background-color:#f9b" | [[岡崎トミ子]]\n'
        '| style="background-color:#9E9" | [[愛知治郎]]\n'
        "|}\n"
        '{| class="wikitable"\n'
        "|-\n"
        '! colspan="10" | 改選定数1\n'
        "|-\n"
        "! [[青森県選挙区|青森県]]\n"
        '| style="background-color:#9E9" | [[山崎力]]\n'
        "! [[岩手県選挙区|岩手県]]\n"
        '| style="background-color:#f9b" | [[平野達男]]\n'
        "|}\n"
    )

    COLOR_MAP = {
        "9E9": "自由民主党",
        "FDF": "公明党",
        "F9B": "民主党",
        "F66": "日本共産党",
    }

    def test_teisu3_tokyo(self) -> None:
        """改選定数3以上: 東京都の4名が正しく抽出される."""
        result = _parse_district_wikitable(self.WIKITEXT_KAISEN_TEISU, self.COLOR_MAP)
        tokyo = [c for c in result if "東京" in c.district_name]
        assert len(tokyo) == 4
        assert tokyo[0].name == "保坂三蔵"
        assert tokyo[0].party_name == "自由民主党"
        assert tokyo[0].district_name == "東京都選挙区"
        assert tokyo[0].prefecture == "東京都"
        assert tokyo[3].name == "緒方靖夫"
        assert tokyo[3].party_name == "日本共産党"

    def test_teisu3_saitama(self) -> None:
        """改選定数3以上: 埼玉県の3名が正しく抽出される."""
        result = _parse_district_wikitable(self.WIKITEXT_KAISEN_TEISU, self.COLOR_MAP)
        saitama = [c for c in result if "埼玉" in c.district_name]
        assert len(saitama) == 3
        assert saitama[0].name == "関口昌一"
        assert saitama[0].district_name == "埼玉県選挙区"

    def test_teisu2_multiple_districts_in_row(self) -> None:
        """改選定数2: 同一テーブル行内の複数選挙区が正しく分離される."""
        result = _parse_district_wikitable(self.WIKITEXT_KAISEN_TEISU, self.COLOR_MAP)
        hokkaido = [c for c in result if "北海道" in c.district_name]
        miyagi = [c for c in result if "宮城" in c.district_name]
        assert len(hokkaido) == 2
        assert len(miyagi) == 2
        assert hokkaido[0].name == "伊達忠一"
        assert miyagi[0].name == "岡崎トミ子"

    def test_teisu1_single_candidates(self) -> None:
        """改選定数1: 各選挙区1名ずつが正しく抽出される."""
        result = _parse_district_wikitable(self.WIKITEXT_KAISEN_TEISU, self.COLOR_MAP)
        aomori = [c for c in result if "青森" in c.district_name]
        iwate = [c for c in result if "岩手" in c.district_name]
        assert len(aomori) == 1
        assert len(iwate) == 1
        assert aomori[0].name == "山崎力"
        assert iwate[0].name == "平野達男"

    def test_total_count(self) -> None:
        """全テーブルの合計当選者数が正しい（4+3+2+2+1+1=13）."""
        result = _parse_district_wikitable(self.WIKITEXT_KAISEN_TEISU, self.COLOR_MAP)
        assert len(result) == 13


class TestParseKuriageWinners:
    """繰上当選パーサーのテスト."""

    WIKITEXT_KURIAGE = (
        "==== 繰上当選 ====\n"
        '{| class="wikitable"\n'
        "|-\n"
        "!年!!月日!!新旧別!!当選者!!所属党派!!欠員!!欠員事由\n"
        "|-\n"
        '| align="right" | 2001\n'
        '| align="right" | 10.3\n'
        '| align="center" | 元\n'
        '| style="background-color:#9E9" | [[中島啓雄]] || 自由民主党\n'
        '| style="background-color:#9E9" | [[高祖憲治]]\n'
        "| 2001.9.25辞職\n"
        "|-\n"
        '| align="right" | 2003\n'
        '| align="right" | 4.28\n'
        '| align="center" | 新\n'
        '| style="background-color:#fdf" | [[ツルネン・マルテイ]] || 民主党\n'
        '| style="background-color:#fdf" | [[中村敦夫]]\n'
        "| 2003.3.31辞職\n"
        "|}\n"
    )

    def test_parse_kuriage_basic(self) -> None:
        """繰上当選者が正しく抽出される."""
        result = _parse_kuriage_winners(
            self.WIKITEXT_KURIAGE,
            {"9E9": "自由民主党", "FDF": "公明党"},
        )
        assert len(result) == 2
        assert result[0].name == "中島啓雄"
        assert result[0].party_name == "自由民主党"
        assert result[1].name == "ツルネン・マルテイ"
        assert result[1].party_name == "民主党"

    def test_kuriage_empty_district(self) -> None:
        """繰上当選者のdistrict_nameは空文字."""
        result = _parse_kuriage_winners(
            self.WIKITEXT_KURIAGE,
            {"9E9": "自由民主党"},
        )
        assert all(c.district_name == "" for c in result)
        assert all(c.prefecture == "" for c in result)

    def test_kuriage_section_not_found(self) -> None:
        """繰上当選セクションがない場合は空リスト."""
        result = _parse_kuriage_winners("=== 選挙区当選者 ===\nテキスト", {})
        assert result == []

    def test_kuriage_all_elected(self) -> None:
        """繰上当選者は全員is_elected=True."""
        result = _parse_kuriage_winners(
            self.WIKITEXT_KURIAGE,
            {"9E9": "自由民主党"},
        )
        assert all(c.is_elected for c in result)


class TestParseSangiinWikitextWithKuriage:
    """統合テスト: parse_sangiin_wikitextが繰上当選を含む."""

    WIKITEXT_WITH_KURIAGE = (
        "{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}\n"
        "\n"
        "=== 選挙区当選者 ===\n"
        "{{参院選挙区当選者\n"
        "|北海道=\n"
        "9e9:[[北海太郎]]\n"
        "}}\n"
        "\n"
        "=== 比例区当選者 ===\n"
        "{{参院比例当選者|\n"
        "9e9:[[比例一郎]]\n"
        "}}\n"
        "\n"
        "==== 繰上当選 ====\n"
        '{| class="wikitable"\n'
        "|-\n"
        "!年!!月日!!新旧別!!当選者!!所属党派!!欠員!!欠員事由\n"
        "|-\n"
        '| align="right" | 2001\n'
        '| align="right" | 10.3\n'
        '| align="center" | 元\n'
        '| style="background-color:#9E9" | [[繰上太郎]] || 自由民主党\n'
        '| style="background-color:#9E9" | [[欠員太郎]]\n'
        "| 辞職\n"
        "|}\n"
    )

    def test_combined_with_kuriage(self) -> None:
        """選挙区+比例区+繰上当選を統合して返す."""
        result = parse_sangiin_wikitext(self.WIKITEXT_WITH_KURIAGE, 26)
        assert len(result) == 3

        district = [c for c in result if "選挙区" in c.district_name]
        proportional = [c for c in result if c.district_name == "比例区"]
        kuriage = [c for c in result if c.district_name == ""]

        assert len(district) == 1
        assert len(proportional) == 1
        assert len(kuriage) == 1
        assert kuriage[0].name == "繰上太郎"


class TestKaisenTeisuBackwardCompatibility:
    """改選定数別テーブル対応が既存の横並びヘッダ形式と互換性を維持するテスト."""

    WIKITEXT_HORIZONTAL = (
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

    def test_horizontal_format_still_works(self) -> None:
        """既存の横並びヘッダ形式が引き続き正しく動作する."""
        result = _parse_district_wikitable(
            self.WIKITEXT_HORIZONTAL,
            {"9E9": "自由民主党", "0FF": "日本社会党"},
        )
        assert len(result) == 7
        hokkaido = [c for c in result if "北海道" in c.district_name]
        assert len(hokkaido) == 4


class TestParseTeisuBetsuTable:
    """定数別テーブル（N人区）形式のパーステスト."""

    WIKITEXT_TEISU_BETSU = (
        "=== 地方区当選者 ===\n"
        "{{colorbox|#9ca|自由党}} {{colorbox|#bbf|民主党}} "
        "{{colorbox|#0ff|日本社会党}}\n"
        '{| class="wikitable" style="margin-right:0px;"\n'
        "|-\n"
        '! colspan="10" | 4人区\n'
        "|-\n"
        '! rowspan="2" | [[北海道選挙区|北海道]]\n'
        '| style="background-color:#9ca" | [[板谷順助]]\n'
        '| style="background-color:#0ff" | [[千葉信]]\n'
        '! rowspan="2" | [[東京都選挙区|東京都]]\n'
        '| style="background-color:#bbf" | [[桜内辰郎]]\n'
        '| style="background-color:#0ff" | [[吉川末次郎]]\n'
        "|-\n"
        '| style="background-color:#bbf" | [[若木勝蔵]]\n'
        '| style="background-color:#9ca" | [[堀末治]]\n'
        '| style="background-color:#0ff" | [[島清]]\n'
        '| style="background-color:#9ca" | [[黒川武雄]]\n'
        "|}\n"
    )

    COLOR_MAP = {
        "9CA": "自由党",
        "BBF": "民主党",
        "0FF": "日本社会党",
    }

    def test_first_row_hokkaido(self) -> None:
        """上段: 北海道の2名が正しく抽出される."""
        result = _parse_district_wikitable(self.WIKITEXT_TEISU_BETSU, self.COLOR_MAP)
        hokkaido = [c for c in result if "北海道" in c.district_name]
        assert len(hokkaido) == 4
        assert hokkaido[0].name == "板谷順助"
        assert hokkaido[0].party_name == "自由党"
        assert hokkaido[0].district_name == "北海道選挙区"
        assert hokkaido[0].prefecture == "北海道"

    def test_first_row_tokyo(self) -> None:
        """上段: 東京都の2名が正しく抽出される."""
        result = _parse_district_wikitable(self.WIKITEXT_TEISU_BETSU, self.COLOR_MAP)
        tokyo = [c for c in result if "東京" in c.district_name]
        assert len(tokyo) == 4
        assert tokyo[0].name == "桜内辰郎"
        assert tokyo[0].party_name == "民主党"
        assert tokyo[0].district_name == "東京都選挙区"

    def test_second_row_assignment(self) -> None:
        """下段: rowspan 2行目の候補者が正しいdistrictに割り当てられる."""
        result = _parse_district_wikitable(self.WIKITEXT_TEISU_BETSU, self.COLOR_MAP)
        hokkaido = [c for c in result if "北海道" in c.district_name]
        tokyo = [c for c in result if "東京" in c.district_name]
        # 上段2 + 下段2 = 4
        assert len(hokkaido) == 4
        assert len(tokyo) == 4
        # 下段の北海道候補者
        assert hokkaido[2].name == "若木勝蔵"
        assert hokkaido[3].name == "堀末治"
        # 下段の東京候補者
        assert tokyo[2].name == "島清"
        assert tokyo[3].name == "黒川武雄"

    def test_total_count(self) -> None:
        """全体の当選者数が正しい（北海道4+東京4=8）."""
        result = _parse_district_wikitable(self.WIKITEXT_TEISU_BETSU, self.COLOR_MAP)
        assert len(result) == 8

    def test_multiple_teisu_tables(self) -> None:
        """複数の定数テーブル（4人区+2人区）を統合してパースする."""
        wikitext = (
            "=== 地方区当選者 ===\n"
            '{| class="wikitable"\n'
            "|-\n"
            '! colspan="6" | 4人区\n'
            "|-\n"
            "! [[北海道選挙区|北海道]]\n"
            '| style="background-color:#9ca" | [[候補A]]\n'
            '| style="background-color:#0ff" | [[候補B]]\n'
            "|}\n"
            '{| class="wikitable"\n'
            "|-\n"
            '! colspan="6" | 2人区\n'
            "|-\n"
            "! [[青森県選挙区|青森県]]\n"
            '| style="background-color:#9ca" | [[候補C]]\n'
            "|}\n"
        )
        result = _parse_district_wikitable(
            wikitext, {"9CA": "自由党", "0FF": "日本社会党"}
        )
        assert len(result) == 3
        hokkaido = [c for c in result if "北海道" in c.district_name]
        aomori = [c for c in result if "青森" in c.district_name]
        assert len(hokkaido) == 2
        assert len(aomori) == 1


class TestProportionalWidthAttribute:
    """width属性付きrank headerのパーステスト."""

    WIKITEXT_WIDTH_RANK = (
        "=== 全国区当選者 ===\n"
        "{{colorbox|#9E9|自由民主党}} {{colorbox|#bbf|民主党}}\n"
        '{| class="wikitable" style="margin-right:0px;"\n'
        "|-\n"
        '! width="70px" | 1-10\n'
        '|style="background-color:#9e9" |[[星一]]\n'
        '|style="background-color:#bbf" |[[柳川宗左衛門]]\n'
        "|-\n"
        "!11-20\n"
        '|style="background-color:#9e9" |[[堀越儀郎]]\n'
        "|}\n"
    )

    def test_width_attribute_rank_header(self) -> None:
        """! width="70px" | 1-10 形式のrank headerが正しく処理される."""
        result = _parse_proportional_wikitable(
            self.WIKITEXT_WIDTH_RANK,
            1,
            {"9E9": "自由民主党", "BBF": "民主党"},
        )
        assert len(result) == 3
        assert result[0].name == "星一"
        assert result[0].rank == 1
        assert result[0].district_name == "全国区"
        assert result[1].name == "柳川宗左衛門"
        assert result[1].rank == 2

    def test_mixed_rank_headers(self) -> None:
        """width属性付きと属性なしのrank headerが混在しても正しく処理される."""
        result = _parse_proportional_wikitable(
            self.WIKITEXT_WIDTH_RANK,
            1,
            {"9E9": "自由民主党", "BBF": "民主党"},
        )
        # 11-20行の候補者
        assert result[2].name == "堀越儀郎"
        assert result[2].rank == 11

    def test_existing_format_still_works(self) -> None:
        """既存の !1-10 形式が引き続き正しく動作する."""
        wikitext = (
            "=== 全国区当選者 ===\n"
            '{| class="wikitable"\n'
            "|-\n"
            "!1-10\n"
            '|style="background-color:#9e9" |[[テスト太郎]]\n'
            "|}\n"
        )
        result = _parse_proportional_wikitable(wikitext, 1, {"9E9": "自由民主党"})
        assert len(result) == 1
        assert result[0].name == "テスト太郎"
        assert result[0].rank == 1


class TestParseHoketsuWinners:
    """補欠当選パーサーのテスト."""

    WIKITEXT_HOKETSU = (
        "==== 補欠当選 ====\n"
        '{| class="wikitable"\n'
        "|-\n"
        "!年!!月日!!選挙区!!当選者!!所属党派!!欠員!!所属党派!!欠員事由\n"
        "|-\n"
        '| align="right" rowspan="2" | 1947\n'
        '| align="right" | 8.1\n'
        "! 滋賀県\n"
        '| style="background-color:#9CA" | [[西川甚五郎]] || 日本自由党\n'
        '| style="background-color:#89E" | [[猪飼清六]] || 緑風会\n'
        "| 1947.7.2辞職\n"
        "|-\n"
        '| align="right" | 10.15\n'
        "! 宮城県\n"
        '| style="background-color:#0FF" | [[岡田宗司]] || 日本社会党\n'
        '| style="background-color:#9CA" | [[内海安吉]] || 日本自由党\n'
        "| 1947.9.15死去\n"
        "|}\n"
    )

    def test_parse_hoketsu_basic(self) -> None:
        """補欠当選者が正しく抽出される."""
        result = _parse_hoketsu_winners(
            self.WIKITEXT_HOKETSU,
            {"9CA": "日本自由党", "89E": "緑風会", "0FF": "日本社会党"},
        )
        assert len(result) == 2
        assert result[0].name == "西川甚五郎"
        assert result[0].party_name == "日本自由党"
        assert result[1].name == "岡田宗司"
        assert result[1].party_name == "日本社会党"

    def test_hoketsu_district(self) -> None:
        """補欠当選者の選挙区が正しく設定される."""
        result = _parse_hoketsu_winners(
            self.WIKITEXT_HOKETSU,
            {"9CA": "日本自由党", "89E": "緑風会", "0FF": "日本社会党"},
        )
        assert result[0].district_name == "滋賀県選挙区"
        assert result[0].prefecture == "滋賀県"
        assert result[1].district_name == "宮城県選挙区"
        assert result[1].prefecture == "宮城県"

    def test_hoketsu_section_not_found(self) -> None:
        """補欠当選セクションがない場合は空リスト."""
        result = _parse_hoketsu_winners("=== 選挙区当選者 ===\nテキスト", {})
        assert result == []

    def test_hoketsu_all_elected(self) -> None:
        """補欠当選者は全員is_elected=True."""
        result = _parse_hoketsu_winners(
            self.WIKITEXT_HOKETSU,
            {"9CA": "日本自由党"},
        )
        assert all(c.is_elected for c in result)


class TestParseSangiinWikitextWithHoketsu:
    """統合テスト: parse_sangiin_wikitextが補欠当選を含む."""

    WIKITEXT_WITH_HOKETSU = (
        "{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}\n"
        "\n"
        "=== 地方区当選者 ===\n"
        "{{参院選挙区当選者\n"
        "|北海道=\n"
        "9e9:[[北海太郎]]\n"
        "}}\n"
        "\n"
        "=== 全国区当選者 ===\n"
        '{| class="wikitable"\n'
        "|-\n"
        '! width="70px" | 1-10\n'
        '|style="background-color:#9e9" |[[全国一郎]]\n'
        "|}\n"
        "\n"
        "==== 補欠当選 ====\n"
        '{| class="wikitable"\n'
        "|-\n"
        "!年!!月日!!選挙区!!当選者!!所属党派!!欠員!!欠員事由\n"
        "|-\n"
        "| 1947 | 8.1\n"
        "! 滋賀県\n"
        '| style="background-color:#9E9" | [[補欠太郎]] || 自由民主党\n'
        '| style="background-color:#9E9" | [[欠員太郎]]\n'
        "| 辞職\n"
        "|}\n"
    )

    def test_combined_with_hoketsu(self) -> None:
        """地方区+全国区+補欠当選を統合して返す."""
        result = parse_sangiin_wikitext(self.WIKITEXT_WITH_HOKETSU, 1)
        assert len(result) == 3

        district = [c for c in result if "選挙区" in c.district_name]
        zenkoku = [c for c in result if c.district_name == "全国区"]
        hoketsu = [
            c
            for c in result
            if c.district_name not in ("全国区", "")
            and "選挙区" in c.district_name
            and c.name == "補欠太郎"
        ]

        assert len(district) == 2  # 北海太郎 + 補欠太郎
        assert len(zenkoku) == 1
        assert zenkoku[0].name == "全国一郎"
        assert zenkoku[0].rank == 1
        assert len(hoketsu) == 1
        assert hoketsu[0].district_name == "滋賀県選挙区"


class TestMultiHeaderHorizontalTable:
    """複数ヘッダ行を持つ横並びテーブルのパーステスト（第9回〜第12回形式）."""

    WIKITEXT_MULTI_HEADER = (
        "=== この選挙で選挙区当選 ===\n"
        "{{colorbox|#9E9|自民党}} {{colorbox|#0ff|社会党}}\n"
        '{| class="wikitable" style="margin-right:0px"\n'
        "|-\n"
        "!colspan=2|[[北海道選挙区|北海道]]"
        "!![[青森県選挙区|青森県]]"
        "!![[岩手県選挙区|岩手県]]\n"
        "|-\n"
        '|style="background-color:#9e9" |[[北海一郎]]'
        '||style="background-color:#0ff" |[[北海二郎]]'
        '||style="background-color:#9e9" |[[青森太郎]]'
        '||style="background-color:#0ff" |[[岩手太郎]]\n'
        "|-\n"
        "!colspan=2|[[福島県選挙区|福島県]]"
        "!![[茨城県選挙区|茨城県]]"
        "!![[大阪府選挙区|大阪府]]\n"
        "|-\n"
        '|style="background-color:#0ff" |[[福島一郎]]'
        '||style="background-color:#9e9" |[[福島二郎]]'
        '||style="background-color:#9e9" |[[茨城太郎]]'
        '||style="background-color:#0ff" |[[大阪太郎]]\n'
        "|}\n"
    )

    COLOR_MAP = {"9E9": "自民党", "0FF": "社会党"}

    def test_first_block_districts(self) -> None:
        """最初のヘッダブロックの選挙区が正しくマッピングされる."""
        result = _parse_district_wikitable(self.WIKITEXT_MULTI_HEADER, self.COLOR_MAP)
        hokkaido = [c for c in result if "北海道" in c.district_name]
        aomori = [c for c in result if "青森" in c.district_name]
        iwate = [c for c in result if "岩手" in c.district_name]
        assert len(hokkaido) == 2
        assert len(aomori) == 1
        assert len(iwate) == 1
        assert hokkaido[0].name == "北海一郎"
        assert aomori[0].name == "青森太郎"

    def test_second_block_districts(self) -> None:
        """2番目のヘッダブロックの選挙区が正しくマッピングされる."""
        result = _parse_district_wikitable(self.WIKITEXT_MULTI_HEADER, self.COLOR_MAP)
        fukushima = [c for c in result if "福島" in c.district_name]
        ibaraki = [c for c in result if "茨城" in c.district_name]
        osaka = [c for c in result if "大阪" in c.district_name]
        assert len(fukushima) == 2
        assert len(ibaraki) == 1
        assert len(osaka) == 1
        assert fukushima[0].name == "福島一郎"
        assert ibaraki[0].name == "茨城太郎"
        assert osaka[0].name == "大阪太郎"

    def test_total_count(self) -> None:
        """全ブロック合計の当選者数が正しい."""
        result = _parse_district_wikitable(self.WIKITEXT_MULTI_HEADER, self.COLOR_MAP)
        assert len(result) == 8

    def test_backward_compatible_with_single_header(self) -> None:
        """単一ヘッダ行のテーブルが引き続き正しく動作する."""
        wikitext = (
            "=== 選挙区当選者 ===\n"
            '{| class="wikitable"\n'
            "|-\n"
            "!colspan=2|[[北海道選挙区|北海道]]"
            "!![[青森県選挙区|青森県]]\n"
            "|-\n"
            '|style="background-color:#9e9" |[[候補A]]'
            '||style="background-color:#0ff" |[[候補B]]'
            '||style="background-color:#9e9" |[[候補C]]\n'
            "|}\n"
        )
        result = _parse_district_wikitable(wikitext, self.COLOR_MAP)
        assert len(result) == 3
        hokkaido = [c for c in result if "北海道" in c.district_name]
        assert len(hokkaido) == 2


class TestHoketsuListFormat:
    """補欠当選リスト形式のパーステスト（第2回〜第12回形式）."""

    WIKITEXT_HOKETSU_LIST = (
        "=== 補欠当選 ===\n"
        "* 和歌山選挙区 [[徳川頼貞]]（1954.4.17死去）"
        "→[[野村吉三郎]]（1954.6.3補欠当選）\n"
        "* 島根選挙区 [[大達茂雄]]（1955.9.25死去）"
        "→[[佐野広]]（1955.11.11補欠当選）\n"
        "* 大阪選挙区 [[中山福蔵]]（1957.3.5死去）"
        "→[[大川光三]]（1957.4.23補欠当選）\n"
    )

    def test_parse_hoketsu_list_basic(self) -> None:
        """リスト形式の補欠当選者が正しく抽出される."""
        result = _parse_hoketsu_winners(self.WIKITEXT_HOKETSU_LIST, {})
        assert len(result) == 3
        assert result[0].name == "野村吉三郎"
        assert result[1].name == "佐野広"
        assert result[2].name == "大川光三"

    def test_hoketsu_list_district(self) -> None:
        """補欠当選者の選挙区が正しく設定される."""
        result = _parse_hoketsu_winners(self.WIKITEXT_HOKETSU_LIST, {})
        assert result[0].district_name == "和歌山県選挙区"
        assert result[0].prefecture == "和歌山県"
        assert result[1].district_name == "島根県選挙区"
        assert result[2].district_name == "大阪府選挙区"

    def test_hoketsu_list_display_name(self) -> None:
        """[[リンク先|表示名]]形式のwikilinkで表示名が使用される."""
        section_text = (
            "* 秋田選挙区 [[鈴木一 (政治家)|鈴木一]]"
            "（辞職）→[[松野孝一 (政治家)|松野孝一]]（補欠当選）\n"
        )
        result = _parse_hoketsu_list(section_text)
        assert len(result) == 1
        assert result[0].name == "松野孝一"

    def test_hoketsu_list_all_elected(self) -> None:
        """リスト形式の補欠当選者は全員is_elected=True."""
        result = _parse_hoketsu_winners(self.WIKITEXT_HOKETSU_LIST, {})
        assert all(c.is_elected for c in result)

    def test_wikitable_format_preferred(self) -> None:
        """wikitable形式が存在する場合はそちらが優先される."""
        wikitext = (
            "==== 補欠当選 ====\n"
            '{| class="wikitable"\n'
            "|-\n"
            "!年!!月日!!選挙区!!当選者!!所属党派!!欠員!!欠員事由\n"
            "|-\n"
            "| 1947 | 8.1\n"
            "! 滋賀県\n"
            '| style="background-color:#9CA" | [[テスト太郎]] || テスト党\n'
            '| style="background-color:#9CA" | [[欠員太郎]]\n'
            "| 辞職\n"
            "|}\n"
        )
        result = _parse_hoketsu_winners(wikitext, {"9CA": "テスト党"})
        assert len(result) == 1
        assert result[0].name == "テスト太郎"


class TestSplitTemplateEntries:
    """テンプレートエントリ分割のテスト."""

    def test_single_entry(self) -> None:
        """単一エントリは1要素リストを返す."""
        result = _split_template_entries("78d:[[中山福蔵]]")
        assert result == ["78d:[[中山福蔵]]"]

    def test_multi_entries(self) -> None:
        """複数エントリが|で分割される."""
        result = _split_template_entries("78d:[[中山福蔵]]|cff:[[亀田得治]]")
        assert len(result) == 2
        assert result[0] == "78d:[[中山福蔵]]"
        assert result[1] == "cff:[[亀田得治]]"

    def test_wikilink_pipe_preserved(self) -> None:
        """[[リンク先|表示名]]内の|は分割されない."""
        result = _split_template_entries("78d:[[佐藤 (政治家)|佐藤]]")
        assert len(result) == 1
        assert result[0] == "78d:[[佐藤 (政治家)|佐藤]]"

    def test_template_multi_entry_integration(self) -> None:
        """テンプレートパーサーが複数エントリ行を正しく処理する."""
        wikitext = """
{{参院選挙区当選者
|大阪=
6cf:[[森下政一]]
78d:[[中山福蔵]]|cff:[[亀田得治]]
}}
"""
        result = _parse_district_template(
            wikitext,
            {"6CF": "右派社会党", "78D": "緑風会", "CFF": "左派社会党"},
        )
        osaka = [c for c in result if "大阪" in c.district_name]
        assert len(osaka) == 3
        names = [c.name for c in osaka]
        assert "森下政一" in names
        assert "中山福蔵" in names
        assert "亀田得治" in names


class TestRankHeaderWithIchi:
    """「位」接尾辞付き順位ヘッダのパーステスト."""

    def test_rank_with_ichi_suffix(self) -> None:
        """!1位-10位 形式のrank headerが正しく処理される."""
        wikitext = (
            "=== この選挙で全国区当選 ===\n"
            '{| class="wikitable"\n'
            "|-\n"
            "!1位-10位\n"
            '|style="background-color:#9e9" |[[田中太郎]]'
            '||style="background-color:#0ff" |[[山田花子]]\n'
            "|-\n"
            "!11位-20位\n"
            '|style="background-color:#9e9" |[[佐藤一郎]]\n'
            "|}\n"
        )
        result = _parse_proportional_wikitable(
            wikitext, 9, {"9E9": "自民党", "0FF": "社会党"}
        )
        assert len(result) == 3
        assert result[0].name == "田中太郎"
        assert result[0].rank == 1
        assert result[1].name == "山田花子"
        assert result[1].rank == 2
        assert result[2].name == "佐藤一郎"
        assert result[2].rank == 11
        assert result[0].district_name == "全国区"
