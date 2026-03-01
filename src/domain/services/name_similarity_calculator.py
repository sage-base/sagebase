"""名前類似度計算ユーティリティ。

各ドメインサービスに分散していた名前類似度計算ロジックを統合する。
前処理（正規化・敬称除去等）は呼び出し側の責任。
このクラスは正規化済み文字列に対する純粋な類似度計算のみを担当する。
"""

from difflib import SequenceMatcher
from typing import Literal


MatchType = Literal["exact", "partial", "fuzzy", "none"]


class NameSimilarityCalculator:
    """名前の類似度を計算するユーティリティクラス。"""

    @staticmethod
    def jaccard(name1: str, name2: str) -> float:
        """Jaccard係数による文字集合ベースの類似度を計算する。

        intersection(name1, name2) / union(name1, name2) を返す。

        Args:
            name1: 比較対象の名前1（正規化済み）
            name2: 比較対象の名前2（正規化済み）

        Returns:
            0.0〜1.0 の類似度スコア
        """
        if name1 == name2:
            return 1.0

        chars1 = set(name1)
        chars2 = set(name2)

        if not chars1 or not chars2:
            return 0.0

        intersection = chars1 & chars2
        union = chars1 | chars2

        return len(intersection) / len(union)

    @staticmethod
    def jaccard_with_containment(
        name1: str,
        name2: str,
        containment_score: float = 0.9,
    ) -> float:
        """包含チェック付きJaccard係数による類似度を計算する。

        一方が他方を含む場合は containment_score を返す。
        そうでなければJaccard係数を返す。

        Args:
            name1: 比較対象の名前1（正規化済み）
            name2: 比較対象の名前2（正規化済み）
            containment_score: 包含時に返すスコア（デフォルト: 0.9）

        Returns:
            0.0〜1.0 の類似度スコア
        """
        if name1 == name2:
            return 1.0

        if name1 in name2 or name2 in name1:
            return containment_score

        return NameSimilarityCalculator.jaccard(name1, name2)

    @staticmethod
    def sequence_ratio(name1: str, name2: str) -> float:
        """SequenceMatcherベースの類似度を計算する。

        difflib.SequenceMatcher.ratio() を使用。
        文字の順序を考慮した類似度を返す。
        重複排除など文字順序が重要な用途に適している。

        Args:
            name1: 比較対象の名前1（正規化済み）
            name2: 比較対象の名前2（正規化済み）

        Returns:
            0.0〜1.0 の類似度スコア
        """
        if not name1 or not name2:
            return 0.0

        return SequenceMatcher(None, name1, name2).ratio()

    @staticmethod
    def staged_match(
        name1: str,
        name2: str,
        partial_score: float = 0.8,
        word_match_score: float = 0.6,
        fuzzy_threshold: float = 0.5,
        fuzzy_factor: float = 0.5,
    ) -> tuple[float, MatchType]:
        """段階的マッチングによる類似度を計算する。

        以下の順序で判定する:
        1. 完全一致 → (1.0, "exact")
        2. 包含チェック → (partial_score, "partial")
        3. 単語一致（2文字以上） → (word_match_score, "fuzzy")
        4. 文字集合の重なり → (score, "fuzzy") / (0.0, "none")

        Args:
            name1: 比較対象の名前1（正規化済み）
            name2: 比較対象の名前2（正規化済み）
            partial_score: 包含一致時のスコア
            word_match_score: 単語一致時のスコア
            fuzzy_threshold: あいまいマッチの閾値
            fuzzy_factor: あいまいマッチのスコア係数

        Returns:
            (score, match_type) のタプル
        """
        if name1 == name2:
            return 1.0, "exact"

        if name1 in name2 or name2 in name1:
            return partial_score, "partial"

        # 単語一致（2文字以上の単語が相手の単語リストに含まれる）
        parts1 = name1.split()
        parts2 = name2.split()
        if any(p in parts2 for p in parts1 if len(p) >= 2):
            return word_match_score, "fuzzy"

        # 文字集合の重なりによるあいまいマッチ
        # len(共通文字集合) / max(文字列長) で計算（Jaccard係数とは異なる指標）
        if len(name1) > 0 and len(name2) > 0:
            common_chars = set(name1) & set(name2)
            similarity = len(common_chars) / max(len(name1), len(name2))
            if similarity > fuzzy_threshold:
                return similarity * fuzzy_factor, "fuzzy"

        return 0.0, "none"
