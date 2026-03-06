"""SpeakerPoliticianMatchingService のテスト."""

from src.domain.services.speaker_politician_matching_service import (
    SpeakerPoliticianMatchingService,
)
from src.domain.value_objects.speaker_politician_match_result import (
    MatchMethod,
    PoliticianCandidate,
)


class TestSpeakerPoliticianMatchingService:
    """SpeakerPoliticianMatchingService.match() のテスト.

    match()は完全一致（confidence=1.0）のみを判定し、
    中間ルール（ふりがな、漢字姓、姓のみ）はLLM判定に委譲された。
    """

    def setup_method(self) -> None:
        self.service = SpeakerPoliticianMatchingService()

    # --- 完全一致テスト ---

    def test_exact_name_match(self) -> None:
        """完全一致マッチングで confidence 1.0 を返す."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="きしだふみお"
            ),
            PoliticianCandidate(
                politician_id=2, name="石破茂", furigana="いしばしげる"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田文雄",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.politician_name == "岸田文雄"
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_NAME

    def test_exact_name_match_with_honorific(self) -> None:
        """敬称付き名前から敬称を除去して完全一致マッチングする."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="きしだふみお"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田文雄君",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_NAME

    def test_exact_name_match_various_honorifics(self) -> None:
        """各種敬称（君、氏、さん、議員、先生）が除去されてマッチする."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="田中太郎"),
        ]
        for honorific in ["君", "氏", "さん", "議員", "先生", "くん", "殿", "様"]:
            result = self.service.match(
                speaker_id=10,
                speaker_name=f"田中太郎{honorific}",
                speaker_name_yomi=None,
                candidates=candidates,
            )
            assert result.politician_id == 1, f"敬称「{honorific}」の除去に失敗"
            assert result.confidence == 1.0

    def test_exact_name_match_with_spaces(self) -> None:
        """スペースを含む名前が正規化されてマッチする."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="岸田 文雄"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田文雄",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 1.0

    # --- match()が完全一致のみ返すことの確認テスト ---

    def test_match_returns_none_for_yomi_only_match(self) -> None:
        """ふりがなのみ一致する場合、match()はNONEを返す（LLMに委譲）."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="河野太郎", furigana="こうのたろう"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="こうの太郎",
            speaker_name_yomi="こうのたろう",
            candidates=candidates,
        )
        # 完全一致しないのでマッチなし
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    def test_match_returns_none_for_surname_only(self) -> None:
        """姓のみ一致する場合、match()はNONEを返す（LLMに委譲）."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="岸田文雄"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    def test_match_returns_none_for_kanji_surname_only(self) -> None:
        """漢字姓のみ一致する場合、match()はNONEを返す（LLMに委譲）."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="武村　のぶひで"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="武村展英",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    # --- kanji_name完全一致フォールバックテスト ---

    def test_kanji_name_fallback_match(self) -> None:
        """candidate.nameが不一致でもkanji_nameで完全一致すればマッチする."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="武村のぶひで",
                kanji_name="武村正義",
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="武村正義",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.politician_name == "武村のぶひで"
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_KANJI_NAME

    def test_kanji_name_not_used_when_name_matches(self) -> None:
        """name完全一致が優先され、kanji_nameフォールバックは使われない."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="武村正義",
                kanji_name="武村正義",
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="武村正義",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_NAME

    def test_kanji_name_none_skipped(self) -> None:
        """kanji_nameがNoneの候補はスキップされマッチなしになる."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="武村のぶひで",
                kanji_name=None,
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="武村正義",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    # --- マッチなしテスト ---

    def test_no_candidates(self) -> None:
        """候補リストが空の場合マッチなし."""
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田文雄",
            speaker_name_yomi=None,
            candidates=[],
        )
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    def test_empty_speaker_name(self) -> None:
        """発言者名が空文字の場合マッチなし."""
        candidates = [PoliticianCandidate(politician_id=1, name="岸田文雄")]
        result = self.service.match(
            speaker_id=10,
            speaker_name="",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0

    def test_no_match_at_all(self) -> None:
        """どの方法でもマッチしない場合."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="きしだふみお"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="全く異なる名前",
            speaker_name_yomi="まったくことなるなまえ",
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    # --- 正規化テスト ---

    def test_normalize_name_removes_honorific(self) -> None:
        """normalize_name が敬称を正しく除去する."""
        assert self.service.normalize_name("岸田文雄君") == "岸田文雄"
        assert self.service.normalize_name("田中太郎議員") == "田中太郎"
        assert self.service.normalize_name("山田花子先生") == "山田花子"
        assert self.service.normalize_name("鈴木一郎氏") == "鈴木一郎"
        assert self.service.normalize_name("佐藤次郎さん") == "佐藤次郎"

    def test_normalize_name_removes_spaces(self) -> None:
        """normalize_name がスペースを除去する."""
        assert self.service.normalize_name("岸田 文雄") == "岸田文雄"
        assert self.service.normalize_name("岸田　文雄") == "岸田文雄"  # 全角スペース

    def test_normalize_name_title_honorifics(self) -> None:
        """役職系の敬称（議長、委員長等）が除去される."""
        assert self.service.normalize_name("西村義直議長") == "西村義直"
        assert self.service.normalize_name("田中太郎委員長") == "田中太郎"
        assert self.service.normalize_name("山田花子副委員長") == "山田花子"
        assert self.service.normalize_name("佐藤次郎副議長") == "佐藤次郎"

    # --- 旧字体→新字体マッチテスト ---

    def test_kyujitai_exact_match(self) -> None:
        """旧字体Speakerと新字体候補が完全一致する."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="桜田義孝"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="櫻田義孝",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_NAME

    def test_kyujitai_san_match(self) -> None:
        """參→参 の変換による完全一致."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="野坂参三"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="野坂參三",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_NAME

    # --- 同姓曖昧判定テスト ---

    def test_has_surname_ambiguity_multiple_same_surname(self) -> None:
        """同姓候補が複数いる場合にTrueを返す."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="田中太郎"),
            PoliticianCandidate(politician_id=2, name="田中次郎"),
        ]
        assert self.service.has_surname_ambiguity("田中", candidates) is True

    def test_has_surname_ambiguity_single_candidate(self) -> None:
        """同姓候補が1人のみの場合にFalseを返す."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="田中太郎"),
            PoliticianCandidate(politician_id=2, name="佐藤花子"),
        ]
        assert self.service.has_surname_ambiguity("田中", candidates) is False

    def test_has_surname_ambiguity_fullname_not_ambiguous(self) -> None:
        """フルネーム（姓の長さ超過）の場合はFalseを返す."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="田中太郎"),
            PoliticianCandidate(politician_id=2, name="田中次郎"),
        ]
        # フルネームは姓のみ判定の対象外
        assert self.service.has_surname_ambiguity("田中太郎", candidates) is False

    def test_has_surname_ambiguity_no_candidates(self) -> None:
        """候補なしの場合にFalseを返す."""
        assert self.service.has_surname_ambiguity("田中", []) is False

    def test_has_surname_ambiguity_no_match(self) -> None:
        """どの候補の姓にも一致しない場合にFalseを返す."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="佐藤太郎"),
            PoliticianCandidate(politician_id=2, name="鈴木花子"),
        ]
        assert self.service.has_surname_ambiguity("田中", candidates) is False

    def test_has_surname_ambiguity_with_honorific(self) -> None:
        """敬称付き名前でも正規化されて判定される."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="田中太郎"),
            PoliticianCandidate(politician_id=2, name="田中次郎"),
        ]
        assert self.service.has_surname_ambiguity("田中君", candidates) is True


