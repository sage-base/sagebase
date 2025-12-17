"""政党メンバー抽出サービスのインターフェース

政党のWebページからメンバー情報を抽出する責務を持ちます。
具体的な実装（Pydantic, BAMLなど）はインフラストラクチャ層で提供されます。
"""

from abc import ABC, abstractmethod

from src.domain.dtos.party_member_dto import PartyMemberExtractionResultDTO


class IPartyMemberExtractorService(ABC):
    """政党メンバー抽出サービスのインターフェース"""

    @abstractmethod
    async def extract_members(
        self, party_id: int, url: str
    ) -> PartyMemberExtractionResultDTO:
        """政党URLからメンバー情報を抽出する

        Args:
            party_id: 政党ID
            url: 政党メンバー一覧のURL

        Returns:
            PartyMemberExtractionResultDTO: 抽出結果

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時はerrorフィールドにエラーメッセージを設定してください
            - HTMLの取得とLLMによる抽出を含む完全な処理を実行します
        """
        pass
