"""議員団メンバーの抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ParliamentaryGroupMemberExtractionResult:
    """議員団メンバーのAI抽出結果を表すDTO。

    URLから抽出された議員団メンバー情報を表現します。
    BAMLを使用した抽出処理の結果を保持し、
    抽出ログへの記録に使用されます。

    Attributes:
        parliamentary_group_id: 議員団ID
        extracted_name: 抽出された議員名
        source_url: 抽出元URL
        extracted_role: 抽出された役職
        extracted_party_name: 抽出された所属政党名
        extracted_district: 抽出された選挙区
        additional_info: その他の抽出情報
        confidence_score: 抽出の信頼度 (0.0-1.0)
    """

    parliamentary_group_id: int
    extracted_name: str
    source_url: str
    extracted_role: str | None = None
    extracted_party_name: str | None = None
    extracted_district: str | None = None
    additional_info: str | None = None
    confidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現
        """
        return asdict(self)
