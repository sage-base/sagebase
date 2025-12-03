"""Parliamentary group member extraction DTOs

議員団メンバー抽出のためのデータ転送オブジェクト。
レイヤー間でメンバー情報をやり取りする際に使用されます。

Clean Architectureの原則に従い、フレームワーク非依存のdataclassを使用しています。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedParliamentaryGroupMemberDTO:
    """抽出された議員団メンバー情報のDTO

    HTMLからLLMによって抽出されたメンバー情報を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。

    フレームワーク非依存のdataclassとして実装されており、
    Pydanticなどの外部ライブラリに依存しません。
    """

    name: str
    role: str | None = None
    party_name: str | None = None
    district: str | None = None
    additional_info: str | None = None


@dataclass
class ParliamentaryGroupMemberExtractionResultDTO:
    """議員団メンバー抽出結果のDTO

    議員団URLからのメンバー抽出結果を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。

    フレームワーク非依存のdataclassとして実装されており、
    Pydanticなどの外部ライブラリに依存しません。
    """

    parliamentary_group_id: int
    url: str
    extracted_members: list[ExtractedParliamentaryGroupMemberDTO]
    extraction_date: datetime | None = None
    error: str | None = None
