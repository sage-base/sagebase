"""ElectionPresenterのテスト."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_elections_usecase import (
    CreateElectionOutputDto,
    DeleteElectionOutputDto,
    ListElectionsOutputDto,
    ManageElectionsUseCase,
    UpdateElectionOutputDto,
)
from src.domain.entities import Election


@pytest.fixture
def mock_use_case() -> AsyncMock:
    """ManageElectionsUseCaseのモック."""
    return AsyncMock(spec=ManageElectionsUseCase)


@pytest.fixture
def sample_elections() -> list[Election]:
    """サンプル選挙リスト."""
    return [
        Election(
            id=1,
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type="統一地方選挙",
        ),
        Election(
            id=2,
            governing_body_id=88,
            term_number=20,
            election_date=date(2019, 4, 7),
            election_type="統一地方選挙",
        ),
    ]


@pytest.fixture
def presenter(mock_use_case: AsyncMock) -> MagicMock:
    """ElectionPresenterのインスタンス."""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.election_presenter.RepositoryAdapter"  # noqa: E501
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.election_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.election_presenter.ManageElectionsUseCase"  # noqa: E501
        ) as mock_uc_class,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        mock_session_instance = MagicMock()
        mock_session_instance.get_or_create = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.election_presenter import (
            ElectionPresenter,
        )

        presenter = ElectionPresenter()
        presenter.use_case = mock_use_case
        return presenter


class TestElectionPresenterInit:
    """初期化テスト."""

    def test_init_creates_instance(self) -> None:
        """Presenterが正しく初期化されることを確認."""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.election_presenter.RepositoryAdapter"  # noqa: E501
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.election_presenter.SessionManager"  # noqa: E501
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.election_presenter.ManageElectionsUseCase"  # noqa: E501
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get_or_create = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.election_presenter import (
                ElectionPresenter,
            )

            presenter = ElectionPresenter()
            assert presenter is not None
            assert presenter.use_case is not None


class TestLoadElections:
    """選挙データ読み込みテスト."""

    def test_load_data_returns_elections(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
        sample_elections: list[Election],
    ) -> None:
        """load_dataが選挙リストを返すことを確認."""
        mock_use_case.list_all_elections.return_value = ListElectionsOutputDto(
            elections=sample_elections
        )

        result = presenter.load_data()

        assert len(result) == 2
        assert result[0].term_number == 21
        mock_use_case.list_all_elections.assert_called_once()

    def test_load_data_returns_empty_on_error(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """エラー時に空リストを返すことを確認."""
        mock_use_case.list_all_elections.side_effect = Exception("DB Error")

        result = presenter.load_data()

        assert result == []

    def test_load_elections_by_governing_body(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
        sample_elections: list[Election],
    ) -> None:
        """特定の開催主体の選挙を読み込めることを確認."""
        mock_use_case.list_elections.return_value = ListElectionsOutputDto(
            elections=sample_elections
        )

        result = presenter.load_elections_by_governing_body(88)

        assert len(result) == 2
        mock_use_case.list_elections.assert_called_once()


class TestCreateElection:
    """選挙作成テスト."""

    def test_create_success(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙作成が成功することを確認."""
        mock_use_case.create_election.return_value = CreateElectionOutputDto(
            success=True, election_id=1
        )

        success, id_or_error = presenter.create(
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type="統一地方選挙",
        )

        assert success is True
        assert id_or_error == "1"
        mock_use_case.create_election.assert_called_once()

    def test_create_failure(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙作成が失敗した場合にエラーメッセージを返すことを確認."""
        mock_use_case.create_election.return_value = CreateElectionOutputDto(
            success=False, error_message="同じ期番号の選挙が既に存在します。"
        )

        success, error = presenter.create(
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
        )

        assert success is False
        assert error == "同じ期番号の選挙が既に存在します。"


class TestUpdateElection:
    """選挙更新テスト."""

    def test_update_success(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙更新が成功することを確認."""
        mock_use_case.update_election.return_value = UpdateElectionOutputDto(
            success=True
        )

        success, error = presenter.update(
            id=1,
            governing_body_id=88,
            term_number=22,
            election_date=date(2027, 4, 11),
            election_type="統一地方選挙",
        )

        assert success is True
        assert error is None
        mock_use_case.update_election.assert_called_once()

    def test_update_failure(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙更新が失敗した場合にエラーメッセージを返すことを確認."""
        mock_use_case.update_election.return_value = UpdateElectionOutputDto(
            success=False, error_message="選挙が見つかりません。"
        )

        success, error = presenter.update(
            id=999,
            governing_body_id=88,
            term_number=22,
            election_date=date(2027, 4, 11),
        )

        assert success is False
        assert error == "選挙が見つかりません。"


class TestDeleteElection:
    """選挙削除テスト."""

    def test_delete_success(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙削除が成功することを確認."""
        mock_use_case.delete_election.return_value = DeleteElectionOutputDto(
            success=True
        )

        success, error = presenter.delete(id=1)

        assert success is True
        assert error is None
        mock_use_case.delete_election.assert_called_once()

    def test_delete_failure(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙削除が失敗した場合にエラーメッセージを返すことを確認."""
        mock_use_case.delete_election.return_value = DeleteElectionOutputDto(
            success=False, error_message="関連する会議体が存在します。"
        )

        success, error = presenter.delete(id=1)

        assert success is False
        assert error == "関連する会議体が存在します。"


class TestToDataframe:
    """DataFrame変換テスト."""

    def test_to_dataframe_returns_dataframe(
        self,
        presenter: MagicMock,
        sample_elections: list[Election],
    ) -> None:
        """選挙リストからDataFrameを作成できることを確認."""
        df = presenter.to_dataframe(sample_elections)

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "期番号" in df.columns
        assert "選挙日" in df.columns
        assert "選挙種別" in df.columns

    def test_to_dataframe_returns_none_for_empty_list(
        self,
        presenter: MagicMock,
    ) -> None:
        """空リストの場合はNoneを返すことを確認."""
        df = presenter.to_dataframe([])

        assert df is None


class TestHandleAction:
    """アクション処理テスト."""

    def test_handle_action_list(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
        sample_elections: list[Election],
    ) -> None:
        """listアクションが正しく処理されることを確認."""
        mock_use_case.list_all_elections.return_value = ListElectionsOutputDto(
            elections=sample_elections
        )

        result = presenter.handle_action("list")

        assert len(result) == 2

    def test_handle_action_list_by_governing_body(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
        sample_elections: list[Election],
    ) -> None:
        """list_by_governing_bodyアクションが正しく処理されることを確認."""
        mock_use_case.list_elections.return_value = ListElectionsOutputDto(
            elections=sample_elections
        )

        result = presenter.handle_action("list_by_governing_body", governing_body_id=88)

        assert len(result) == 2

    def test_handle_action_list_by_governing_body_invalid_id(
        self,
        presenter: MagicMock,
    ) -> None:
        """無効なgoverning_body_idの場合に空リストを返すことを確認."""
        result = presenter.handle_action("list_by_governing_body", governing_body_id=0)

        assert result == []

    def test_handle_action_unknown_raises_error(
        self,
        presenter: MagicMock,
    ) -> None:
        """不明なアクションでValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown_action")


class TestGetElectionTypeOptions:
    """選挙種別オプション取得テスト."""

    def test_get_election_type_options(
        self,
        presenter: MagicMock,
        mock_use_case: AsyncMock,
    ) -> None:
        """選挙種別オプションが返されることを確認."""
        mock_use_case.get_election_type_options.return_value = [
            "統一地方選挙",
            "通常選挙",
            "補欠選挙",
            "再選挙",
            "その他",
        ]

        options = presenter.get_election_type_options()

        assert len(options) == 5
        assert "統一地方選挙" in options


class TestSessionManagement:
    """セッション管理テスト."""

    def test_set_selected_governing_body(
        self,
        presenter: MagicMock,
    ) -> None:
        """選択された開催主体を設定できることを確認."""
        presenter.set_selected_governing_body(88)

        assert presenter.form_state["selected_governing_body_id"] == 88

    def test_get_selected_governing_body(
        self,
        presenter: MagicMock,
    ) -> None:
        """選択された開催主体を取得できることを確認."""
        presenter.form_state["selected_governing_body_id"] = 88

        result = presenter.get_selected_governing_body()

        assert result == 88

    def test_get_selected_governing_body_returns_none_when_not_set(
        self,
        presenter: MagicMock,
    ) -> None:
        """未設定の場合はNoneを返すことを確認."""
        result = presenter.get_selected_governing_body()

        assert result is None
