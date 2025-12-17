"""政党メンバー抽出のデータ転送オブジェクト

政党メンバー抽出のためのデータ転送オブジェクト。
レイヤー間でメンバー情報をやり取りする際に使用されます。

Clean Architectureの原則に従い、フレームワーク非依存のdataclassを使用しています。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedPartyMemberDTO:
    """抽出された政党メンバー情報のDTO

    HTMLからLLMによって抽出されたメンバー情報を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。

    フレームワーク非依存のdataclassとして実装されており、
    Pydanticなどの外部ライブラリに依存しません。
    """

    name: str
    position: str | None = None
    electoral_district: str | None = None
    prefecture: str | None = None
    profile_url: str | None = None
    party_position: str | None = None


@dataclass
class PartyMemberExtractionResultDTO:
    """政党メンバー抽出結果のDTO

    政党URLからのメンバー抽出結果を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。

    フレームワーク非依存のdataclassとして実装されており、
    Pydanticなどの外部ライブラリに依存しません。
    """

    party_id: int
    url: str
    extracted_members: list[ExtractedPartyMemberDTO]
    extraction_date: datetime | None = None
    error: str | None = None
