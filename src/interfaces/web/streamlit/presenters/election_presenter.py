"""選挙管理のプレゼンター."""

from datetime import date
from typing import Any

import pandas as pd

from src.application.dtos.election_dto import (
    CreateElectionInputDto,
    DeleteElectionInputDto,
    ElectionOutputItem,
    GenerateSeedFileOutputDto,
    ListElectionsInputDto,
    UpdateElectionInputDto,
)
from src.application.usecases.manage_elections_usecase import ManageElectionsUseCase
from src.common.logging import get_logger
from src.domain.entities.governing_body import GoverningBody
from src.infrastructure.di.container import Container
from src.infrastructure.external.seed_generator_service import (
    SeedGeneratorServiceImpl,
)
from src.infrastructure.persistence.election_repository_impl import (
    ElectionRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ElectionPresenter(BasePresenter[list[ElectionOutputItem]]):
    """選挙管理のプレゼンター."""

    def __init__(self, container: Container | None = None):
        """プレゼンターを初期化する."""
        super().__init__(container)
        # リポジトリとユースケースを初期化
        self.election_repo = RepositoryAdapter(ElectionRepositoryImpl)
        self.governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
        # Type: ignore - RepositoryAdapter duck-types as repository protocol
        self.seed_generator_service = SeedGeneratorServiceImpl()
        self.use_case = ManageElectionsUseCase(
            self.election_repo,  # type: ignore[arg-type]
            seed_generator_service=self.seed_generator_service,
        )
        self.session = SessionManager()
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(__name__)

    def _get_or_create_form_state(self) -> dict[str, Any]:
        """セッションからフォーム状態を取得または作成する."""
        default_state = {
            "editing_mode": None,
            "editing_id": None,
            "selected_governing_body_id": None,
        }
        return self.session.get_or_create("election_form_state", default_state)

    def _save_form_state(self) -> None:
        """フォーム状態をセッションに保存する."""
        self.session.set("election_form_state", self.form_state)

    def load_data(self) -> list[ElectionOutputItem]:
        """全選挙を読み込む."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[ElectionOutputItem]:
        """全選挙を読み込む（非同期実装）."""
        try:
            result = await self.use_case.list_all_elections()
            return result.elections
        except Exception as e:
            self.logger.error(f"Failed to load elections: {e}")
            return []

    def load_elections_by_governing_body(
        self, governing_body_id: int
    ) -> list[ElectionOutputItem]:
        """特定の開催主体に属する選挙を読み込む."""
        return self._run_async(
            self._load_elections_by_governing_body_async(governing_body_id)
        )

    async def _load_elections_by_governing_body_async(
        self, governing_body_id: int
    ) -> list[ElectionOutputItem]:
        """特定の開催主体に属する選挙を読み込む（非同期実装）."""
        try:
            result = await self.use_case.list_elections(
                ListElectionsInputDto(governing_body_id=governing_body_id)
            )
            return result.elections
        except Exception as e:
            self.logger.exception(
                f"Failed to load elections for governing body {governing_body_id}: {e}"
            )
            return []

    def load_governing_bodies(self) -> list[GoverningBody]:
        """全開催主体を読み込む."""
        return self._run_async(self._load_governing_bodies_async())

    async def _load_governing_bodies_async(self) -> list[GoverningBody]:
        """全開催主体を読み込む（非同期実装）."""
        try:
            return await self.governing_body_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to load governing bodies: {e}")
            return []

    def get_election_type_options(self) -> list[str]:
        """選挙種別の選択肢を取得する."""
        return self.use_case.get_election_type_options()

    def create(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """選挙を作成する."""
        return self._run_async(
            self._create_async(
                governing_body_id, term_number, election_date, election_type
            )
        )

    async def _create_async(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """選挙を作成する（非同期実装）."""
        try:
            result = await self.use_case.create_election(
                CreateElectionInputDto(
                    governing_body_id=governing_body_id,
                    term_number=term_number,
                    election_date=election_date,
                    election_type=election_type,
                )
            )
            if result.success:
                return True, str(result.election_id)
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to create election: {e}"
            self.logger.exception(error_msg)
            return False, error_msg

    def update(
        self,
        id: int,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """選挙を更新する."""
        return self._run_async(
            self._update_async(
                id, governing_body_id, term_number, election_date, election_type
            )
        )

    async def _update_async(
        self,
        id: int,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """選挙を更新する（非同期実装）."""
        try:
            result = await self.use_case.update_election(
                UpdateElectionInputDto(
                    id=id,
                    governing_body_id=governing_body_id,
                    term_number=term_number,
                    election_date=election_date,
                    election_type=election_type,
                )
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to update election: {e}"
            self.logger.exception(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """選挙を削除する."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        """選挙を削除する（非同期実装）."""
        try:
            result = await self.use_case.delete_election(DeleteElectionInputDto(id=id))
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to delete election: {e}"
            self.logger.exception(error_msg)
            return False, error_msg

    def to_dataframe(self, elections: list[ElectionOutputItem]) -> pd.DataFrame | None:
        """選挙リストをDataFrameに変換する."""
        if not elections:
            return None

        df_data = []
        for election in elections:
            df_data.append(
                {
                    "ID": election.id,
                    "期番号": f"第{election.term_number}期",
                    "選挙日": election.election_date,
                    "選挙種別": election.election_type or "",
                }
            )
        return pd.DataFrame(df_data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """ユーザーアクションを処理する."""
        if action == "list":
            return self.load_data()
        elif action == "list_by_governing_body":
            governing_body_id = kwargs.get("governing_body_id")
            if governing_body_id is None or governing_body_id == 0:
                self.logger.warning(
                    "Invalid governing_body_id for list_by_governing_body"
                )
                return []
            return self.load_elections_by_governing_body(governing_body_id)
        elif action == "create":
            governing_body_id = kwargs.get("governing_body_id")
            term_number = kwargs.get("term_number")
            election_date = kwargs.get("election_date")
            if not all([governing_body_id, term_number, election_date]):
                return False, "必須パラメータが不足しています"
            # Type assertion after validation
            assert isinstance(governing_body_id, int)
            assert isinstance(term_number, int)
            return self.create(
                governing_body_id,
                term_number,
                election_date,  # type: ignore[arg-type]
                kwargs.get("election_type"),
            )
        elif action == "update":
            id = kwargs.get("id")
            governing_body_id = kwargs.get("governing_body_id")
            term_number = kwargs.get("term_number")
            election_date = kwargs.get("election_date")
            if not all([id, governing_body_id, term_number, election_date]):
                return False, "必須パラメータが不足しています"
            # Type assertion after validation
            assert isinstance(id, int)
            assert isinstance(governing_body_id, int)
            assert isinstance(term_number, int)
            return self.update(
                id,
                governing_body_id,
                term_number,
                election_date,  # type: ignore[arg-type]
                kwargs.get("election_type"),
            )
        elif action == "delete":
            id = kwargs.get("id")
            if not id:
                return False, "IDが指定されていません"
            return self.delete(id)
        else:
            raise ValueError(f"Unknown action: {action}")

    def set_selected_governing_body(self, governing_body_id: int | None) -> None:
        """選択された開催主体を設定する."""
        self.form_state["selected_governing_body_id"] = governing_body_id
        self._save_form_state()

    def get_selected_governing_body(self) -> int | None:
        """選択された開催主体を取得する."""
        return self.form_state.get("selected_governing_body_id")

    def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """選挙のSEEDファイルを生成する."""
        return self._run_async(self._generate_seed_file_async())

    async def _generate_seed_file_async(self) -> tuple[bool, str | None, str | None]:
        """選挙のSEEDファイルを生成する（非同期実装）."""
        try:
            result: GenerateSeedFileOutputDto = await self.use_case.generate_seed_file()
            if result.success:
                return True, result.seed_content, result.file_path
            return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to generate seed file: {e}"
            self.logger.exception(error_msg)
            return False, None, error_msg
