"""選挙結果メンバー管理のユースケース."""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository


logger = get_logger(__name__)


# Input DTOs


@dataclass
class ListElectionMembersByElectionInputDto:
    """選挙ID別メンバー一覧取得の入力DTO."""

    election_id: int


@dataclass
class ListElectionMembersByPoliticianInputDto:
    """政治家ID別選挙結果一覧取得の入力DTO."""

    politician_id: int


@dataclass
class CreateElectionMemberInputDto:
    """選挙結果メンバー作成の入力DTO."""

    election_id: int
    politician_id: int
    result: str
    votes: int | None = None
    rank: int | None = None


@dataclass
class UpdateElectionMemberInputDto:
    """選挙結果メンバー更新の入力DTO."""

    id: int
    election_id: int
    politician_id: int
    result: str
    votes: int | None = None
    rank: int | None = None


@dataclass
class DeleteElectionMemberInputDto:
    """選挙結果メンバー削除の入力DTO."""

    id: int


# Output DTOs


@dataclass
class ListElectionMembersOutputDto:
    """選挙結果メンバー一覧取得の出力DTO."""

    election_members: list[ElectionMember]
    success: bool = True
    error_message: str | None = None


@dataclass
class CreateElectionMemberOutputDto:
    """選挙結果メンバー作成の出力DTO."""

    success: bool
    election_member_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdateElectionMemberOutputDto:
    """選挙結果メンバー更新の出力DTO."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteElectionMemberOutputDto:
    """選挙結果メンバー削除の出力DTO."""

    success: bool
    error_message: str | None = None


class ManageElectionMembersUseCase:
    """選挙結果メンバー管理のユースケース."""

    def __init__(self, election_member_repository: ElectionMemberRepository) -> None:
        """ユースケースを初期化する.

        Args:
            election_member_repository: 選挙結果メンバーリポジトリインスタンス
        """
        self.election_member_repository = election_member_repository

    async def list_by_election(
        self, input_dto: ListElectionMembersByElectionInputDto
    ) -> ListElectionMembersOutputDto:
        """選挙IDに属するメンバー一覧を取得する."""
        try:
            members = await self.election_member_repository.get_by_election_id(
                input_dto.election_id
            )
            return ListElectionMembersOutputDto(election_members=members)
        except Exception as e:
            logger.error(f"Failed to list election members by election: {e}")
            return ListElectionMembersOutputDto(
                election_members=[], success=False, error_message=str(e)
            )

    async def list_by_politician(
        self, input_dto: ListElectionMembersByPoliticianInputDto
    ) -> ListElectionMembersOutputDto:
        """政治家IDに紐づく選挙結果一覧を取得する."""
        try:
            members = await self.election_member_repository.get_by_politician_id(
                input_dto.politician_id
            )
            return ListElectionMembersOutputDto(election_members=members)
        except Exception as e:
            logger.error(f"Failed to list election members by politician: {e}")
            return ListElectionMembersOutputDto(
                election_members=[], success=False, error_message=str(e)
            )

    async def create_election_member(
        self, input_dto: CreateElectionMemberInputDto
    ) -> CreateElectionMemberOutputDto:
        """選挙結果メンバーを作成する."""
        try:
            election_member = ElectionMember(
                election_id=input_dto.election_id,
                politician_id=input_dto.politician_id,
                result=input_dto.result,
                votes=input_dto.votes,
                rank=input_dto.rank,
            )

            created = await self.election_member_repository.create(election_member)
            return CreateElectionMemberOutputDto(
                success=True, election_member_id=created.id
            )
        except Exception as e:
            logger.error(f"Failed to create election member: {e}")
            return CreateElectionMemberOutputDto(success=False, error_message=str(e))

    async def update_election_member(
        self, input_dto: UpdateElectionMemberInputDto
    ) -> UpdateElectionMemberOutputDto:
        """選挙結果メンバーを更新する."""
        try:
            existing = await self.election_member_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateElectionMemberOutputDto(
                    success=False, error_message="選挙結果メンバーが見つかりません。"
                )

            election_member = ElectionMember(
                id=input_dto.id,
                election_id=input_dto.election_id,
                politician_id=input_dto.politician_id,
                result=input_dto.result,
                votes=input_dto.votes,
                rank=input_dto.rank,
            )

            await self.election_member_repository.update(election_member)
            return UpdateElectionMemberOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update election member: {e}")
            return UpdateElectionMemberOutputDto(success=False, error_message=str(e))

    async def delete_election_member(
        self, input_dto: DeleteElectionMemberInputDto
    ) -> DeleteElectionMemberOutputDto:
        """選挙結果メンバーを削除する."""
        try:
            existing = await self.election_member_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteElectionMemberOutputDto(
                    success=False, error_message="選挙結果メンバーが見つかりません。"
                )

            result = await self.election_member_repository.delete(input_dto.id)
            if result:
                return DeleteElectionMemberOutputDto(success=True)
            else:
                return DeleteElectionMemberOutputDto(
                    success=False, error_message="削除できませんでした。"
                )
        except Exception as e:
            logger.error(f"Failed to delete election member: {e}")
            return DeleteElectionMemberOutputDto(success=False, error_message=str(e))

    def get_result_options(self) -> list[str]:
        """選挙結果の選択肢を取得する."""
        return ["当選", "落選", "次点", "繰上当選", "無投票当選"]