class TestFilterCandidatesForLlm:
    """filter_candidates_for_llm() のテスト.

    LLM判定前の候補フィルタリング。3つのフィルタ基準（OR条件）:
    1. 名前パート部分一致: Politician名をスペース分割し各パートがSpeaker名に含まれるか
    2. 漢字姓一致: extract_kanji_surname()で姓抽出して双方向チェック
    3. ふりがなプレフィックス一致: name_yomiとfuriganaの先頭>=3文字一致
    """

    def setup_method(self) -> None:
        self.service = SpeakerPoliticianMatchingService()

    # --- 基準1: 名前パート部分一致（スペース区切り） ---

    def test_name_part_match_with_space_separated_candidate(self) -> None:
        """Politician名をスペース分割し、パート(>=2文字)がSpeaker名に含まれればマッチ."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="たちばな　慶一郎",
                furigana="たちばなけいいちろう",
            ),
            PoliticianCandidate(
                politician_id=2,
                name="佐藤　花子",
                furigana="さとうはなこ",
            ),
        ]
        # "慶一郎"(3文字>=2文字)が"橘慶一郎"に含まれるため候補1がマッチ
        result = self.service.filter_candidates_for_llm(
            speaker_name="橘慶一郎",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert len(result) == 1
        assert result[0].politician_id == 1

    def test_name_part_short_part_skipped(self) -> None:
        """1文字のパートはフィルタ基準から除外される."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="木 太郎",  # "木"は1文字なのでスキップ
            ),
        ]
        # "太郎"(2文字>=2文字)が"木太郎"に含まれるのでマッチ
        result = self.service.filter_candidates_for_llm(
            speaker_name="木太郎",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert len(result) == 1
        assert result[0].politician_id == 1

    # --- 基準2: 漢字姓抽出による一致判定 ---

    def test_kanji_surname_extraction_candidate_to_speaker(self) -> None:
        """候補名の漢字姓がSpeaker名に含まれればマッチ（候補→Speaker方向）."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="上野みちこ",  # 漢字姓 "上野" を抽出
            ),
        ]
        # "上野"(2文字>=2文字)が"上野宏史"に含まれるのでマッチ
        result = self.service.filter_candidates_for_llm(
            speaker_name="上野宏史",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert len(result) == 1
        assert result[0].politician_id == 1

    def test_kanji_surname_extraction_speaker_to_candidate(self) -> None:
        """Speaker名の漢字姓が候補名に含まれればマッチ（Speaker→候補方向）."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="武村展英",
            ),
        ]
        # Speaker "武村のぶひで" → 漢字姓 "武村" → "武村展英" に含まれる
        result = self.service.filter_candidates_for_llm(
            speaker_name="武村のぶひで",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert len(result) == 1
        assert result[0].politician_id == 1

    def test_kanji_surname_single_char_not_matched(self) -> None:
        """1文字の漢字姓はフィルタ基準から除外される."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="林よしひろ",  # 漢字姓 "林" は1文字
            ),
        ]
        # "林"は1文字なので漢字姓一致の対象外
        result = self.service.filter_candidates_for_llm(
            speaker_name="林芳正",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert len(result) == 0

    # --- 基準3: ふりがなプレフィックス一致 ---

    def test_furigana_prefix_match(self) -> None:
        """Speaker name_yomiとPolitician furiganaの先頭>=3文字が一致すればマッチ."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="橘慶一郎",
                furigana="たちばなけいいちろう",
            ),
            PoliticianCandidate(
                politician_id=2,
                name="佐藤花子",
                furigana="さとうはなこ",
            ),
        ]
        result = self.service.filter_candidates_for_llm(
            speaker_name="たちばな慶一郎",
            speaker_name_yomi="たちばなけいいちろう",
            candidates=candidates,
        )
        # ふりがなプレフィックス一致で候補1がマッチ
        assert any(c.politician_id == 1 for c in result)

    def test_furigana_prefix_match_katakana_normalized(self) -> None:
        """カタカナのname_yomiもひらがなに正規化してプレフィックス一致する."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="岸田文雄",
                furigana="きしだふみお",
            ),
        ]
        # カタカナ → ひらがな正規化で "きしだふみお" と一致
        result = self.service.filter_candidates_for_llm(
            speaker_name="別名",
            speaker_name_yomi="キシダフミオ",
            candidates=candidates,
        )
        assert len(result) == 1
        assert result[0].politician_id == 1

    def test_furigana_prefix_too_short_no_match(self) -> None:
        """ふりがなが3文字未満の場合はマッチしない."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="木太郎",
                furigana="き",  # 1文字のふりがな
            ),
        ]
        result = self.service.filter_candidates_for_llm(
            speaker_name="別名",
            speaker_name_yomi="き",
            candidates=candidates,
        )
        # 先頭一致の最小長(3)に満たないのでマッチしない
        assert len(result) == 0

    def test_furigana_no_match_when_yomi_none(self) -> None:
        """Speaker name_yomiがNoneの場合、ふりがなプレフィックス基準は適用されない."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="岸田文雄",
                furigana="きしだふみお",
            ),
        ]
        # name_yomiがNone、かつ名前パート・漢字姓いずれもマッチしない
        result = self.service.filter_candidates_for_llm(
            speaker_name="全く異なる名前",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert len(result) == 0

    # --- 候補0件テスト ---

    def test_no_candidates_returns_empty(self) -> None:
        """候補リストが空の場合、空リストを返す."""
        result = self.service.filter_candidates_for_llm(
            speaker_name="岸田文雄",
            speaker_name_yomi=None,
            candidates=[],
        )
        assert result == []

    def test_empty_speaker_name_returns_empty(self) -> None:
        """発言者名が空文字の場合、空リストを返す."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="岸田文雄"),
        ]
        result = self.service.filter_candidates_for_llm(
            speaker_name="",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result == []

    def test_no_relevant_candidate(self) -> None:
        """どの基準にもマッチしない名前の場合、空リストを返す."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="岸田文雄",
                furigana="きしだふみお",
            ),
            PoliticianCandidate(
                politician_id=2,
                name="石破茂",
                furigana="いしばしげる",
            ),
        ]
        result = self.service.filter_candidates_for_llm(
            speaker_name="全く異なる名前",
            speaker_name_yomi="まったくことなるなまえ",
            candidates=candidates,
        )
        assert result == []

    # --- 複数候補マッチテスト ---

    def test_multiple_candidates_matched(self) -> None:
        """複数の候補がフィルタ基準に該当する場合、全てを返す."""
        candidates = [
            PoliticianCandidate(
                politician_id=1,
                name="田中一郎",
                furigana="たなかいちろう",
            ),
            PoliticianCandidate(
                politician_id=2,
                name="田中次郎",
                furigana="たなかじろう",
            ),
            PoliticianCandidate(
                politician_id=3,
                name="佐藤花子",
                furigana="さとうはなこ",
            ),
        ]
        # "田中" はSpeaker "田中ひろし" の漢字姓として抽出され、
        # "田中一郎"と"田中次郎"の両方に含まれる
        result = self.service.filter_candidates_for_llm(
            speaker_name="田中ひろし",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        matched_ids = {c.politician_id for c in result}
        assert matched_ids == {1, 2}
        # 佐藤花子はマッチしない
        assert 3 not in matched_ids
