"""会議体メンバーの抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ConferenceMemberExtractionResult:
    """会議体メンバーのAI抽出結果を表すDTO。

    HTMLから抽出された会議体メンバー情報を表現します。
    BAMLを使用した抽出処理の結果を保持し、
    抽出ログへの記録に使用されます。

    Attributes:
        conference_id: 会議体ID
        extracted_name: 抽出された議員名
        source_url: 抽出元URL
        extracted_role: 抽出された役職（議長、副議長、委員長など）
        extracted_party_name: 抽出された所属政党名
        additional_data: その他の抽出情報
        confidence_score: 抽出の信頼度 (0.0-1.0)
    """

    conference_id: int
    extracted_name: str
    source_url: str
    extracted_role: str | None = None
    extracted_party_name: str | None = None
    additional_data: str | None = None
    confidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現
        """
        return asdict(self)
