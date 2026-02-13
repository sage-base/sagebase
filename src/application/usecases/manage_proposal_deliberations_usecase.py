"""議案審議（ProposalDeliberation）管理ユースケース.

議案と会議の多対多紐付けを管理するユースケース。
"""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities.proposal_deliberation import ProposalDeliberation
from src.domain.repositories.proposal_deliberation_repository import (
    ProposalDeliberationRepository,
)


@dataclass
class ListDeliberationsInputDto:
    """審議一覧取得の入力DTO."""

    proposal_id: int | None = None
    conference_id: int | None = None
    meeting_id: int | None = None


@dataclass
class ListDeliberationsOutputDto:
    """審議一覧取得の出力DTO."""

    deliberations: list[ProposalDeliberation]
    total_count: int


@dataclass
class CreateDeliberationInputDto:
    """審議作成の入力DTO."""

    proposal_id: int
    conference_id: int
    meeting_id: int | None = None
    stage: str | None = None


@dataclass
class CreateDeliberationOutputDto:
    """審議作成の出力DTO."""

    success: bool
    message: str
    deliberation: ProposalDeliberation | None = None


@dataclass
class DeleteDeliberationInputDto:
    """審議削除の入力DTO."""

    deliberation_id: int


@dataclass
class DeleteDeliberationOutputDto:
    """審議削除の出力DTO."""

    success: bool
    message: str


class ManageProposalDeliberationsUseCase:
    """議案審議管理ユースケース."""

    def __init__(
        self,
        repository: ProposalDeliberationRepository,
    ):
        self.repository = repository
        self.logger = get_logger(self.__class__.__name__)

    async def list_deliberations(
        self, input_dto: ListDeliberationsInputDto
    ) -> ListDeliberationsOutputDto:
        try:
            if input_dto.proposal_id is not None:
                deliberations = await self.repository.get_by_proposal_id(
                    input_dto.proposal_id
                )
            elif input_dto.conference_id is not None:
                deliberations = await self.repository.get_by_conference_id(
                    input_dto.conference_id
                )
            elif input_dto.meeting_id is not None:
                deliberations = await self.repository.get_by_meeting_id(
                    input_dto.meeting_id
                )
            else:
                deliberations = await self.repository.get_all()

            return ListDeliberationsOutputDto(
                deliberations=deliberations,
                total_count=len(deliberations),
            )
        except Exception as e:
            self.logger.error(f"Error listing deliberations: {e}", exc_info=True)
            raise

    async def create_deliberation(
        self, input_dto: CreateDeliberationInputDto
    ) -> CreateDeliberationOutputDto:
        try:
            existing = await self.repository.find_by_proposal_and_conference(
                proposal_id=input_dto.proposal_id,
                conference_id=input_dto.conference_id,
                meeting_id=input_dto.meeting_id,
                stage=input_dto.stage,
            )
            if existing:
                return CreateDeliberationOutputDto(
                    success=False,
                    message="同一の議案審議紐付けが既に存在します",
                    deliberation=existing,
                )

            entity = ProposalDeliberation(
                proposal_id=input_dto.proposal_id,
                conference_id=input_dto.conference_id,
                meeting_id=input_dto.meeting_id,
                stage=input_dto.stage,
            )
            created = await self.repository.create(entity)

            return CreateDeliberationOutputDto(
                success=True,
                message="議案審議紐付けを作成しました",
                deliberation=created,
            )
        except Exception as e:
            self.logger.error(f"Error creating deliberation: {e}", exc_info=True)
            return CreateDeliberationOutputDto(
                success=False,
                message=f"作成中にエラーが発生しました: {str(e)}",
            )

    async def delete_deliberation(
        self, input_dto: DeleteDeliberationInputDto
    ) -> DeleteDeliberationOutputDto:
        try:
            existing = await self.repository.get_by_id(input_dto.deliberation_id)
            if not existing:
                return DeleteDeliberationOutputDto(
                    success=False,
                    message=f"審議ID {input_dto.deliberation_id} が見つかりません",
                )

            success = await self.repository.delete(input_dto.deliberation_id)
            if success:
                return DeleteDeliberationOutputDto(
                    success=True,
                    message="議案審議紐付けを削除しました",
                )
            return DeleteDeliberationOutputDto(
                success=False,
                message="削除に失敗しました",
            )
        except Exception as e:
            self.logger.error(f"Error deleting deliberation: {e}", exc_info=True)
            return DeleteDeliberationOutputDto(
                success=False,
                message=f"削除中にエラーが発生しました: {str(e)}",
            )
