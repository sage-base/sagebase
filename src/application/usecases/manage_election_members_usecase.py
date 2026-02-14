"""選挙結果メンバー管理のユースケース."""

from __future__ import annotations

from src.application.dtos.election_dto import GenerateSeedFileOutputDto
from src.application.dtos.election_member_dto import (
    CreateElectionMemberInputDto,
    CreateElectionMemberOutputDto,
    DeleteElectionMemberInputDto,
    DeleteElectionMemberOutputDto,
    ElectionMemberOutputItem,
    ListElectionMembersByElectionInputDto,
    ListElectionMembersByPoliticianInputDto,
    ListElectionMembersOutputDto,
    UpdateElectionMemberInputDto,
    UpdateElectionMemberOutputDto,
)
from src.common.logging import get_logger
from src.domain.entities import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.services.interfaces.seed_generator_service import (
    ISeedGeneratorService,
)


logger = get_logger(__name__)


class ManageElectionMembersUseCase:
    """選挙結果メンバー管理のユースケース."""

    def __init__(
        self,
        election_member_repository: ElectionMemberRepository,
        seed_generator_service: ISeedGeneratorService | None = None,
    ) -> None:
        """ユースケースを初期化する.

        Args:
            election_member_repository: 選挙結果メンバーリポジトリインスタンス
            seed_generator_service: シードファイル生成サービスインスタンス
        """
        self.election_member_repository = election_member_repository
        self.seed_generator_service = seed_generator_service

    async def list_by_election(
        self, input_dto: ListElectionMembersByElectionInputDto
    ) -> ListElectionMembersOutputDto:
        """選挙IDに属するメンバー一覧を取得する."""
        try:
            members = await self.election_member_repository.get_by_election_id(
                input_dto.election_id
            )
            return ListElectionMembersOutputDto(
                election_members=[
                    ElectionMemberOutputItem.from_entity(m) for m in members
                ]
            )
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
            return ListElectionMembersOutputDto(
                election_members=[
                    ElectionMemberOutputItem.from_entity(m) for m in members
                ]
            )
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
            if input_dto.result not in ElectionMember.VALID_RESULTS:
                return CreateElectionMemberOutputDto(
                    success=False,
                    error_message=(
                        "無効な選挙結果です。有効な値: "
                        f"{', '.join(ElectionMember.VALID_RESULTS)}"
                    ),
                )

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
            if input_dto.result not in ElectionMember.VALID_RESULTS:
                return UpdateElectionMemberOutputDto(
                    success=False,
                    error_message=(
                        "無効な選挙結果です。有効な値: "
                        f"{', '.join(ElectionMember.VALID_RESULTS)}"
                    ),
                )

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
        return list(ElectionMember.VALID_RESULTS)

    async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """選挙結果メンバーのSEEDファイルを生成する."""
        if self.seed_generator_service is None:
            return GenerateSeedFileOutputDto(
                success=False,
                error_message="シードファイル生成サービスが設定されていません",
            )

        try:
            result = (
                self.seed_generator_service.generate_and_save_election_members_seed()
            )
            return GenerateSeedFileOutputDto(
                success=True,
                seed_content=result.content,
                file_path=result.file_path,
            )
        except Exception as e:
            logger.error(f"Failed to generate election members seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
