"""NameNormalizer のテスト."""

from src.domain.services.name_normalizer import NameNormalizer


class TestNormalize:
    """normalize メソッドのテスト."""

    # --- 旧字体→新字体変換 ---

    def test_kyujitai_sakura(self) -> None:
        """櫻→桜 の変換."""
        assert NameNormalizer.normalize("櫻田義孝") == "桜田義孝"

    def test_kyujitai_sai(self) -> None:
        """齋→斎 の変換."""
        assert NameNormalizer.normalize("齋藤花子") == "斎藤花子"

    def test_kyujitai_san(self) -> None:
        """參→参 の変換（Issueの例）."""
        assert NameNormalizer.normalize("野坂參三") == "野坂参三"

    def test_kyujitai_man(self) -> None:
        """滿→満 の変換（Issueの例）."""
        assert NameNormalizer.normalize("川野芳滿") == "川野芳満"

    def test_kyujitai_ei(self) -> None:
        """榮→栄 の変換（Issueの例）."""
        assert NameNormalizer.normalize("西村榮一") == "西村栄一"

    def test_kyujitai_taka(self) -> None:
        """髙→高 の変換."""
        assert NameNormalizer.normalize("髙橋一郎") == "高橋一郎"

    def test_multiple_kyujitai(self) -> None:
        """複数の旧字体を含む名前."""
        assert NameNormalizer.normalize("國澤太郎") == "国沢太郎"

    # --- Issue #1305: 旧字体テーブル拡充 ---

    def test_kyujitai_ya(self) -> None:
        """彌→弥 の変換."""
        assert NameNormalizer.normalize("河井彌八") == "河井弥八"

    def test_kyujitai_kaku(self) -> None:
        """覺→覚 の変換."""
        assert NameNormalizer.normalize("足鹿覺") == "足鹿覚"

    def test_kyujitai_gan(self) -> None:
        """巖→巌 の変換."""
        assert NameNormalizer.normalize("寺前巖") == "寺前巌"

    def test_kyujitai_ho(self) -> None:
        """穗→穂 の変換."""
        assert NameNormalizer.normalize("穗積七郎") == "穂積七郎"

    def test_kyujitai_en(self) -> None:
        """圓→円 の変換."""
        assert NameNormalizer.normalize("草葉隆圓") == "草葉隆円"

    def test_kyujitai_oku(self) -> None:
        """奧→奥 の変換."""
        assert NameNormalizer.normalize("奧野誠亮") == "奥野誠亮"

    def test_kyujitai_ina(self) -> None:
        """稻→稲 の変換."""
        assert NameNormalizer.normalize("稻葉修") == "稲葉修"

    def test_kyujitai_asa_with_multiple(self) -> None:
        """淺→浅 + 稻→稲 の複数旧字体変換."""
        assert NameNormalizer.normalize("淺沼稻次郎") == "浅沼稲次郎"

    def test_kyujitai_taki(self) -> None:
        """瀧→滝 の変換."""
        assert NameNormalizer.normalize("瀧井太郎") == "滝井太郎"

    def test_kyujitai_shin(self) -> None:
        """眞→真 の変換."""
        assert NameNormalizer.normalize("眞鍋勝") == "真鍋勝"

    # --- Issue #1322: 旧字体テーブル拡充（衞・莊・權・澁・禪・禰） ---

    def test_kyujitai_1322_ei(self) -> None:
        """衞→衛 の変換."""
        assert NameNormalizer.normalize("木島喜兵衞") == "木島喜兵衛"

    def test_kyujitai_1322_sou(self) -> None:
        """莊→荘 の変換."""
        assert NameNormalizer.normalize("臼井莊一") == "臼井荘一"

    def test_kyujitai_1322_ken(self) -> None:
        """權→権 の変換."""
        assert NameNormalizer.normalize("石山權作") == "石山権作"

    def test_kyujitai_1322_shibu(self) -> None:
        """澁→渋 の変換（藏→蔵も同時変換）."""
        assert NameNormalizer.normalize("澁谷直藏") == "渋谷直蔵"

    def test_kyujitai_1322_zen(self) -> None:
        """禪→禅 の変換（廣→広も同時変換）."""
        assert NameNormalizer.normalize("廣川弘禪") == "広川弘禅"

    def test_kyujitai_1322_ne(self) -> None:
        """禰→祢 の変換（曾→曽も同時変換）."""
        assert NameNormalizer.normalize("曾禰益") == "曽祢益"

    def test_kyujitai_1322_ei_single(self) -> None:
        """衞→衛 の単独変換（他の旧字体を含まないケース）."""
        assert NameNormalizer.normalize("衞藤太郎") == "衛藤太郎"

    def test_kyujitai_1322_ne_single(self) -> None:
        """禰→祢 の単独変換."""
        assert NameNormalizer.normalize("禰宜田太郎") == "祢宜田太郎"

    # --- NFKC正規化 ---

    def test_nfkc_fullwidth_space(self) -> None:
        """全角スペース除去."""
        assert NameNormalizer.normalize("岸田　文雄") == "岸田文雄"

    def test_nfkc_halfwidth_space(self) -> None:
        """半角スペース除去."""
        assert NameNormalizer.normalize("岸田 文雄") == "岸田文雄"

    # --- 敬称除去 ---

    def test_honorific_kun(self) -> None:
        """「君」除去."""
        assert NameNormalizer.normalize("岸田文雄君") == "岸田文雄"

    def test_honorific_giin(self) -> None:
        """「議員」除去."""
        assert NameNormalizer.normalize("田中太郎議員") == "田中太郎"

    def test_honorific_gichou(self) -> None:
        """「議長」除去."""
        assert NameNormalizer.normalize("西村義直議長") == "西村義直"

    def test_honorific_fuku_gichou(self) -> None:
        """「副議長」除去（「議長」より先にマッチ）."""
        assert NameNormalizer.normalize("佐藤次郎副議長") == "佐藤次郎"

    def test_honorific_iinchou(self) -> None:
        """「委員長」除去."""
        assert NameNormalizer.normalize("田中太郎委員長") == "田中太郎"

    # --- 複合テスト ---

    def test_combined_kyujitai_space_honorific(self) -> None:
        """旧字体 + スペース + 敬称の複合正規化."""
        assert NameNormalizer.normalize("櫻井　太郎議員") == "桜井太郎"

    def test_no_change_needed(self) -> None:
        """変更不要な名前."""
        assert NameNormalizer.normalize("岸田文雄") == "岸田文雄"

    def test_empty_string(self) -> None:
        """空文字."""
        assert NameNormalizer.normalize("") == ""

    def test_whitespace_only(self) -> None:
        """空白のみ."""
        assert NameNormalizer.normalize("  　 ") == ""


