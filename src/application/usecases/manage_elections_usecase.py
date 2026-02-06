"""選挙管理のユースケース."""

from src.application.dtos.election_dto import (
    CreateElectionInputDto,
    CreateElectionOutputDto,
    DeleteElectionInputDto,
    DeleteElectionOutputDto,
    ElectionOutputItem,
    GenerateSeedFileOutputDto,
    ListElectionsInputDto,
    ListElectionsOutputDto,
    UpdateElectionInputDto,
    UpdateElectionOutputDto,
)
from src.common.logging import get_logger
from src.domain.entities import Election
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.services.interfaces.seed_generator_service import (
    ISeedGeneratorService,
)


logger = get_logger(__name__)


class ManageElectionsUseCase:
    """選挙管理のユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        seed_generator_service: ISeedGeneratorService | None = None,
    ) -> None:
        """ユースケースを初期化する.

        Args:
            election_repository: 選挙リポジトリインスタンス
            seed_generator_service: シードファイル生成サービスインスタンス
        """
        self.election_repository = election_repository
        self.seed_generator_service = seed_generator_service

    async def list_elections(
        self, input_dto: ListElectionsInputDto
    ) -> ListElectionsOutputDto:
        """開催主体に属する選挙一覧を取得する."""
        try:
            elections = await self.election_repository.get_by_governing_body(
                input_dto.governing_body_id
            )
            return ListElectionsOutputDto(
                elections=[ElectionOutputItem.from_entity(e) for e in elections]
            )
        except Exception as e:
            logger.error(f"Failed to list elections: {e}")
            return ListElectionsOutputDto(
                elections=[], success=False, error_message=str(e)
            )

    async def list_all_elections(self) -> ListElectionsOutputDto:
        """全選挙一覧を取得する."""
        try:
            elections = await self.election_repository.get_all()
            return ListElectionsOutputDto(
                elections=[ElectionOutputItem.from_entity(e) for e in elections]
            )
        except Exception as e:
            logger.error(f"Failed to list all elections: {e}")
            return ListElectionsOutputDto(
                elections=[], success=False, error_message=str(e)
            )

    async def create_election(
        self, input_dto: CreateElectionInputDto
    ) -> CreateElectionOutputDto:
        """選挙を作成する."""
        try:
            # 重複チェック（同じ開催主体・期番号の組み合わせ）
            existing = await self.election_repository.get_by_governing_body_and_term(
                input_dto.governing_body_id, input_dto.term_number
            )
            if existing:
                return CreateElectionOutputDto(
                    success=False,
                    error_message="同じ開催主体と期番号の選挙が既に存在します。",
                )

            # 期番号のバリデーション
            if input_dto.term_number < 1:
                return CreateElectionOutputDto(
                    success=False,
                    error_message="期番号は1以上である必要があります。",
                )

            # 選挙エンティティを作成
            election = Election(
                governing_body_id=input_dto.governing_body_id,
                term_number=input_dto.term_number,
                election_date=input_dto.election_date,
                election_type=input_dto.election_type,
            )

            created = await self.election_repository.create(election)
            return CreateElectionOutputDto(success=True, election_id=created.id)
        except Exception as e:
            logger.error(f"Failed to create election: {e}")
            return CreateElectionOutputDto(success=False, error_message=str(e))

    async def update_election(
        self, input_dto: UpdateElectionInputDto
    ) -> UpdateElectionOutputDto:
        """選挙を更新する."""
        try:
            # 存在確認
            existing = await self.election_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateElectionOutputDto(
                    success=False, error_message="選挙が見つかりません。"
                )

            # 重複チェック（自身を除く）
            duplicate = await self.election_repository.get_by_governing_body_and_term(
                input_dto.governing_body_id, input_dto.term_number
            )
            if duplicate and duplicate.id != input_dto.id:
                return UpdateElectionOutputDto(
                    success=False,
                    error_message="同じ開催主体と期番号の選挙が既に存在します。",
                )

            # 期番号のバリデーション
            if input_dto.term_number < 1:
                return UpdateElectionOutputDto(
                    success=False,
                    error_message="期番号は1以上である必要があります。",
                )

            # 更新
            election = Election(
                id=input_dto.id,
                governing_body_id=input_dto.governing_body_id,
                term_number=input_dto.term_number,
                election_date=input_dto.election_date,
                election_type=input_dto.election_type,
            )

            await self.election_repository.update(election)
            return UpdateElectionOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update election: {e}")
            return UpdateElectionOutputDto(success=False, error_message=str(e))

    async def delete_election(
        self, input_dto: DeleteElectionInputDto
    ) -> DeleteElectionOutputDto:
        """選挙を削除する."""
        try:
            # 存在確認
            existing = await self.election_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteElectionOutputDto(
                    success=False, error_message="選挙が見つかりません。"
                )

            result = await self.election_repository.delete(input_dto.id)
            if result:
                return DeleteElectionOutputDto(success=True)
            else:
                return DeleteElectionOutputDto(
                    success=False,
                    error_message="削除できませんでした（関連する会議体が存在する可能性があります）。",
                )
        except Exception as e:
            logger.error(f"Failed to delete election: {e}")
            return DeleteElectionOutputDto(success=False, error_message=str(e))

    def get_election_type_options(self) -> list[str]:
        """選挙種別の選択肢を取得する."""
        return ["統一地方選挙", "通常選挙", "補欠選挙", "再選挙", "その他"]

    async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """選挙のSEEDファイルを生成する."""
        if self.seed_generator_service is None:
            return GenerateSeedFileOutputDto(
                success=False,
                error_message="シードファイル生成サービスが設定されていません",
            )

        try:
            result = self.seed_generator_service.generate_and_save_elections_seed()

            return GenerateSeedFileOutputDto(
                success=True,
                seed_content=result.content,
                file_path=result.file_path,
            )
        except Exception as e:
            logger.error(f"Failed to generate seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
