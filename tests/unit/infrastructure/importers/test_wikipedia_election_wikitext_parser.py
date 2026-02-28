"""WikipediaElectionWikitextParserのユニットテスト."""

from src.infrastructure.importers.wikipedia_election_wikitext_parser import (
    extract_color_party_mapping,
    extract_name_from_wikilink,
    parse_all_wikitext,
    parse_proportional_wikitext,
    parse_wikitext,
)


class TestExtractColorPartyMapping:
    """凡例パースのテスト."""

    def test_colorbox_pattern(self) -> None:
        wikitext = (
            "{{colorbox|#9E9|自由民主党}} "
            "{{colorbox|#f9b|民主党}} "
            "{{colorbox|#F6C|新進党}}"
        )
        result = extract_color_party_mapping(wikitext)
        assert result["9E9"] == "自由民主党"
        assert result["F9B"] == "民主党"
        assert result["F6C"] == "新進党"

    def test_color_normalization(self) -> None:
        wikitext = "{{colorbox|9e9|自由民主党}} {{colorbox|#F9B|民主党}}"
        result = extract_color_party_mapping(wikitext)
        assert result["9E9"] == "自由民主党"
        assert result["F9B"] == "民主党"

    def test_party_box_pattern(self) -> None:
        wikitext = "{{政党箱|#ABD|自由党}}"
        result = extract_color_party_mapping(wikitext)
        assert result["ABD"] == "自由党"

    def test_empty_wikitext(self) -> None:
        assert extract_color_party_mapping("") == {}


class TestExtractNameFromWikilink:
    """Wikilink名前抽出のテスト."""

    def test_simple_link(self) -> None:
        assert extract_name_from_wikilink("[[横路孝弘]]") == "横路孝弘"

    def test_display_name(self) -> None:
        assert (
            extract_name_from_wikilink("[[横路孝弘 (政治家)|横路孝弘]]") == "横路孝弘"
        )

    def test_with_ref_tag(self) -> None:
        text = '[[田中太郎]]<ref name="test">出典</ref>'
        assert extract_name_from_wikilink(text) == "田中太郎"

    def test_with_self_closing_ref(self) -> None:
        text = '[[田中太郎]]<ref name="test" />'
        assert extract_name_from_wikilink(text) == "田中太郎"

    def test_with_refnest(self) -> None:
        text = "[[田中太郎]]{{Refnest|group=注|何か{{内側}}の脚注}}"
        assert extract_name_from_wikilink(text) == "田中太郎"

    def test_plain_text(self) -> None:
        assert extract_name_from_wikilink("横路孝弘") == "横路孝弘"


