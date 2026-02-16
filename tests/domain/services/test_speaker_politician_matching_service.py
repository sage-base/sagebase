"""SpeakerPoliticianMatchingService のテスト."""

from src.domain.services.speaker_politician_matching_service import (
    SpeakerPoliticianMatchingService,
)
from src.domain.value_objects.speaker_politician_match_result import (
    MatchMethod,
    PoliticianCandidate,
)


class TestSpeakerPoliticianMatchingService:
    """SpeakerPoliticianMatchingService のテスト."""

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

    # --- ふりがなマッチテスト ---

    def test_yomi_match(self) -> None:
        """ふりがな一致で confidence 0.9 を返す."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="河野太郎", furigana="こうのたろう"
            ),
            PoliticianCandidate(
                politician_id=2, name="菅義偉", furigana="すがよしひで"
            ),
        ]
        # 名前は不一致だがふりがなで一致
        result = self.service.match(
            speaker_id=10,
            speaker_name="こうの太郎",
            speaker_name_yomi="こうのたろう",
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 0.9
        assert result.match_method == MatchMethod.YOMI

    def test_yomi_match_katakana_to_hiragana(self) -> None:
        """カタカナのふりがなもひらがなに正規化してマッチする."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="キシダフミオ"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="別名",
            speaker_name_yomi="きしだふみお",
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 0.9
        assert result.match_method == MatchMethod.YOMI

    def test_yomi_match_speaker_katakana(self) -> None:
        """Speaker側がカタカナでもマッチする."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="きしだふみお"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="別名",
            speaker_name_yomi="キシダフミオ",
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 0.9

    def test_yomi_not_matched_when_speaker_yomi_none(self) -> None:
        """Speaker.name_yomi が None の場合、ふりがなマッチはスキップされる."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="特殊名前", furigana="とくしゅなまえ"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="別名",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        # 完全一致もふりがなもマッチしない
        assert result.politician_id is None
        assert result.confidence == 0.0

    def test_yomi_not_matched_when_candidate_furigana_none(self) -> None:
        """候補の furigana が None の場合、その候補はふりがなマッチ対象外."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="特殊名前", furigana=None),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="別名",
            speaker_name_yomi="とくしゅなまえ",
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0

    # --- 姓のみ一致テスト ---

    def test_surname_only_match(self) -> None:
        """姓のみ一致（同姓1人のみ）で confidence 0.8 を返す."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="岸田文雄"),
            PoliticianCandidate(politician_id=2, name="石破茂"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 0.8
        assert result.match_method == MatchMethod.SURNAME_ONLY

    def test_surname_only_match_multiple_candidates_no_match(self) -> None:
        """同姓候補が複数いる場合はマッチしない."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="田中太郎"),
            PoliticianCandidate(politician_id=2, name="田中花子"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="田中",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id is None
        assert result.confidence == 0.0
        assert result.match_method == MatchMethod.NONE

    def test_surname_3_chars(self) -> None:
        """3文字の姓でもマッチする."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="長谷川太郎"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="長谷川",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        assert result.politician_id == 1
        assert result.confidence == 0.8

    def test_surname_too_long_no_match(self) -> None:
        """5文字以上の名前は姓のみマッチ対象外."""
        candidates = [
            PoliticianCandidate(politician_id=1, name="長谷川太郎次郎"),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="長谷川太郎",
            speaker_name_yomi=None,
            candidates=candidates,
        )
        # 5文字は姓の最大長(4)を超えるため姓のみマッチ対象外
        assert result.politician_id is None

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

    # --- 優先順位テスト ---

    def test_exact_match_takes_priority_over_yomi(self) -> None:
        """完全一致がふりがなよりも優先される."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="きしだふみお"
            ),
        ]
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田文雄",
            speaker_name_yomi="きしだふみお",
            candidates=candidates,
        )
        assert result.confidence == 1.0
        assert result.match_method == MatchMethod.EXACT_NAME

    def test_yomi_takes_priority_over_surname(self) -> None:
        """ふりがなが姓のみより優先される."""
        candidates = [
            PoliticianCandidate(
                politician_id=1, name="岸田文雄", furigana="きしだふみお"
            ),
            PoliticianCandidate(
                politician_id=2, name="石破茂", furigana="いしばしげる"
            ),
        ]
        # 名前は「岸田」（姓のみ一致可能）だが、ふりがなは石破と一致
        result = self.service.match(
            speaker_id=10,
            speaker_name="岸田",
            speaker_name_yomi="いしばしげる",
            candidates=candidates,
        )
        # ふりがなの方が優先される
        assert result.politician_id == 2
        assert result.confidence == 0.9
        assert result.match_method == MatchMethod.YOMI

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
