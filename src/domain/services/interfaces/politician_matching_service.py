"""政治家マッチングサービスのインターフェース定義

このモジュールは、政治家マッチングサービスの抽象化層を提供します。
Domain層に配置され、Infrastructure層の実装から実装されます。
"""

from typing import Any, Protocol

from src.domain.value_objects.politician_match import PoliticianMatch


class IPoliticianMatchingService(Protocol):
    """政治家マッチングサービスのインターフェース

    発言者と政治家のマッチング処理を行うサービスの抽象化。
    Infrastructure層で具体的な実装（BAMLベース等）が提供されます。

    実装クラス:
        - BAMLPoliticianMatchingService: BAMLを使用した実装
    """

    async def find_best_match(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
        role_name_mappings: dict[str, str] | None = None,
    ) -> PoliticianMatch:
        """発言者に最適な政治家マッチを見つける

        ルールベースマッチング（高速パス）とLLMマッチングのハイブリッドアプローチで
        発言者と政治家のマッチングを行います。

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別（例: "議員", "委員"など）
            speaker_party: 発言者の所属政党（もしあれば）
            role_name_mappings: 役職-人名マッピング辞書（例: {"議長": "伊藤条一"}）
                役職のみの発言者名を実名に解決するために使用

        Returns:
            PoliticianMatch: マッチング結果
                （マッチの有無、政治家情報、信頼度、理由を含む）
        """
        ...

    async def find_best_match_from_candidates(
        self,
        speaker_name: str,
        candidates: list[dict[str, Any]],
        speaker_type: str | None = None,
        speaker_party: str | None = None,
        role_name_mappings: dict[str, str] | None = None,
    ) -> PoliticianMatch:
        """外部から提供された候補リストを使って発言者に最適な政治家マッチを見つける.

        find_best_matchと同じロジックだが、内部でpolitician_repositoryから
        候補を取得する代わりに、引数で渡された候補リストを使用する。
        ConferenceMemberでスコープされた候補リストを渡す場合に使用。

        Args:
            speaker_name: マッチングする発言者名
            candidates: 候補政治家のリスト。各dictは少なくとも
                "id", "name" を含む。"party_name" はオプション。
            speaker_type: 発言者の種別
            speaker_party: 発言者の所属政党
            role_name_mappings: 役職-人名マッピング辞書

        Returns:
            PoliticianMatch: マッチング結果
        """
        ...
