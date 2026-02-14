"""ElectionMemberPresenterのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.dtos.election_dto import GenerateSeedFileOutputDto
from src.application.dtos.election_member_dto import (
    CreateElectionMemberOutputDto,
    DeleteElectionMemberOutputDto,
    ElectionMemberOutputItem,
    ListElectionMembersOutputDto,
    UpdateElectionMemberOutputDto,
)
from src.application.usecases.manage_election_members_usecase import (
    ManageElectionMembersUseCase,
)
from src.application.usecases.manage_elections_usecase import ManageElectionsUseCase
from src.domain.entities import Politician
from src.domain.repositories.politician_repository import PoliticianRepository


@pytest.fixture
def mock_use_case() -> AsyncMock:
    """ManageElectionMembersUseCaseのモック."""
    return AsyncMock(spec=ManageElectionMembersUseCase)


@pytest.fixture
def mock_politician_repo() -> AsyncMock:
    """PoliticianRepositoryのモック."""
    return AsyncMock(spec=PoliticianRepository)


@pytest.fixture
def mock_election_use_case() -> AsyncMock:
    """ManageElectionsUseCaseのモック."""
    return AsyncMock(spec=ManageElectionsUseCase)


@pytest.fixture
def sample_members() -> list[ElectionMemberOutputItem]:
    """サンプル選挙結果メンバー出力アイテムリスト."""
    return [
        ElectionMemberOutputItem(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        ),
        ElectionMemberOutputItem(
            id=2,
            election_id=10,
            politician_id=101,
            result="落選",
            votes=3000,
            rank=2,
        ),
    ]


@pytest.fixture
def sample_politicians() -> list[Politician]:
    """サンプル政治家リスト."""
    p1 = Politician(name="田中太郎", prefecture="東京都", district="千代田区", id=100)
    p2 = Politician(name="山田花子", prefecture="大阪府", district="大阪市", id=101)
    return [p1, p2]


@pytest.fixture
def mock_container(
    mock_use_case,
    mock_election_use_case,
    mock_politician_repo,
):
    """DIコンテナのモック."""
    container = MagicMock()
    container.use_cases.manage_election_members_usecase.return_value = mock_use_case
    container.use_cases.manage_elections_usecase.return_value = mock_election_use_case
    container.repositories.politician_repository.return_value = mock_politician_repo
    return container


@pytest.fixture
def presenter(mock_container):
    """ElectionMemberPresenterのインスタンス."""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.election_member_presenter.SessionManager"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.base.Container"
        ) as mock_container_cls,
    ):
        mock_container_cls.create_for_environment.return_value = mock_container

        from src.interfaces.web.streamlit.presenters.election_member_presenter import (
            ElectionMemberPresenter,
        )

        presenter = ElectionMemberPresenter()
        yield presenter


class TestElectionMemberPresenterInit:
    """初期化テスト."""

    def test_init_creates_instance(self) -> None:
        """Presenterが正しく初期化されることを確認."""
        mock_container = MagicMock()
        mock_container.use_cases.manage_election_members_usecase.return_value = (
            AsyncMock()
        )
        mock_container.use_cases.manage_elections_usecase.return_value = AsyncMock()
        mock_container.repositories.politician_repository.return_value = AsyncMock()

        with (
            patch(
                "src.interfaces.web.streamlit.presenters.election_member_presenter.SessionManager"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.base.Container"
            ) as mock_container_cls,
        ):
            mock_container_cls.create_for_environment.return_value = mock_container

            from src.interfaces.web.streamlit.presenters.election_member_presenter import (  # noqa: E501
                ElectionMemberPresenter,
            )

            presenter = ElectionMemberPresenter()
            assert presenter is not None
            assert presenter.use_case is not None


class TestLoadMembers:
    """メンバーデータ読み込みテスト."""

    def test_load_data_returns_empty(self, presenter) -> None:
        """load_dataが空リストを返すことを確認."""
        result = presenter.load_data()
        assert result == []

    def test_load_members_by_election(
        self,
        presenter,
        mock_use_case: AsyncMock,
        sample_members: list[ElectionMemberOutputItem],
    ) -> None:
        """選挙別メンバー一覧が返されることを確認."""
        mock_use_case.list_by_election.return_value = ListElectionMembersOutputDto(
            election_members=sample_members
        )

        result = presenter.load_members_by_election(10)

        assert len(result) == 2
        assert result[0].result == "当選"
        mock_use_case.list_by_election.assert_called_once()

    def test_load_members_by_election_error(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """エラー時に空リストを返すことを確認."""
        mock_use_case.list_by_election.side_effect = Exception("DB Error")

        result = presenter.load_members_by_election(10)

        assert result == []

    def test_load_politicians(
        self,
        presenter,
        mock_politician_repo: AsyncMock,
        sample_politicians: list[Politician],
    ) -> None:
        """政治家一覧が返されることを確認."""
        mock_politician_repo.get_all.return_value = sample_politicians

        result = presenter.load_politicians()

        assert len(result) == 2
        mock_politician_repo.get_all.assert_called_once()

    def test_load_politicians_error(
        self,
        presenter,
        mock_politician_repo: AsyncMock,
    ) -> None:
        """政治家読み込みエラー時に空リストを返すことを確認."""
        mock_politician_repo.get_all.side_effect = Exception("DB Error")

        result = presenter.load_politicians()

        assert result == []


class TestCreateElectionMember:
    """メンバー作成テスト."""

    def test_create_success(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """メンバー作成が成功することを確認."""
        mock_use_case.create_election_member.return_value = (
            CreateElectionMemberOutputDto(success=True, election_member_id=1)
        )

        success, error = presenter.create(
            election_id=10,
            politician_id=100,
            result="当選",
            votes=5000,
            rank=1,
        )

        assert success is True
        assert error is None
        mock_use_case.create_election_member.assert_called_once()

    def test_create_failure(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """メンバー作成が失敗した場合にエラーメッセージを返すことを確認."""
        mock_use_case.create_election_member.return_value = (
            CreateElectionMemberOutputDto(
                success=False,
                error_message="同じ選挙に同じ政治家が既に登録されています。",
            )
        )

        success, error = presenter.create(
            election_id=10,
            politician_id=100,
            result="当選",
        )

        assert success is False
        assert error == "同じ選挙に同じ政治家が既に登録されています。"

    def test_create_exception(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """例外発生時にエラーメッセージを返すことを確認."""
        mock_use_case.create_election_member.side_effect = Exception("DB Error")

        success, error = presenter.create(
            election_id=10,
            politician_id=100,
            result="当選",
        )

        assert success is False
        assert error is not None


class TestUpdateElectionMember:
    """メンバー更新テスト."""

    def test_update_success(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """メンバー更新が成功することを確認."""
        mock_use_case.update_election_member.return_value = (
            UpdateElectionMemberOutputDto(success=True)
        )

        success, error = presenter.update(
            id=1,
            election_id=10,
            politician_id=100,
            result="繰上当選",
            votes=5000,
            rank=1,
        )

        assert success is True
        assert error is None
        mock_use_case.update_election_member.assert_called_once()

    def test_update_failure(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """メンバー更新が失敗した場合にエラーメッセージを返すことを確認."""
        mock_use_case.update_election_member.return_value = (
            UpdateElectionMemberOutputDto(
                success=False, error_message="メンバーが見つかりません。"
            )
        )

        success, error = presenter.update(
            id=999,
            election_id=10,
            politician_id=100,
            result="当選",
        )

        assert success is False
        assert error == "メンバーが見つかりません。"

    def test_update_exception(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """例外発生時にエラーメッセージを返すことを確認."""
        mock_use_case.update_election_member.side_effect = Exception("DB Error")

        success, error = presenter.update(
            id=1,
            election_id=10,
            politician_id=100,
            result="当選",
        )

        assert success is False
        assert error is not None


class TestDeleteElectionMember:
    """メンバー削除テスト."""

    def test_delete_success(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """メンバー削除が成功することを確認."""
        mock_use_case.delete_election_member.return_value = (
            DeleteElectionMemberOutputDto(success=True)
        )

        success, error = presenter.delete(id=1)

        assert success is True
        assert error is None
        mock_use_case.delete_election_member.assert_called_once()

    def test_delete_failure(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """メンバー削除が失敗した場合にエラーメッセージを返すことを確認."""
        mock_use_case.delete_election_member.return_value = (
            DeleteElectionMemberOutputDto(
                success=False, error_message="削除に失敗しました。"
            )
        )

        success, error = presenter.delete(id=1)

        assert success is False
        assert error == "削除に失敗しました。"

    def test_delete_exception(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """例外発生時にエラーメッセージを返すことを確認."""
        mock_use_case.delete_election_member.side_effect = Exception("DB Error")

        success, error = presenter.delete(id=1)

        assert success is False
        assert error is not None


class TestToDataframe:
    """DataFrame変換テスト."""

    def test_to_dataframe_returns_dataframe(
        self,
        presenter,
        sample_members: list[ElectionMemberOutputItem],
    ) -> None:
        """メンバーリストからDataFrameを作成できることを確認."""
        politician_map = {100: "田中太郎", 101: "山田花子"}
        df = presenter.to_dataframe(sample_members, politician_map)

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "政治家" in df.columns
        assert "結果" in df.columns
        assert "得票数" in df.columns
        assert "順位" in df.columns
        assert df.iloc[0]["政治家"] == "田中太郎"

    def test_to_dataframe_returns_none_for_empty_list(
        self,
        presenter,
    ) -> None:
        """空リストの場合はNoneを返すことを確認."""
        df = presenter.to_dataframe([], {})
        assert df is None

    def test_to_dataframe_with_none_values(
        self,
        presenter,
    ) -> None:
        """votes/rankがNoneの場合に空文字で表示されることを確認."""
        members = [
            ElectionMemberOutputItem(
                id=1,
                election_id=10,
                politician_id=100,
                result="無投票当選",
                votes=None,
                rank=None,
            ),
        ]
        df = presenter.to_dataframe(members, {100: "田中太郎"})

        assert df is not None
        assert df.iloc[0]["得票数"] == ""
        assert df.iloc[0]["順位"] == ""

    def test_to_dataframe_unknown_politician(
        self,
        presenter,
        sample_members: list[ElectionMemberOutputItem],
    ) -> None:
        """政治家マップにない場合はID表示になることを確認."""
        df = presenter.to_dataframe(sample_members, {})

        assert df is not None
        assert df.iloc[0]["政治家"] == "ID:100"


class TestHandleAction:
    """アクション処理テスト."""

    def test_handle_action_list_by_election(
        self,
        presenter,
        mock_use_case: AsyncMock,
        sample_members: list[ElectionMemberOutputItem],
    ) -> None:
        """list_by_electionアクションが正しく処理されることを確認."""
        mock_use_case.list_by_election.return_value = ListElectionMembersOutputDto(
            election_members=sample_members
        )

        result = presenter.handle_action("list_by_election", election_id=10)

        assert len(result) == 2

    def test_handle_action_list_by_election_none_id(
        self,
        presenter,
    ) -> None:
        """election_idがNoneの場合に空リストを返すことを確認."""
        result = presenter.handle_action("list_by_election")

        assert result == []

    def test_handle_action_create(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """createアクションが正しく処理されることを確認."""
        mock_use_case.create_election_member.return_value = (
            CreateElectionMemberOutputDto(success=True, election_member_id=1)
        )

        success, error = presenter.handle_action(
            "create",
            election_id=10,
            politician_id=100,
            result="当選",
        )

        assert success is True

    def test_handle_action_create_missing_params(
        self,
        presenter,
    ) -> None:
        """必須パラメータ不足でエラーを返すことを確認."""
        success, error = presenter.handle_action("create", election_id=10)

        assert success is False
        assert "必須パラメータが不足しています" in error

    def test_handle_action_update(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """updateアクションが正しく処理されることを確認."""
        mock_use_case.update_election_member.return_value = (
            UpdateElectionMemberOutputDto(success=True)
        )

        success, error = presenter.handle_action(
            "update",
            id=1,
            election_id=10,
            politician_id=100,
            result="繰上当選",
        )

        assert success is True

    def test_handle_action_update_missing_params(
        self,
        presenter,
    ) -> None:
        """update必須パラメータ不足でエラーを返すことを確認."""
        success, error = presenter.handle_action("update", id=1)

        assert success is False
        assert "必須パラメータが不足しています" in error

    def test_handle_action_delete(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """deleteアクションが正しく処理されることを確認."""
        mock_use_case.delete_election_member.return_value = (
            DeleteElectionMemberOutputDto(success=True)
        )

        success, error = presenter.handle_action("delete", id=1)

        assert success is True

    def test_handle_action_delete_no_id(
        self,
        presenter,
    ) -> None:
        """IDなしのdeleteでエラーを返すことを確認."""
        success, error = presenter.handle_action("delete")

        assert success is False

    def test_handle_action_unknown_raises_error(
        self,
        presenter,
    ) -> None:
        """不明なアクションでValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown_action")