class TestParseFormatA:
    """形式A（第41回）パースのテスト."""

    WIKITEXT_41 = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#f9b|新進党}}
{{colorbox|#F6C|民主党}} {{colorbox|#0FF|社会民主党}}
{{colorbox|#F66|日本共産党}} {{colorbox|#CCF|新党さきがけ}}

{{衆院小選挙区当選者
|北海道=
f9b:[[横路孝弘]]
F6C:[[長内順一]]
9E9:[[石崎岳]]
|東京都=
9E9:[[与謝野馨]]
f9b:[[鳩山由紀夫]]
F6C:[[松本善明]]
|北海道増減=
何かのデータ
}}
"""

    def test_parse_hokkaido(self) -> None:
        result = parse_wikitext(self.WIKITEXT_41, 41)
        hokkaido = [c for c in result if c.prefecture == "北海道"]
        assert len(hokkaido) == 3
        assert hokkaido[0].name == "横路孝弘"
        assert hokkaido[0].district_name == "北海道1区"
        assert hokkaido[0].party_name == "新進党"
        assert hokkaido[1].name == "長内順一"
        assert hokkaido[1].district_name == "北海道2区"
        assert hokkaido[1].party_name == "民主党"
        assert hokkaido[2].name == "石崎岳"
        assert hokkaido[2].district_name == "北海道3区"
        assert hokkaido[2].party_name == "自由民主党"

    def test_parse_tokyo(self) -> None:
        result = parse_wikitext(self.WIKITEXT_41, 41)
        tokyo = [c for c in result if c.prefecture == "東京都"]
        assert len(tokyo) == 3
        assert tokyo[0].name == "与謝野馨"
        assert tokyo[0].district_name == "東京都1区"
        assert tokyo[0].party_name == "自由民主党"

    def test_skip_increase_decrease_section(self) -> None:
        result = parse_wikitext(self.WIKITEXT_41, 41)
        total = len(result)
        assert total == 6  # 北海道3 + 東京3

    def test_candidate_defaults(self) -> None:
        result = parse_wikitext(self.WIKITEXT_41, 41)
        for c in result:
            assert c.total_votes == 0
            assert c.rank == 1
            assert c.is_elected is True


class TestParseFormatB:
    """形式B（第42-44回）パースのテスト."""

    WIKITEXT_42 = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#f9b|民主党}} {{colorbox|#FDF|公明党}}

{{衆議院小選挙区当選者(第49回まで)
|北海道1区色=f9b|北海道1区=[[横路孝弘]]
|北海道2区色=9E9|北海道2区=[[吉川貴盛]]
|東京都1区色=9E9|東京都1区=[[与謝野馨]]
|東京都2区色=f9b|東京都2区=[[中山義活]]
|大阪府1区色=FDF|大阪府1区=[[公明太郎]]
}}
"""

    def test_parse_basic(self) -> None:
        result = parse_wikitext(self.WIKITEXT_42, 42)
        assert len(result) == 5

    def test_party_resolution(self) -> None:
        result = parse_wikitext(self.WIKITEXT_42, 42)
        assert result[0].name == "横路孝弘"
        assert result[0].party_name == "民主党"
        assert result[0].district_name == "北海道1区"
        assert result[0].prefecture == "北海道"

    def test_tokyo_district(self) -> None:
        result = parse_wikitext(self.WIKITEXT_42, 42)
        tokyo = [c for c in result if c.prefecture == "東京都"]
        assert len(tokyo) == 2
        assert tokyo[0].district_name == "東京都1区"

    def test_osaka_district(self) -> None:
        result = parse_wikitext(self.WIKITEXT_42, 42)
        osaka = [c for c in result if c.prefecture == "大阪府"]
        assert len(osaka) == 1
        assert osaka[0].party_name == "公明党"

    def test_candidate_defaults(self) -> None:
        result = parse_wikitext(self.WIKITEXT_42, 42)
        for c in result:
            assert c.total_votes == 0
            assert c.rank == 1
            assert c.is_elected is True

    def test_also_works_for_43_and_44(self) -> None:
        result_43 = parse_wikitext(self.WIKITEXT_42, 43)
        result_44 = parse_wikitext(self.WIKITEXT_42, 44)
        assert len(result_43) == 5
        assert len(result_44) == 5


class TestParseFormatC:
    """形式C（第1-40回、中選挙区制wikitable）パースのテスト."""

    WIKITEXT_40 = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}
{{colorbox|#0cf|新生党}} {{colorbox|#fdf|公明党}}
{{colorbox|#FFF|無所属}}

=== 当選者 ===
{| class="wikitable" style="font-size:80%; margin-right:0px"
! rowspan="2"  | [[北海道]]
! [[北海道第1区 (中選挙区)|1区]]
|style="background-color:#9e9" | [[町村信孝]]
|style="background-color:#fdf" | [[長内順一]]
|style="background-color:#0ff" | [[伊東秀子]]
|style="background-color:#9e9" | [[佐藤静雄 (衆議院議員)|佐藤静雄]]
! [[北海道第2区 (中選挙区)|2区]]
|style="background-color:#9e9" | [[今津寛]]
|style="background-color:#0ff" | [[五十嵐広三]]
|-
! [[青森県]]
! [[青森県第1区 (中選挙区)|1区]]
|style="background-color:#9e9" | [[田名部匡省]]
|style="background-color:#9e9" | [[大島理森]]
|style="background-color:#0ff" | [[今村修]]
|
|}
"""

    def test_parse_total(self) -> None:
        result = parse_wikitext(self.WIKITEXT_40, 40)
        assert len(result) == 9

    def test_hokkaido_1ku(self) -> None:
        result = parse_wikitext(self.WIKITEXT_40, 40)
        hok1 = [c for c in result if c.district_name == "北海道1区"]
        assert len(hok1) == 4
        assert hok1[0].name == "町村信孝"
        assert hok1[0].party_name == "自由民主党"
        assert hok1[0].prefecture == "北海道"

    def test_hokkaido_2ku(self) -> None:
        result = parse_wikitext(self.WIKITEXT_40, 40)
        hok2 = [c for c in result if c.district_name == "北海道2区"]
        assert len(hok2) == 2
        assert hok2[0].name == "今津寛"

    def test_display_name(self) -> None:
        result = parse_wikitext(self.WIKITEXT_40, 40)
        sato = [c for c in result if c.name == "佐藤静雄"]
        assert len(sato) == 1

    def test_aomori(self) -> None:
        result = parse_wikitext(self.WIKITEXT_40, 40)
        aomori = [c for c in result if c.prefecture == "青森県"]
        assert len(aomori) == 3
        assert aomori[0].district_name == "青森県1区"

    def test_candidate_defaults(self) -> None:
        result = parse_wikitext(self.WIKITEXT_40, 40)
        for c in result:
            assert c.total_votes == 0
            assert c.rank == 1
            assert c.is_elected is True

    def test_no_proportional_for_old_elections(self) -> None:
        """第40回以前は比例代表なし."""
        result = parse_proportional_wikitext(self.WIKITEXT_40, 40)
        assert result == []

    WIKITEXT_OLD_SECTION = """
{{colorbox|#bdb|立憲政友会}} {{colorbox|#fff|無所属}}

== この選挙で当選 ==
{| class="wikitable" style="font-size:80%; margin-right:0px"
![[北海道]]
!札幌
|style="background-color:#fff" |[[浅羽靖]]
!函館
|style="background-color:#bdb" |[[内山吉太]]
|-
![[青森県]]
!1区
|style="background-color:#bdb" |[[奈須川光宝]]
!2区
|style="background-color:#bdb" |[[榊喜洋芽]]
|}
"""

    def test_old_section_name(self) -> None:
        """「この選挙で当選」セクション名にも対応."""
        result = parse_wikitext(self.WIKITEXT_OLD_SECTION, 9)
        assert len(result) == 4
        assert result[0].name == "浅羽靖"
        assert result[0].party_name == "無所属"

    def test_plain_district_name(self) -> None:
        """Wikilinkなしの選挙区名（第1-9回形式）."""
        result = parse_wikitext(self.WIKITEXT_OLD_SECTION, 9)
        aomori = [c for c in result if c.prefecture == "青森県"]
        assert len(aomori) == 2
        assert aomori[0].district_name == "青森県1区"
        assert aomori[1].district_name == "青森県2区"

    def test_location_district(self) -> None:
        """地名ベースの選挙区名（札幌、函館等）."""
        result = parse_wikitext(self.WIKITEXT_OLD_SECTION, 9)
        hokkaido = [c for c in result if c.prefecture == "北海道"]
        assert len(hokkaido) == 2
        assert "札幌" in hokkaido[0].district_name
        assert "函館" in hokkaido[1].district_name

    WIKITEXT_SEMICOLON = """
{{colorbox|#9b9|自民党}} {{colorbox|#fff|無所属}}

=== 当選者 ===
{| class="wikitable"
![[東京都]]
!1区
|style="background-color:#9b9;"|[[鳩山一郎]]
|style="background-color:#fff;"|[[尾崎行雄]]
|}
"""

    def test_semicolon_style(self) -> None:
        """セミコロン付きスタイル属性のパース."""
        result = parse_wikitext(self.WIKITEXT_SEMICOLON, 15)
        assert len(result) == 2
        assert result[0].name == "鳩山一郎"
        assert result[0].party_name == "自民党"
        assert result[0].prefecture == "東京都"

    WIKITEXT_MULTIROW = """
{{colorbox|#9e9|自民}} {{colorbox|#0ff|社会}}

=== 当選者 ===
{| class="wikitable"
! rowspan="2" | [[北海道]]
! rowspan="2" |[[北海道第1区 (中選挙区)|1区]]
|style="background-color:#9e9" | [[候補A]]
|style="background-color:#0ff" | [[候補B]]
|style="background-color:#9e9" | [[候補C]]
|-
|style="background-color:#0ff" | [[候補D]]
| colspan="2" |
|-
! [[青森県]]
! [[青森県第1区 (中選挙区)|1区]]
|style="background-color:#9e9" | [[候補E]]
|}
"""

    def test_multirow_district(self) -> None:
        """rowspanで複数行にまたがる選挙区."""
        result = parse_wikitext(self.WIKITEXT_MULTIROW, 30)
        assert len(result) == 5
        hok1 = [c for c in result if c.district_name == "北海道1区"]
        assert len(hok1) == 4
        assert hok1[3].name == "候補D"

    def test_empty_wikitext_format_c(self) -> None:
        assert parse_wikitext("", 10) == []
        assert parse_wikitext("何かのテキスト", 30) == []


class TestParseWikitextIntegration:
    """統合テスト: 凡例なしでフォールバック使用."""

    WIKITEXT_NO_LEGEND = """
{{衆議院小選挙区当選者(第49回まで)
|北海道1区色=9E9|北海道1区=[[自民太郎]]
|北海道2区色=F9B|北海道2区=[[民主花子]]
}}
"""

    def test_fallback_party_mapping(self) -> None:
        result = parse_wikitext(self.WIKITEXT_NO_LEGEND, 42)
        assert len(result) == 2
        assert result[0].party_name == "自由民主党"
        assert result[1].party_name == "民主党"


class TestEdgeCases:
    """エッジケースのテスト."""

    def test_empty_wikitext(self) -> None:
        assert parse_wikitext("", 41) == []
        assert parse_wikitext("", 42) == []

    def test_no_matching_template(self) -> None:
        assert parse_wikitext("何かのテキスト", 41) == []
        assert parse_wikitext("何かのテキスト", 42) == []

    def test_display_name_in_wikilink(self) -> None:
        wikitext = """
{{衆議院小選挙区当選者(第49回まで)
|北海道1区色=9E9|北海道1区=[[田中太郎 (政治家)|田中太郎]]
}}
"""
        result = parse_wikitext(wikitext, 42)
        assert len(result) == 1
        assert result[0].name == "田中太郎"

    def test_ref_tag_removal(self) -> None:
        wikitext = """
{{衆議院小選挙区当選者(第49回まで)
|北海道1区色=9E9|北海道1区=[[田中太郎]]<ref>出典</ref>
}}
"""
        result = parse_wikitext(wikitext, 42)
        assert len(result) == 1
        assert result[0].name == "田中太郎"


class TestProportionalFormatA:
    """比例代表形式A（第41回）パースのテスト."""

    WIKITEXT = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#f9b|新進党}}
{{colorbox|#F6C|民主党}} {{colorbox|#F66|日本共産党}}

{{衆院比例当選者
|北海道定数=9
|北海道=
f9b:[[池端清一]]
9e9:[[鈴木宗男]]
F6C:[[鰐淵俊之]]
|東北定数=16
|東北=
9e9:[[穂積良行]]
f9b:[[日野市朗]]
F66:[[松本善明]]
|北海道増減=自民党 3
|東北増減=自民党 6
}}
"""

    def test_parse_basic(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 41)
        assert len(result) == 6

    def test_hokkaido_block(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 41)
        hokkaido = [c for c in result if c.district_name == "比例北海道ブロック"]
        assert len(hokkaido) == 3
        assert hokkaido[0].name == "池端清一"
        assert hokkaido[0].party_name == "新進党"
        assert hokkaido[0].rank == 1
        assert hokkaido[1].name == "鈴木宗男"
        assert hokkaido[1].party_name == "自由民主党"
        assert hokkaido[1].rank == 2

    def test_tohoku_block(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 41)
        tohoku = [c for c in result if c.district_name == "比例東北ブロック"]
        assert len(tohoku) == 3
        assert tohoku[2].name == "松本善明"
        assert tohoku[2].party_name == "日本共産党"

    def test_skip_increase_decrease(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 41)
        assert len(result) == 6

    def test_is_elected(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 41)
        for c in result:
            assert c.is_elected is True
            assert c.total_votes == 0


class TestProportionalFormatB:
    """比例代表形式B（第42回）パースのテスト."""

    WIKITEXT = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#f9b|民主党}}
{{colorbox|#fdf|公明党}} {{colorbox|#abd|自由党}}

{{衆議院当選者一覧(比例区)
|北海1色=f9b|北海1=[[中沢健次]]
|東北1色=9e9|東北1=[[御法川英文]]
|北関1色=9e9|北関1=[[中曽根康弘]]
|北海2色=9e9|北海2=[[鈴木宗男]]
|東北2色=f9b|東北2=[[日野市朗]]
|北関2色=f9b|北関2=[[金子善次郎]]
}}
"""

    def test_parse_basic(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 42)
        assert len(result) == 6

    def test_hokkaido_block(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 42)
        hokkaido = [c for c in result if c.district_name == "比例北海道ブロック"]
        assert len(hokkaido) == 2
        assert hokkaido[0].name == "中沢健次"
        assert hokkaido[0].party_name == "民主党"
        assert hokkaido[0].rank == 1
        assert hokkaido[1].name == "鈴木宗男"
        assert hokkaido[1].rank == 2

    def test_block_name_mapping(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 42)
        blocks = {c.district_name for c in result}
        assert "比例北海道ブロック" in blocks
        assert "比例東北ブロック" in blocks
        assert "比例北関東ブロック" in blocks


class TestProportionalWikitable:
    """比例代表wikitable形式（第43-44回）パースのテスト."""

    _HEADER = (
        "!width=2.1%| "
        "!!width=8.9%|[[比例北海道ブロック|北海道]]"
        "!!width=8.9%|[[比例東北ブロック|東北]]"
        "!!width=8.9%|[[比例北関東ブロック|北関東]]"
    )
    WIKITEXT = (
        "\n{{colorbox|#f9b|民主党}}"
        " {{colorbox|#9E9|自由民主党}}\n"
        "{{colorbox|#fdf|公明党}}"
        " {{colorbox|#F66|日本共産党}}\n\n"
        "=== 比例区当選者 ===\n"
        '{| class="wikitable"\n' + _HEADER + "\n|-\n!1\n"
        '|style="background-color:#f9b"|[[佐々木秀典]]\n'
        '|style="background-color:#9e9"|[[吉野正芳]]\n'
        '|style="background-color:#f9b"|[[武山百合子]]\n'
        "|-\n!2\n"
        '|style="background-color:#9e9"|[[金田英行]]\n'
        '|style="background-color:#f9b"|[[橋本清仁]]\n'
        '|style="background-color:#9e9"|[[佐田玄一郎]]\n'
        "|-\n!\n"
        "|民主党 3→4\n|民主党 5→5\n|民主党 6→8\n"
        "|}\n"
    )

    def test_parse_basic(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 43)
        assert len(result) == 6

    def test_hokkaido_block(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 43)
        hokkaido = [c for c in result if c.district_name == "比例北海道ブロック"]
        assert len(hokkaido) == 2
        assert hokkaido[0].name == "佐々木秀典"
        assert hokkaido[0].party_name == "民主党"
        assert hokkaido[0].rank == 1
        assert hokkaido[1].name == "金田英行"
        assert hokkaido[1].party_name == "自由民主党"
        assert hokkaido[1].rank == 2

    def test_works_for_44(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 44)
        assert len(result) == 6

    def test_skip_summary_rows(self) -> None:
        result = parse_proportional_wikitext(self.WIKITEXT, 43)
        for c in result:
            assert "→" not in c.name


class TestParseAllWikitext:
    """parse_all_wikitext統合テスト."""

    WIKITEXT = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#f9b|民主党}}

{{衆議院小選挙区当選者(第49回まで)
|北海道1区色=f9b|北海道1区=[[横路孝弘]]
}}

{{衆議院当選者一覧(比例区)
|北海1色=9e9|北海1=[[鈴木宗男]]
}}
"""

    def test_combines_smd_and_pr(self) -> None:
        result = parse_all_wikitext(self.WIKITEXT, 42)
        assert len(result) == 2
        names = {c.name for c in result}
        assert "横路孝弘" in names
        assert "鈴木宗男" in names

    WIKITEXT_OLD = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|社会党}}

=== 当選者 ===
{| class="wikitable"
! [[北海道]]
! [[北海道第1区 (中選挙区)|1区]]
|style="background-color:#9e9" | [[田中太郎]]
|}
"""

    def test_old_election_no_proportional(self) -> None:
        """第40回以前はparse_all_wikitextでも比例なし."""
        result = parse_all_wikitext(self.WIKITEXT_OLD, 30)
        assert len(result) == 1
        assert result[0].name == "田中太郎"
