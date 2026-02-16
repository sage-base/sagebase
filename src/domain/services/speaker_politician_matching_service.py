"""発言者→政治家ルールベースマッチングサービス.

ConferenceMemberで絞り込んだ候補リストに対して、
名前・ふりがなベースのルールマッチングを行う。
DB非依存の純粋なドメインロジック。
"""

import re

from src.domain.value_objects.speaker_politician_match_result import (
    MatchMethod,
    PoliticianCandidate,
    SpeakerPoliticianMatchResult,
)


# 末尾から除去する敬称
# 長い順にソートし「副議長」が「議長」より先にマッチするようにする
_HONORIFICS = sorted(
    [
        "副委員長",
        "委員長",
        "副議長",
        "議長",
        "副市長",
        "市長",
        "副知事",
        "知事",
        "議員",
        "先生",
        "殿",
        "氏",
        "さん",
        "くん",
        "君",
        "様",
    ],
    key=len,
    reverse=True,
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
        3. 姓のみ一致（同姓候補1人のみ）→ confidence: 0.8
        4. マッチなし → confidence: 0.0

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

        # 3. 姓のみ一致チェック（同姓候補が1人のみの場合）
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
        """名前を正規化する（敬称除去、スペース除去）."""
        normalized = name.strip()
        # 全角・半角スペースを除去
        normalized = re.sub(r"[\s　]+", "", normalized)
        # 末尾から敬称を除去
        for honorific in _HONORIFICS:
            if normalized.endswith(honorific):
                normalized = normalized[: -len(honorific)]
                break
        return normalized.strip()

    def _normalize_kana(self, kana: str) -> str:
        """ふりがなを正規化する（カタカナ→ひらがな変換、スペース除去）."""
        normalized = kana.strip()
        normalized = re.sub(r"[\s　]+", "", normalized)
        # カタカナをひらがなに変換
        normalized = self._katakana_to_hiragana(normalized)
        return normalized

    @staticmethod
    def _katakana_to_hiragana(text: str) -> str:
        """カタカナをひらがなに変換する."""
        result = []
        for char in text:
            code = ord(char)
            # カタカナ範囲(0x30A1-0x30F6)をひらがな(0x3041-0x3096)に変換
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)

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
