"""手動検証可能なエンティティのプロトコル定義。

Bronze Layer / Gold Layer アーキテクチャにおいて、
Goldエンティティが人間の修正状態を保持し、AI再実行時に
人間の修正を保護するための共通インターフェースを提供する。
"""

from typing import Protocol


class VerifiableEntity(Protocol):
    """手動検証可能なエンティティのプロトコル。

    Goldエンティティが手動検証状態とLLM抽出ログ参照を
    持つことを示すインターフェース。

    Attributes:
        is_manually_verified: 人間による手動検証が行われたかどうか
        latest_extraction_log_id: 最新のLLM抽出ログへの参照ID

    Methods:
        mark_as_manually_verified: 手動検証済みとしてマークする
        update_from_extraction_log: 最新の抽出ログIDを更新する
        can_be_updated_by_ai: AIによる更新が可能かどうかを返す
    """

    is_manually_verified: bool
    latest_extraction_log_id: int | None

    def mark_as_manually_verified(self) -> None:
        """手動検証済みとしてマークする。

        このメソッドを呼び出すと、is_manually_verifiedがTrueになり、
        以降のAI更新から保護される。
        """
        ...

    def update_from_extraction_log(self, log_id: int) -> None:
        """最新の抽出ログIDを更新する。

        Args:
            log_id: ExtractionLogエンティティのID
        """
        ...

    def can_be_updated_by_ai(self) -> bool:
        """AIによる更新が可能かどうかを返す。

        Returns:
            is_manually_verifiedがFalseの場合True、
            そうでなければFalse
        """
        ...
