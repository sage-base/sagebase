"""会議体メンバーエンティティをAI抽出結果から更新するUseCase。"""

import logging

from typing import Any

from src.application.dtos.extraction_result.conference_member_extraction_result import (
    ConferenceMemberExtractionResult,
)
from src.application.usecases.base.update_entity_from_extraction_usecase import (
    UpdateEntityFromExtractionUseCase,
)
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.entities.extraction_log import EntityType
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository
from src.domain.repositories.session_adapter import ISessionAdapter


logger = logging.getLogger(__name__)


class UpdateExtractedConferenceMemberFromExtractionUseCase(
    UpdateEntityFromExtractionUseCase[
        ExtractedConferenceMember, ConferenceMemberExtractionResult
    ]
):
    """会議体メンバーエンティティをAI抽出結果から更新するUseCase。

    人間による手動修正を保護しつつ、AI抽出結果で会議体メンバーエンティティを更新する。

    Attributes:
        _extracted_conference_member_repo: 会議体メンバーリポジトリ
        _extraction_log_repo: 抽出ログリポジトリ
        _session: セッションアダプター
    """

    def __init__(
        self,
        extracted_conference_member_repo: ExtractedConferenceMemberRepository,
        extraction_log_repo: ExtractionLogRepository,
        session_adapter: ISessionAdapter,
    ) -> None:
        """UseCaseを初期化する。

        Args:
            extracted_conference_member_repo: 会議体メンバーリポジトリ
            extraction_log_repo: 抽出ログリポジトリ
            session_adapter: セッションアダプター
        """
        super().__init__(extraction_log_repo, session_adapter)
        self._extracted_conference_member_repo = extracted_conference_member_repo

    def _get_entity_type(self) -> EntityType:
        """エンティティタイプを返す。

        Returns:
            EntityType.CONFERENCE_MEMBER
        """
        return EntityType.CONFERENCE_MEMBER

    async def _get_entity(self, entity_id: int) -> ExtractedConferenceMember | None:
        """会議体メンバーエンティティを取得する。

        Args:
            entity_id: 会議体メンバーID

        Returns:
            会議体メンバーエンティティ、存在しない場合はNone
        """
        return await self._extracted_conference_member_repo.get_by_id(entity_id)

    async def _save_entity(self, entity: ExtractedConferenceMember) -> None:
        """会議体メンバーエンティティを保存する。

        Args:
            entity: 保存する会議体メンバーエンティティ
        """
        await self._extracted_conference_member_repo.update(entity)

    def _to_extracted_data(  # type: ignore[override]
        self, result: ConferenceMemberExtractionResult
    ) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Args:
            result: 会議体メンバー抽出結果

        Returns:
            抽出データのdict表現
        """
        return result.to_dict()

    async def _apply_extraction(
        self,
        entity: ExtractedConferenceMember,
        result: ConferenceMemberExtractionResult,
        log_id: int,
    ) -> None:
        """抽出結果を会議体メンバーエンティティに適用する。

        抽出結果をエンティティの各フィールドに反映し、
        抽出ログIDを更新する。

        Args:
            entity: 更新対象の会議体メンバーエンティティ
            result: 抽出結果
            log_id: 抽出ログID
        """
        # 抽出結果を各フィールドに反映
        entity.extracted_name = result.extracted_name
        entity.source_url = result.source_url
        if result.extracted_role is not None:
            entity.extracted_role = result.extracted_role
        if result.extracted_party_name is not None:
            entity.extracted_party_name = result.extracted_party_name
        if result.additional_data is not None:
            entity.additional_data = result.additional_data

        # 抽出ログIDを更新
        entity.update_from_extraction_log(log_id)

        logger.debug(
            f"Applied extraction to ExtractedConferenceMember id={entity.id}, "
            f"log_id={log_id}"
        )

    def _get_confidence_score(  # type: ignore[override]
        self, result: ConferenceMemberExtractionResult
    ) -> float | None:
        """信頼度スコアを取得する。

        Args:
            result: 抽出結果

        Returns:
            信頼度スコア（0.0〜1.0）、または取得できない場合はNone
        """
        return result.confidence_score
