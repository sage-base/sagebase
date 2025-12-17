"""ExtractedPartyMember entity."""

from datetime import datetime

from src.domain.entities.base import BaseEntity


class ExtractedPartyMember(BaseEntity):
    """政党メンバー抽出情報を表すエンティティ.

    このエンティティは、政党のウェブサイトから抽出された
    議員情報を表します。フレームワーク非依存の純粋なドメインモデルです。
    """

    def __init__(
        self,
        party_id: int,
        extracted_name: str,
        source_url: str,
        extracted_position: str | None = None,
        extracted_electoral_district: str | None = None,
        extracted_prefecture: str | None = None,
        profile_url: str | None = None,
        party_position: str | None = None,
        extracted_at: datetime | None = None,
        matched_politician_id: int | None = None,
        matching_confidence: float | None = None,
        matching_status: str = "pending",
        matched_at: datetime | None = None,
        additional_info: str | None = None,
        id: int | None = None,
    ) -> None:
        """Initialize ExtractedPartyMember.

        Args:
            party_id: 政党ID
            extracted_name: 抽出された議員名
            source_url: 抽出元URL
            extracted_position: 抽出された役職（衆議院議員、参議院議員など）
            extracted_electoral_district: 抽出された選挙区
            extracted_prefecture: 抽出された都道府県
            profile_url: プロフィールページURL
            party_position: 党内役職
            extracted_at: 抽出日時
            matched_politician_id: マッチした政治家ID
            matching_confidence: マッチング信頼度（0.0-1.0）
            matching_status: マッチング状態（pending, matched, no_match）
            matched_at: マッチング実施日時
            additional_info: 追加情報（JSON形式など）
            id: エンティティID
        """
        super().__init__(id)
        self.party_id = party_id
        self.extracted_name = extracted_name
        self.source_url = source_url
        self.extracted_position = extracted_position
        self.extracted_electoral_district = extracted_electoral_district
        self.extracted_prefecture = extracted_prefecture
        self.profile_url = profile_url
        self.party_position = party_position
        self.extracted_at = extracted_at or datetime.now()
        self.matched_politician_id = matched_politician_id
        self.matching_confidence = matching_confidence
        self.matching_status = matching_status
        self.matched_at = matched_at
        self.additional_info = additional_info

    def is_matched(self) -> bool:
        """マッチング済みかどうかを確認.

        Returns:
            bool: マッチング済みの場合True
        """
        return self.matching_status == "matched"

    def is_no_match(self) -> bool:
        """マッチング実行済みだが該当なしかどうかを確認.

        Returns:
            bool: マッチング実行済みで該当なしの場合True
        """
        return self.matching_status == "no_match"

    def is_pending(self) -> bool:
        """マッチング未実行かどうかを確認.

        Returns:
            bool: マッチング未実行の場合True
        """
        return self.matching_status == "pending"

    def __str__(self) -> str:
        """文字列表現を返す."""
        return (
            f"ExtractedPartyMember(name={self.extracted_name}, "
            f"party_id={self.party_id}, "
            f"status={self.matching_status})"
        )

    def __repr__(self) -> str:
        """開発者向け文字列表現を返す."""
        return (
            f"ExtractedPartyMember("
            f"id={self.id}, "
            f"party_id={self.party_id}, "
            f"name={self.extracted_name!r}, "
            f"position={self.extracted_position!r}, "
            f"status={self.matching_status})"
        )
