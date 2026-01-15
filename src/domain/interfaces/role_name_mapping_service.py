"""Role-Name Mapping service interface

役職-人名マッピング抽出サービスの抽象インターフェース。
Clean Architectureの原則に従い、ドメイン層で定義されています。
"""

from abc import ABC, abstractmethod

from src.domain.dtos.role_name_mapping_dto import RoleNameMappingResultDTO


class IRoleNameMappingService(ABC):
    """役職-人名マッピング抽出サービスのインターフェース

    議事録の出席者情報から役職と人名の対応を抽出する責務を持ちます。
    具体的な実装（BAML、ルールベースなど）はインフラストラクチャ層で提供されます。
    """

    @abstractmethod
    async def extract_role_name_mapping(
        self, attendee_text: str
    ) -> RoleNameMappingResultDTO:
        """出席者テキストから役職-人名マッピングを抽出

        Args:
            attendee_text: 議事録の出席者情報テキスト

        Returns:
            RoleNameMappingResultDTO: 抽出された役職-人名マッピング結果

        Note:
            - 実装は非同期で動作する必要があります
            - エラー時は空のマッピングと低い信頼度を返すか、適切な例外を投げてください
        """
        pass
