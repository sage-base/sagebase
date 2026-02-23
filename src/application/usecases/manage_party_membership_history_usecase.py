"""政党所属履歴管理ユースケース."""

from src.application.dtos.party_membership_history_dto import (
    CreateMembershipInputDto,
    CreateMembershipOutputDto,
    EndMembershipInputDto,
    EndMembershipOutputDto,
    GetCurrentPartyInputDto,
    GetCurrentPartyOutputDto,
    GetHistoryByPoliticianInputDto,
    GetHistoryByPoliticianOutputDto,
    PartyMembershipHistoryOutputItem,
)
from src.common.logging import get_logger
from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)


class ManagePartyMembershipHistoryUseCase:
    """政党所属履歴を管理するユースケース."""

    def __init__(self, repository: PartyMembershipHistoryRepository):
        self.repository = repository
        self.logger = get_logger(self.__class__.__name__)

    async def get_history_by_politician(
        self, input_dto: GetHistoryByPoliticianInputDto
    ) -> GetHistoryByPoliticianOutputDto:
        """政治家の所属履歴を取得する."""
        try:
            entities = await self.repository.get_by_politician(input_dto.politician_id)
            items = [PartyMembershipHistoryOutputItem.from_entity(e) for e in entities]
            return GetHistoryByPoliticianOutputDto(items=items)
        except Exception as e:
            self.logger.error(f"政党所属履歴の取得に失敗しました: {e}", exc_info=True)
            raise

    async def get_current_party(
        self, input_dto: GetCurrentPartyInputDto
    ) -> GetCurrentPartyOutputDto:
        """政治家の現在の政党所属を取得する."""
        try:
            entity = await self.repository.get_current_by_politician(
                input_dto.politician_id, input_dto.as_of_date
            )
            item = (
                PartyMembershipHistoryOutputItem.from_entity(entity) if entity else None
            )
            return GetCurrentPartyOutputDto(item=item)
        except Exception as e:
            self.logger.error(f"現在の政党所属の取得に失敗しました: {e}", exc_info=True)
            raise

    async def create_membership(
        self, input_dto: CreateMembershipInputDto
    ) -> CreateMembershipOutputDto:
        """所属履歴を作成する."""
        try:
            entity = PartyMembershipHistory(
                politician_id=input_dto.politician_id,
                political_party_id=input_dto.political_party_id,
                start_date=input_dto.start_date,
                end_date=input_dto.end_date,
            )
            created = await self.repository.create(entity)
            item = PartyMembershipHistoryOutputItem.from_entity(created)
            return CreateMembershipOutputDto(
                success=True,
                message="政党所属履歴を作成しました",
                item=item,
            )
        except Exception as e:
            self.logger.error(f"政党所属履歴の作成に失敗しました: {e}", exc_info=True)
            return CreateMembershipOutputDto(
                success=False,
                message=f"作成中にエラーが発生しました: {e!s}",
            )

    async def end_membership(
        self, input_dto: EndMembershipInputDto
    ) -> EndMembershipOutputDto:
        """所属を終了する."""
        try:
            entity = await self.repository.end_membership(
                input_dto.membership_id, input_dto.end_date
            )
            if entity is None:
                return EndMembershipOutputDto(
                    success=False,
                    message=f"所属履歴ID {input_dto.membership_id} が見つかりません",
                )
            item = PartyMembershipHistoryOutputItem.from_entity(entity)
            return EndMembershipOutputDto(
                success=True,
                message="政党所属を終了しました",
                item=item,
            )
        except Exception as e:
            self.logger.error(f"政党所属の終了に失敗しました: {e}", exc_info=True)
            return EndMembershipOutputDto(
                success=False,
                message=f"終了処理中にエラーが発生しました: {e!s}",
            )
