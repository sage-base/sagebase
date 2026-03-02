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
        """発言者名を候補政治家リストとマッチングする（完全一致のみ）.

        正規化後の完全一致判定のみを行う。
        中間ルール（ふりがな、漢字姓、姓のみ）は廃止され、
        完全一致しないケースはLLM判定（BAML）に委譲する。

        Args:
            speaker_id: 発言者ID
            speaker_name: 発言者名（敬称付きの可能性あり）
            speaker_name_yomi: 発言者のふりがな（シグネチャ互換のため保持）
            candidates: マッチング候補の政治家リスト

        Returns:
            マッチング結果（完全一致 confidence=1.0 またはマッチなし confidence=0.0）
        """
        normalized_name = self.normalize_name(speaker_name)

        if not normalized_name or not candidates:
            return self._no_match(speaker_id, speaker_name)

        # 完全一致チェック（正規化後）
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

        return self._no_match(speaker_id, speaker_name)

    def filter_candidates_for_llm(
        self,
        speaker_name: str,
        speaker_name_yomi: str | None,
        candidates: list[PoliticianCandidate],
    ) -> list[PoliticianCandidate]:
        """LLM判定前の候補フィルタリング.

        完全一致しなかったSpeakerに対して、名前部分一致で候補を絞り込む。
        フィルタ基準（OR条件）:
        1. Politician名の各パート（≥2文字）がSpeaker名に含まれる
        2. 漢字姓抽出による一致判定
        3. Speaker name_yomiとPolitician furiganaのプレフィックス一致

        Args:
            speaker_name: 発言者名
            speaker_name_yomi: 発言者のふりがな
            candidates: マッチング候補の政治家リスト

        Returns:
            フィルタリングされた候補リスト（0件の場合あり）
        """
        normalized_name = self.normalize_name(speaker_name)
        if not normalized_name or not candidates:
            return []

        return [
            c
            for c in candidates
            if self._is_candidate_relevant(normalized_name, speaker_name_yomi, c)
        ]

    def _is_candidate_relevant(
        self,
        normalized_speaker_name: str,
        speaker_name_yomi: str | None,
        candidate: PoliticianCandidate,
    ) -> bool:
        """候補がLLM判定に関連するかを判定する.

        3つの基準のいずれかに該当すればTrue:
        1. 名前パート部分一致（スペース分割）
        2. 漢字姓一致（双方向）
        3. ふりがなプレフィックス一致
        """
        normalized_candidate = self.normalize_name(candidate.name)
        if not normalized_candidate:
            return False

        # 基準1: 名前パート部分一致
        # Politician名をスペースで分割し、各パート（≥2文字）がSpeaker名に含まれるか
        candidate_parts = candidate.name.replace("\u3000", " ").split()
        if len(candidate_parts) > 1:
            for part in candidate_parts:
                if len(part) >= 2 and part in normalized_speaker_name:
                    return True
        else:
            # スペースなしの場合、漢字姓を抽出して判定
            # 基準2: 漢字姓一致（候補側 → Speaker名に含まれるか）
            kanji_surname = NameNormalizer.extract_kanji_surname(candidate.name)
            if (
                kanji_surname
                and len(kanji_surname) >= 2
                and kanji_surname != normalized_candidate
                and kanji_surname in normalized_speaker_name
            ):
                return True

        # 基準2追加: 漢字姓一致（Speaker側 → 候補名に含まれるか）
        speaker_kanji_surname = NameNormalizer.extract_kanji_surname(
            normalized_speaker_name
        )
        if (
            speaker_kanji_surname
            and len(speaker_kanji_surname) >= 2
            and speaker_kanji_surname != normalized_speaker_name
            and speaker_kanji_surname in normalized_candidate
        ):
            return True

        # 基準3: ふりがなプレフィックス一致（姓の読みが一致するか）
        if speaker_name_yomi and candidate.furigana:
            normalized_yomi = self._normalize_kana(speaker_name_yomi)
            normalized_furigana = self._normalize_kana(candidate.furigana)
            if normalized_yomi and normalized_furigana:
                # 共通プレフィックス長を計算（姓部分の一致判定）
                common_prefix_len = 0
                for i in range(min(len(normalized_yomi), len(normalized_furigana))):
                    if normalized_yomi[i] == normalized_furigana[i]:
                        common_prefix_len += 1
                    else:
                        break
                # 姓は通常2-4文字 → 3文字以上の共通プレフィックスで候補
                if common_prefix_len >= 3:
                    return True

        return False

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
                if len(matched_candidates) > 1:
                    return None

        if len(matched_candidates) == 1:
            return matched_candidates[0]

        return None

    def _find_surname_matches(
        self, normalized_name: str, candidates: list[PoliticianCandidate]
    ) -> list[PoliticianCandidate]:
        """姓が一致する候補を検索する（最大2件で早期終了）.

        Args:
            normalized_name: 正規化済みの発言者名（姓のみ想定）
            candidates: 候補リスト

        Returns:
            姓が一致した候補リスト（最大2件）
        """
        if not (_MIN_SURNAME_LEN <= len(normalized_name) <= _MAX_SURNAME_LEN):
            return []

        matched: list[PoliticianCandidate] = []
        for candidate in candidates:
            normalized_candidate = self.normalize_name(candidate.name)
            if not normalized_candidate:
                continue
            if normalized_candidate.startswith(normalized_name) and len(
                normalized_name
            ) < len(normalized_candidate):
                matched.append(candidate)
                if len(matched) > 1:
                    return matched
        return matched

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
        matches = self._find_surname_matches(speaker_name, candidates)
        if len(matches) == 1:
            return matches[0]
        return None

    def has_surname_ambiguity(
        self, speaker_name: str, candidates: list[PoliticianCandidate]
    ) -> bool:
        """同姓の候補が複数存在し、姓のみでは特定できないかを判定する.

        Args:
            speaker_name: 発言者名（未正規化でも可）
            candidates: マッチング候補の政治家リスト

        Returns:
            同姓候補が2人以上存在する場合True
        """
        normalized_name = self.normalize_name(speaker_name)
        if not normalized_name or not candidates:
            return False

        return len(self._find_surname_matches(normalized_name, candidates)) >= 2

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
