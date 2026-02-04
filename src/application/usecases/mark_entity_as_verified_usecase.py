"""手動検証フラグ更新UseCase。

VerifiableEntityプロトコルを実装したエンティティの手動検証フラグを
更新するための汎用的なUseCase。

Note:
    CONFERENCE_MEMBERとPARLIAMENTARY_GROUP_MEMBERは対象外。
    これらはBronze Layerエンティティであり、検証状態はGold Layer
    （ConferenceMember、ParliamentaryGroupMembership）で管理されるため。
"""

from dataclasses import dataclass
from enum import Enum

from src.common.logging import get_logger
from src.domain.repositories import (
    ConversationRepository,
)


logger = get_logger(__name__)


class EntityType(Enum):
    """手動検証可能なエンティティタイプ。"""

    CONVERSATION = "conversation"


@dataclass
class MarkEntityAsVerifiedInputDto:
    """手動検証フラグ更新の入力DTO。"""

    entity_type: EntityType
    entity_id: int
    is_verified: bool


@dataclass
class MarkEntityAsVerifiedOutputDto:
    """手動検証フラグ更新の出力DTO。"""

    success: bool
    error_message: str | None = None


class MarkEntityAsVerifiedUseCase:
    """手動検証フラグ更新UseCase。

    各エンティティの手動検証フラグを更新する汎用的なUseCase。
    エンティティタイプに応じて適切なリポジトリを使用する。
    """

    def __init__(
        self,
        conversation_repository: ConversationRepository | None = None,
    ):
        """初期化。

        Args:
            conversation_repository: 発言リポジトリ
        """
        self._conversation_repo = conversation_repository

    async def execute(
        self, input_dto: MarkEntityAsVerifiedInputDto
    ) -> MarkEntityAsVerifiedOutputDto:
        """手動検証フラグを更新する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO
        """
        try:
            if input_dto.entity_type == EntityType.CONVERSATION:
                return await self._update_conversation(
                    input_dto.entity_id, input_dto.is_verified
                )
            else:
                return MarkEntityAsVerifiedOutputDto(
                    success=False,
                    error_message=f"Unknown entity type: {input_dto.entity_type}",
                )
        except Exception as e:
            logger.error(f"Failed to update verification status: {e}")
            return MarkEntityAsVerifiedOutputDto(success=False, error_message=str(e))

    async def _update_conversation(
        self, entity_id: int, is_verified: bool
    ) -> MarkEntityAsVerifiedOutputDto:
        """発言の手動検証フラグを更新する。"""
        if not self._conversation_repo:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="Conversation repository not configured",
            )

        entity = await self._conversation_repo.get_by_id(entity_id)
        if not entity:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="発言が見つかりません。",
            )

        if is_verified:
            entity.mark_as_manually_verified()
        else:
            entity.is_manually_verified = False

        await self._conversation_repo.update(entity)
        return MarkEntityAsVerifiedOutputDto(success=True)
