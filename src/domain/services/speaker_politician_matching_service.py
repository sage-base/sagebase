"""発言者→政治家マッチングサービス.

完全一致判定 + LLM候補フィルタリングの2機能を提供する。
中間ルール（ふりがな/漢字姓/姓のみ）はLLM判定に委譲済み。
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
    """発言者→政治家マッチングサービス（完全一致 + LLM候補フィルタ）."""

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

        # kanji_name完全一致フォールバック
        for candidate in candidates:
            if candidate.kanji_name:
                normalized_kanji = self.normalize_name(candidate.kanji_name)
                if normalized_name == normalized_kanji:
                    return SpeakerPoliticianMatchResult(
                        speaker_id=speaker_id,
                        speaker_name=speaker_name,
                        politician_id=candidate.politician_id,
                        politician_name=candidate.name,
                        confidence=1.0,
                        match_method=MatchMethod.EXACT_KANJI_NAME,
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

        # Speaker固定値を事前計算（候補ごとに再計算しない）
        speaker_kanji_surname = NameNormalizer.extract_kanji_surname(normalized_name)
        normalized_yomi = (
            self._normalize_kana(speaker_name_yomi) if speaker_name_yomi else None
        )

        return [
            c
            for c in candidates
            if self._is_candidate_relevant(
                normalized_name,
                speaker_kanji_surname,
                normalized_yomi,
                c,
            )
        ]

    def _is_candidate_relevant(
        self,
        normalized_speaker_name: str,
        speaker_kanji_surname: str | None,
        normalized_speaker_yomi: str | None,
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
        if (
            speaker_kanji_surname
            and len(speaker_kanji_surname) >= 2
            and speaker_kanji_surname != normalized_speaker_name
            and speaker_kanji_surname in normalized_candidate
        ):
            return True

        # 基準3: ふりがなプレフィックス一致（姓の読みが一致するか）
        if normalized_speaker_yomi and candidate.furigana:
            normalized_furigana = self._normalize_kana(candidate.furigana)
            if normalized_speaker_yomi and normalized_furigana:
                # 共通プレフィックス長を計算（姓部分の一致判定）
                common_prefix_len = 0
                for i in range(
                    min(len(normalized_speaker_yomi), len(normalized_furigana))
                ):
                    if normalized_speaker_yomi[i] == normalized_furigana[i]:
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