class TestGetResultOptions:
    """結果オプション取得テスト."""

    def test_get_result_options(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """結果オプションが返されることを確認."""
        mock_use_case.get_result_options.return_value = [
            "当選",
            "落選",
            "次点",
            "繰上当選",
            "無投票当選",
        ]

        options = presenter.get_result_options()

        assert len(options) == 5
        assert "当選" in options
        assert "繰上当選" in options


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト."""

    def test_generate_seed_file_success(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """SEEDファイル生成が成功することを確認."""
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=True,
            seed_content="INSERT INTO election_members ...",
            file_path="database/seed_election_members_generated.sql",
        )

        success, seed_content, file_path = presenter.generate_seed_file()

        assert success is True
        assert seed_content == "INSERT INTO election_members ..."
        assert file_path == "database/seed_election_members_generated.sql"
        mock_use_case.generate_seed_file.assert_called_once()

    def test_generate_seed_file_failure(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """SEEDファイル生成が失敗した場合にエラーを返すことを確認."""
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=False,
            error_message="シードファイル生成サービスが設定されていません",
        )

        success, seed_content, error_msg = presenter.generate_seed_file()

        assert success is False
        assert seed_content is None
        assert "設定されていません" in (error_msg or "")

    def test_generate_seed_file_exception(
        self,
        presenter,
        mock_use_case: AsyncMock,
    ) -> None:
        """例外発生時にエラーメッセージを返すことを確認."""
        mock_use_case.generate_seed_file.side_effect = Exception("Unexpected error")

        success, seed_content, error_msg = presenter.generate_seed_file()

        assert success is False
        assert seed_content is None
        assert error_msg is not None
