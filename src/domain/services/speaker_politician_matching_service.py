"""発言者→政治家ルールベースマッチングサービス.

ConferenceMemberで絞り込んだ候補リストに対して、
名前・ふりがなベースのルールマッチングを行う。
DB非依存の純粋なドメインロジック。
"""

from src.domain.services.name_normalizer import NameNormalizer
from src.domain.value_objects.speaker_politician_match_result import (
    MatchMethod,
    PoliticianCandidate,
    SpeakerPoliticianMatchResult,
)


# 姓の最小・最大文字数（日本語名の姓は1-4文字が一般的）
_MIN_SURNAME_LEN = 1
_MAX_SURNAME_LEN = 4


class SpeakerPoliticianMatchingService:
    """発言者→政治家のルールベースマッチングサービス."""

    def match(
        self,
        speaker_id: int,
        speaker_name: str,
        speaker_name_yomi: str | None,
        candidates: list[PoliticianCandidate],
    ) -> SpeakerPoliticianMatchResult:
        """発言者名を候補政治家リストとマッチングする.

        マッチング優先順位:
        1. 完全一致 → confidence: 1.0
        2. ふりがな一致 → confidence: 0.9
        3. 漢字姓マッチ（ひらがな混じり候補名対応）→ confidence: 0.85
        4. 姓のみ一致（同姓候補1人のみ）→ confidence: 0.8
        5. マッチなし → confidence: 0.0

        Args:
            speaker_id: 発言者ID
            speaker_name: 発言者名（敬称付きの可能性あり）
            speaker_name_yomi: 発言者のふりがな（APIから取得、Noneの場合あり）
            candidates: マッチング候補の政治家リスト

        Returns:
            マッチング結果
        """
        normalized_name = self.normalize_name(speaker_name)

        if not normalized_name or not candidates:
            return self._no_match(speaker_id, speaker_name)

        # 1. 完全一致チェック
        for candidate in candidates:
            normalized_candidate = self.normalize_name(candidate.name)
            if normalized_name == normalized_candidate:
                return SpeakerPoliticianMatchResult(
                    speaker_id=speaker_id,
                    speaker_name=speaker_name,
                    politician_id=candidate.politician_id,
                    politician_name=candidate.name,
                    confidence=1.0,
                    match_method=MatchMethod.EXACT_NAME,
                )

        # 2. ふりがなチェック
        if speaker_name_yomi:
            normalized_yomi = self._normalize_kana(speaker_name_yomi)
            if normalized_yomi:
                for candidate in candidates:
                    if candidate.furigana:
                        normalized_furigana = self._normalize_kana(candidate.furigana)
                        if normalized_yomi == normalized_furigana:
                            return SpeakerPoliticianMatchResult(
                                speaker_id=speaker_id,
                                speaker_name=speaker_name,
                                politician_id=candidate.politician_id,
                                politician_name=candidate.name,
                                confidence=0.9,
                                match_method=MatchMethod.YOMI,
                            )

        # 3. 漢字姓マッチ（ひらがな混じり候補名対応）
        kanji_surname_match = self._match_by_kanji_surname(normalized_name, candidates)
        if kanji_surname_match:
            return SpeakerPoliticianMatchResult(
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                politician_id=kanji_surname_match.politician_id,
                politician_name=kanji_surname_match.name,
                confidence=0.85,
                match_method=MatchMethod.KANJI_SURNAME,
            )

        # 4. 姓のみ一致チェック（同姓候補が1人のみの場合）
        surname_match = self._match_by_surname(normalized_name, candidates)
        if surname_match:
            return SpeakerPoliticianMatchResult(
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                politician_id=surname_match.politician_id,
                politician_name=surname_match.name,
                confidence=0.8,
                match_method=MatchMethod.SURNAME_ONLY,
            )

        return self._no_match(speaker_id, speaker_name)

    def normalize_name(self, name: str) -> str:
        """名前を正規化する（旧字体→新字体変換、NFKC正規化、敬称除去、スペース除去）."""
        return NameNormalizer.normalize(name)

    def _normalize_kana(self, kana: str) -> str:
        """ふりがなを正規化する（カタカナ→ひらがな変換、スペース除去）."""
        return NameNormalizer.normalize_kana(kana)

    def _match_by_kanji_surname(
        self, speaker_name: str, candidates: list[PoliticianCandidate]
    ) -> PoliticianCandidate | None:
        """ひらがな混じり候補名の漢字姓部分でマッチングする.

        候補名が漢字+ひらがな混在（例: "武村のぶひで"）の場合、
        先頭の漢字部分（姓）を抽出してSpeaker名と比較する。

        Args:
            speaker_name: 正規化済みの発言者名
            candidates: 候補リスト

        Returns:
            マッチした候補（同姓1人の場合のみ）、該当なしはNone
        """
        matched_candidates: list[PoliticianCandidate] = []

        for candidate in candidates:
            # ひらがな混じりの候補名のみ対象
            if not NameNormalizer.has_mixed_hiragana(candidate.name):
                continue

            kanji_surname = NameNormalizer.extract_kanji_surname(candidate.name)
            if not kanji_surname:
                continue

            # 姓の長さチェック
            if not (_MIN_SURNAME_LEN <= len(kanji_surname) <= _MAX_SURNAME_LEN):
                continue

            # Speaker名がこの漢字姓で始まり、かつSpeaker名の方が長い（フルネーム）
            if speaker_name.startswith(kanji_surname) and len(speaker_name) > len(
                kanji_surname
            ):
                matched_candidates.append(candidate)

        # 同姓候補が1人のみの場合にマッチ
        if len(matched_candidates) == 1:
            return matched_candidates[0]

        return None

    def _match_by_surname(
        self, speaker_name: str, candidates: list[PoliticianCandidate]
    ) -> PoliticianCandidate | None:
        """姓のみでマッチングする.

        発言者名が候補の姓と一致し、かつその姓を持つ候補が1人のみの場合にマッチ。

        Args:
            speaker_name: 正規化済みの発言者名
            candidates: 候補リスト

        Returns:
            マッチした候補（同姓1人の場合のみ）、該当なしはNone
        """
        matched_candidates: list[PoliticianCandidate] = []

        for candidate in candidates:
            normalized_candidate = self.normalize_name(candidate.name)
            if not normalized_candidate:
                continue

            # 発言者名が候補のフルネームの先頭と一致（姓のみの発言者）
            if (
                _MIN_SURNAME_LEN <= len(speaker_name) <= _MAX_SURNAME_LEN
                and normalized_candidate.startswith(speaker_name)
                and len(speaker_name) < len(normalized_candidate)
            ):
                matched_candidates.append(candidate)

        # 同姓候補が1人のみの場合にマッチ
        if len(matched_candidates) == 1:
            return matched_candidates[0]

        return None

    @staticmethod
    def _no_match(speaker_id: int, speaker_name: str) -> SpeakerPoliticianMatchResult:
        """マッチなし結果を返す."""
        return SpeakerPoliticianMatchResult(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            politician_id=None,
            politician_name=None,
            confidence=0.0,
            match_method=MatchMethod.NONE,
        )