class TestExtractKanjiSurname:
    """extract_kanji_surname メソッドのテスト."""

    def test_hiragana_mixed(self) -> None:
        """ひらがな混じり名から漢字姓を抽出."""
        assert NameNormalizer.extract_kanji_surname("武村のぶひで") == "武村"

    def test_all_kanji(self) -> None:
        """全漢字名はそのまま返る."""
        assert NameNormalizer.extract_kanji_surname("岸田文雄") == "岸田文雄"

    def test_all_hiragana(self) -> None:
        """全ひらがなは空文字."""
        assert NameNormalizer.extract_kanji_surname("たけむら") == ""

    def test_single_kanji_surname(self) -> None:
        """1文字姓."""
        assert NameNormalizer.extract_kanji_surname("林よしひろ") == "林"

    def test_three_kanji_surname(self) -> None:
        """3文字姓."""
        assert NameNormalizer.extract_kanji_surname("長谷川たかし") == "長谷川"

    def test_with_spaces(self) -> None:
        """スペースを含む名前."""
        assert NameNormalizer.extract_kanji_surname("武村　のぶひで") == "武村"

    def test_empty_string(self) -> None:
        """空文字."""
        assert NameNormalizer.extract_kanji_surname("") == ""

    def test_odoriji_nonomura(self) -> None:
        """踊り字「々」を含む姓（佐々木）."""
        assert NameNormalizer.extract_kanji_surname("佐々木はじめ") == "佐々木"

    def test_odoriji_sasaki_with_space(self) -> None:
        """踊り字「々」+スペース."""
        assert NameNormalizer.extract_kanji_surname("佐々木　あけみ") == "佐々木"

    def test_katakana_in_surname_mittsubayashi(self) -> None:
        """カタカナ「ッ」を含む姓（三ッ林）."""
        assert NameNormalizer.extract_kanji_surname("三ッ林ひろみ") == "三ッ林"

    def test_katakana_in_surname_mitsuya(self) -> None:
        """カタカナ「ツ」を含む姓（三ツ矢）."""
        assert NameNormalizer.extract_kanji_surname("三ツ矢のりお") == "三ツ矢"

    def test_katakana_ke_in_surname(self) -> None:
        """カタカナ「ヶ」を含む姓（竹ヶ原）."""
        assert NameNormalizer.extract_kanji_surname("竹ヶ原ゆみこ") == "竹ヶ原"

    def test_starts_with_katakana(self) -> None:
        """先頭がカタカナの場合は空文字（漢字でないため）."""
        assert NameNormalizer.extract_kanji_surname("ッ林ひろみ") == ""


class TestHasMixedHiragana:
    """has_mixed_hiragana メソッドのテスト."""

    def test_mixed(self) -> None:
        """漢字+ひらがな混在."""
        assert NameNormalizer.has_mixed_hiragana("武村のぶひで") is True

    def test_all_kanji(self) -> None:
        """全漢字."""
        assert NameNormalizer.has_mixed_hiragana("岸田文雄") is False

    def test_all_hiragana(self) -> None:
        """全ひらがな."""
        assert NameNormalizer.has_mixed_hiragana("たけむら") is False

    def test_kanji_katakana(self) -> None:
        """漢字+カタカナ（ひらがななし）."""
        assert NameNormalizer.has_mixed_hiragana("武村ノブヒデ") is False


class TestNormalizeKana:
    """normalize_kana メソッドのテスト."""

    def test_katakana_to_hiragana(self) -> None:
        """カタカナ→ひらがな変換."""
        assert NameNormalizer.normalize_kana("キシダフミオ") == "きしだふみお"

    def test_hiragana_unchanged(self) -> None:
        """ひらがなはそのまま."""
        assert NameNormalizer.normalize_kana("きしだふみお") == "きしだふみお"

    def test_space_removal(self) -> None:
        """スペース除去."""
        assert NameNormalizer.normalize_kana("きしだ ふみお") == "きしだふみお"

    def test_mixed_kana(self) -> None:
        """カタカナ+ひらがな混在."""
        assert NameNormalizer.normalize_kana("キシダふみお") == "きしだふみお"

    def test_halfwidth_katakana(self) -> None:
        """半角カタカナがNFKC正規化で全角→ひらがなに変換される."""
        assert NameNormalizer.normalize_kana("ﾔﾏﾀﾞﾀﾛｳ") == "やまだたろう"
