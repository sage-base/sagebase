"""ParliamentaryGroupPresenterのテスト"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_parliamentary_groups_usecase import (
    CreateParliamentaryGroupOutputDto,
    DeleteParliamentaryGroupOutputDto,
    ExtractMembersOutputDto,
    GenerateSeedFileOutputDto,
    ManageParliamentaryGroupsUseCase,
    ParliamentaryGroupListOutputDto,
    UpdateParliamentaryGroupOutputDto,
)
from src.domain.entities import ParliamentaryGroup
from src.domain.entities.governing_body import GoverningBody
from src.domain.entities.parliamentary_group_party import ParliamentaryGroupParty
from src.domain.entities.political_party import PoliticalParty


@pytest.fixture
def mock_use_case():
    """ManageParliamentaryGroupsUseCaseのモック"""
    return AsyncMock(spec=ManageParliamentaryGroupsUseCase)


@pytest.fixture
def sample_parliamentary_groups():
    """サンプル議員団リスト"""
    return [
        ParliamentaryGroup(
            id=1,
            name="自民党会派",
            governing_body_id=100,
        ),
        ParliamentaryGroup(
            id=2,
            name="立憲民主党会派",
            governing_body_id=100,
        ),
    ]


@pytest.fixture
def sample_governing_bodies():
    """サンプル開催主体リスト"""
    return [
        GoverningBody(id=100, name="東京都議会"),
        GoverningBody(id=101, name="大阪府議会"),
    ]


@pytest.fixture
def presenter(mock_use_case):
    """ParliamentaryGroupPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ManageParliamentaryGroupsUseCase"
        ) as mock_uc_class,
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.GeminiLLMService"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ParliamentaryGroupMemberExtractorFactory"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.NoOpSessionAdapter"
        ),
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        mock_session_instance = MagicMock()
        mock_session_instance.get_or_create = MagicMock(
            return_value={
                "editing_mode": None,
                "editing_id": None,
                "governing_body_filter": "すべて",
                "created_parliamentary_groups": [],
            }
        )
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (  # noqa: E501
            ParliamentaryGroupPresenter,
        )

        presenter = ParliamentaryGroupPresenter()
        presenter.use_case = mock_use_case
        return presenter


class TestParliamentaryGroupPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.SessionManager"
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ManageParliamentaryGroupsUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.GeminiLLMService"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ParliamentaryGroupMemberExtractorFactory"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.NoOpSessionAdapter"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get_or_create = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (  # noqa: E501
                ParliamentaryGroupPresenter,
            )

            presenter = ParliamentaryGroupPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    async def test_load_data_async_success(
        self, presenter, mock_use_case, sample_parliamentary_groups
    ):
        """議員団リストを読み込めることを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.return_value = (
            ParliamentaryGroupListOutputDto(
                parliamentary_groups=sample_parliamentary_groups
            )
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert len(result) == 2
        mock_use_case.list_parliamentary_groups.assert_called_once()

    async def test_load_data_async_exception(self, presenter, mock_use_case):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert result == []


class TestLoadParliamentaryGroupsWithFilters:
    """load_parliamentary_groups_with_filtersメソッドのテスト"""

    async def test_with_governing_body_filter(
        self, presenter, mock_use_case, sample_parliamentary_groups
    ):
        """開催主体フィルタで絞り込めることを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.return_value = (
            ParliamentaryGroupListOutputDto(
                parliamentary_groups=sample_parliamentary_groups
            )
        )

        # Act
        result = await presenter._load_parliamentary_groups_with_filters_async(
            governing_body_id=100
        )

        # Assert
        assert len(result) == 2

    async def test_with_active_only_filter(
        self, presenter, mock_use_case, sample_parliamentary_groups
    ):
        """アクティブのみフィルタで絞り込めることを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.return_value = (
            ParliamentaryGroupListOutputDto(
                parliamentary_groups=[sample_parliamentary_groups[0]]
            )
        )

        # Act
        result = await presenter._load_parliamentary_groups_with_filters_async(
            active_only=True
        )

        # Assert
        assert len(result) == 1


class TestGetAllGoverningBodies:
    """get_all_governing_bodiesメソッドのテスト"""

    async def test_get_all_governing_bodies_success(
        self, presenter, sample_governing_bodies
    ):
        """開催主体リストを取得できることを確認"""
        # Arrange
        presenter.governing_body_repo = MagicMock()
        presenter.governing_body_repo.get_all = AsyncMock(
            return_value=sample_governing_bodies
        )

        # Act
        result = await presenter._get_all_governing_bodies_async()

        # Assert
        assert len(result) == 2


class TestGetAllPoliticalParties:
    """get_all_political_partiesメソッドのテスト"""

    async def test_get_all_political_parties_success(self, presenter):
        """政党リストを取得できることを確認"""
        from src.domain.entities.political_party import PoliticalParty

        # Arrange
        parties = [
            PoliticalParty(id=1, name="自由民主党"),
            PoliticalParty(id=2, name="立憲民主党"),
        ]
        presenter.political_party_repo = MagicMock()
        presenter.political_party_repo.get_all = AsyncMock(return_value=parties)

        # Act
        result = await presenter._get_all_political_parties_async()

        # Assert
        assert len(result) == 2
        assert result[0].name == "自由民主党"

    async def test_get_all_political_parties_exception(self, presenter):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        presenter.political_party_repo = MagicMock()
        presenter.political_party_repo.get_all = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        result = await presenter._get_all_political_parties_async()

        # Assert
        assert result == []


class TestCreate:
    """createメソッドのテスト"""

    async def test_create_success(self, presenter, mock_use_case):
        """議員団の作成が成功することを確認"""
        # Arrange
        created_group = ParliamentaryGroup(id=1, name="新規会派", governing_body_id=100)
        mock_use_case.create_parliamentary_group.return_value = (
            CreateParliamentaryGroupOutputDto(
                success=True, parliamentary_group=created_group, error_message=None
            )
        )

        # Act
        success, group, error_message = await presenter._create_async(
            name="新規会派",
            governing_body_id=100,
            political_party_id=3,
        )

        # Assert
        assert success is True
        assert group is not None
        assert group.id == 1
        call_args = mock_use_case.create_parliamentary_group.call_args[0][0]
        assert call_args.political_party_id == 3

    async def test_create_with_dates(self, presenter, mock_use_case):
        """start_date/end_dateを指定して議員団を作成できることを確認"""
        # Arrange
        created_group = ParliamentaryGroup(
            id=2,
            name="期間付き会派",
            governing_body_id=100,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
        )
        mock_use_case.create_parliamentary_group.return_value = (
            CreateParliamentaryGroupOutputDto(
                success=True, parliamentary_group=created_group, error_message=None
            )
        )

        # Act
        success, group, error_message = await presenter._create_async(
            name="期間付き会派",
            governing_body_id=100,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
        )

        # Assert
        assert success is True
        assert group is not None
        call_args = mock_use_case.create_parliamentary_group.call_args[0][0]
        assert call_args.start_date == date(2024, 1, 1)
        assert call_args.end_date == date(2025, 12, 31)

    async def test_create_with_invalid_date_range(self, presenter, mock_use_case):
        """end_date < start_dateの場合にエラーが返ることを確認"""
        # Arrange
        mock_use_case.create_parliamentary_group.side_effect = ValueError(
            "end_date (2023-12-31) は start_date (2024-01-01) より前にはできません"
        )

        # Act
        success, group, error_message = await presenter._create_async(
            name="不正な期間の会派",
            governing_body_id=100,
            start_date=date(2024, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Assert
        assert success is False
        assert group is None
        assert error_message is not None

    async def test_create_failure(self, presenter, mock_use_case):
        """議員団の作成が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.create_parliamentary_group.return_value = (
            CreateParliamentaryGroupOutputDto(
                success=False,
                parliamentary_group=None,
                error_message="作成に失敗しました",
            )
        )

        # Act
        success, group, error_message = await presenter._create_async(
            name="新規会派", governing_body_id=100
        )

        # Assert
        assert success is False
        assert group is None


class TestUpdate:
    """updateメソッドのテスト"""

    async def test_update_success(self, presenter, mock_use_case):
        """議員団の更新が成功することを確認"""
        # Arrange
        mock_use_case.update_parliamentary_group.return_value = (
            UpdateParliamentaryGroupOutputDto(success=True, error_message=None)
        )

        # Act
        success, error_message = await presenter._update_async(
            id=1, name="更新された会派", political_party_id=7
        )

        # Assert
        assert success is True
        call_args = mock_use_case.update_parliamentary_group.call_args[0][0]
        assert call_args.political_party_id == 7

    async def test_update_with_dates(self, presenter, mock_use_case):
        """start_date/end_dateを指定して議員団を更新できることを確認"""
        # Arrange
        mock_use_case.update_parliamentary_group.return_value = (
            UpdateParliamentaryGroupOutputDto(success=True, error_message=None)
        )

        # Act
        success, error_message = await presenter._update_async(
            id=1,
            name="更新された会派",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        )

        # Assert
        assert success is True
        call_args = mock_use_case.update_parliamentary_group.call_args[0][0]
        assert call_args.start_date == date(2024, 4, 1)
        assert call_args.end_date == date(2025, 3, 31)

    async def test_update_with_invalid_date_range(self, presenter, mock_use_case):
        """end_date < start_dateの場合にエラーが返ることを確認"""
        # Arrange
        mock_use_case.update_parliamentary_group.side_effect = ValueError(
            "end_date (2023-12-31) は start_date (2024-01-01) より前にはできません"
        )

        # Act
        success, error_message = await presenter._update_async(
            id=1,
            name="不正な期間の会派",
            start_date=date(2024, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Assert
        assert success is False
        assert error_message is not None

    async def test_update_failure(self, presenter, mock_use_case):
        """議員団の更新が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.update_parliamentary_group.return_value = (
            UpdateParliamentaryGroupOutputDto(
                success=False, error_message="更新に失敗しました"
            )
        )

        # Act
        success, error_message = await presenter._update_async(id=999, name="不明")

        # Assert
        assert success is False


class TestDelete:
    """deleteメソッドのテスト"""

    async def test_delete_success(self, presenter, mock_use_case):
        """議員団の削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_parliamentary_group.return_value = (
            DeleteParliamentaryGroupOutputDto(success=True, error_message=None)
        )

        # Act
        success, error_message = await presenter._delete_async(id=1)

        # Assert
        assert success is True

    async def test_delete_failure(self, presenter, mock_use_case):
        """議員団の削除が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.delete_parliamentary_group.return_value = (
            DeleteParliamentaryGroupOutputDto(
                success=False, error_message="削除に失敗しました"
            )
        )

        # Act
        success, error_message = await presenter._delete_async(id=1)

        # Assert
        assert success is False


class TestExtractMembers:
    """extract_membersメソッドのテスト"""

    async def test_extract_members_success(self, presenter, mock_use_case):
        """メンバー抽出が成功することを確認"""
        # Arrange
        mock_use_case.extract_members.return_value = ExtractMembersOutputDto(
            success=True,
            extracted_members=[],
            error_message=None,
        )

        # Act
        success, result, error_message = await presenter._extract_members_async(
            parliamentary_group_id=1, url="https://example.com"
        )

        # Assert
        assert success is True
        assert result is not None


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト"""

    async def test_generate_seed_file_success(self, presenter, mock_use_case):
        """シードファイル生成が成功することを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=True,
            seed_content="INSERT INTO...",
            file_path="/tmp/seed.sql",
            error_message=None,
        )

        # Act
        success, seed_content, file_path = await presenter._generate_seed_file_async()

        # Assert
        assert success is True
        assert seed_content == "INSERT INTO..."


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(
        self, presenter, sample_parliamentary_groups, sample_governing_bodies
    ):
        """議員団リストをDataFrameに変換できることを確認"""
        # Arrange
        presenter.political_party_repo = MagicMock()
        presenter.political_party_repo.get_all = AsyncMock(return_value=[])
        presenter.parliamentary_group_party_repo = MagicMock()
        presenter.parliamentary_group_party_repo.get_by_parliamentary_group_ids = (
            AsyncMock(return_value=[])
        )

        # Act
        df = presenter.to_dataframe(
            sample_parliamentary_groups, sample_governing_bodies
        )

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "議員団名" in df.columns
        assert "政党" in df.columns
        assert "開始日" in df.columns
        assert "終了日" in df.columns

    def test_to_dataframe_with_party_mapping(
        self, presenter, sample_parliamentary_groups, sample_governing_bodies
    ):
        """中間テーブルにデータがある場合に政党名が正しく表示されること."""
        # Arrange
        parties = [PoliticalParty(id=10, name="自由民主党")]
        presenter.political_party_repo = MagicMock()
        presenter.political_party_repo.get_all = AsyncMock(return_value=parties)

        group_parties = [
            ParliamentaryGroupParty(
                id=1,
                parliamentary_group_id=1,
                political_party_id=10,
                is_primary=True,
            ),
        ]
        presenter.parliamentary_group_party_repo = MagicMock()
        presenter.parliamentary_group_party_repo.get_by_parliamentary_group_ids = (
            AsyncMock(return_value=group_parties)
        )

        # Act
        df = presenter.to_dataframe(
            sample_parliamentary_groups, sample_governing_bodies
        )

        # Assert
        assert isinstance(df, pd.DataFrame)
        # id=1 の会派に「自由民主党」が表示される
        row_1 = df[df["ID"] == 1].iloc[0]
        assert row_1["政党"] == "自由民主党"
        # id=2 の会派は政党なし
        row_2 = df[df["ID"] == 2].iloc[0]
        assert row_2["政党"] == "未設定"

    def test_to_dataframe_empty(self, presenter, sample_governing_bodies):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([], sample_governing_bodies)

        # Assert
        assert df is None


class TestGetPrimaryPartyId:
    """get_primary_party_idメソッドのテスト"""

    def test_returns_party_id_when_exists(self, presenter):
        """主要政党が存在する場合に正しいIDが返ること."""
        primary = ParliamentaryGroupParty(
            id=1,
            parliamentary_group_id=10,
            political_party_id=20,
            is_primary=True,
        )
        presenter.parliamentary_group_party_repo = MagicMock()
        presenter.parliamentary_group_party_repo.get_primary_party = AsyncMock(
            return_value=primary
        )

        result = presenter.get_primary_party_id(10)

        assert result == 20

    def test_returns_none_when_no_primary(self, presenter):
        """主要政党が存在しない場合にNoneが返ること."""
        presenter.parliamentary_group_party_repo = MagicMock()
        presenter.parliamentary_group_party_repo.get_primary_party = AsyncMock(
            return_value=None
        )

        result = presenter.get_primary_party_id(10)

        assert result is None


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_list(self, presenter):
        """listアクションが正しく処理されることを確認"""
        # Arrange
        presenter.load_parliamentary_groups_with_filters = MagicMock(return_value=[])

        # Act
        presenter.handle_action("list")

        # Assert
        presenter.load_parliamentary_groups_with_filters.assert_called_once()

    def test_handle_action_create_with_dates(self, presenter):
        """createアクションでstart_date/end_dateが渡されることを確認"""
        # Arrange
        presenter.create = MagicMock(return_value=(True, None, None))

        # Act
        presenter.handle_action(
            "create",
            name="テスト会派",
            governing_body_id=100,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
        )

        # Assert
        presenter.create.assert_called_once_with(
            "テスト会派",
            100,
            None,
            None,
            True,
            None,
            "",
            date(2024, 1, 1),
            date(2025, 12, 31),
        )

    def test_handle_action_update_with_dates(self, presenter):
        """updateアクションでstart_date/end_dateが渡されることを確認"""
        # Arrange
        presenter.update = MagicMock(return_value=(True, None))

        # Act
        presenter.handle_action(
            "update",
            id=1,
            name="更新会派",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        )

        # Assert
        presenter.update.assert_called_once_with(
            1,
            "更新会派",
            None,
            None,
            True,
            None,
            "",
            date(2024, 4, 1),
            date(2025, 3, 31),
        )

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")


class TestGetMembershipsByGroup:
    """get_memberships_by_groupメソッドのテスト"""

    async def test_get_memberships_by_group_success(self, presenter):
        """議員団のメンバーシップを取得できることを確認"""
        from datetime import date
        from unittest.mock import MagicMock

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )
        from src.domain.entities.politician import Politician

        # Arrange
        mock_membership = MagicMock(spec=ParliamentaryGroupMembership)
        mock_membership.id = 1
        mock_membership.politician_id = 10
        mock_membership.parliamentary_group_id = 100
        mock_membership.role = "幹事長"
        mock_membership.start_date = date(2023, 1, 1)
        mock_membership.end_date = None

        mock_politician = MagicMock(spec=Politician)
        mock_politician.name = "山田太郎"

        presenter.membership_repo = MagicMock()
        presenter.membership_repo.get_by_group = AsyncMock(
            return_value=[mock_membership]
        )
        presenter.politician_repo = MagicMock()
        presenter.politician_repo.get_by_id = AsyncMock(return_value=mock_politician)

        # Act
        result = await presenter._get_memberships_by_group_async(100)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["politician_name"] == "山田太郎"
        assert result[0]["role"] == "幹事長"
        assert result[0]["is_active"] is True

    async def test_get_memberships_by_group_politician_not_found(self, presenter):
        """政治家が見つからない場合に「不明」を返すことを確認"""
        from datetime import date
        from unittest.mock import MagicMock

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        mock_membership = MagicMock(spec=ParliamentaryGroupMembership)
        mock_membership.id = 1
        mock_membership.politician_id = 10
        mock_membership.parliamentary_group_id = 100
        mock_membership.role = None
        mock_membership.start_date = date(2023, 1, 1)
        mock_membership.end_date = date(2024, 1, 1)

        presenter.membership_repo = MagicMock()
        presenter.membership_repo.get_by_group = AsyncMock(
            return_value=[mock_membership]
        )
        presenter.politician_repo = MagicMock()
        presenter.politician_repo.get_by_id = AsyncMock(
            side_effect=Exception("Not found")
        )

        # Act
        result = await presenter._get_memberships_by_group_async(100)

        # Assert
        assert len(result) == 1
        assert result[0]["politician_name"] == "不明"
        assert result[0]["is_active"] is False

    async def test_get_memberships_by_group_exception(self, presenter):
        """リポジトリで例外発生時に空リストを返すことを確認"""
        # Arrange
        presenter.membership_repo = MagicMock()
        presenter.membership_repo.get_by_group = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Act
        result = await presenter._get_memberships_by_group_async(100)

        # Assert
        assert result == []


class TestGetMembershipsForGroups:
    """get_memberships_for_groupsメソッドのテスト"""

    async def test_get_memberships_for_groups_success(self, presenter):
        """複数の議員団のメンバーシップを取得できることを確認"""
        from datetime import date
        from unittest.mock import MagicMock

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )
        from src.domain.entities.politician import Politician

        # Arrange
        def create_mock_membership(id, group_id, politician_id):
            mock = MagicMock(spec=ParliamentaryGroupMembership)
            mock.id = id
            mock.politician_id = politician_id
            mock.parliamentary_group_id = group_id
            mock.role = None
            mock.start_date = date(2023, 1, 1)
            mock.end_date = None
            return mock

        mock_memberships_group1 = [create_mock_membership(1, 100, 10)]
        mock_memberships_group2 = [
            create_mock_membership(2, 101, 11),
            create_mock_membership(3, 101, 12),
        ]

        mock_politician = MagicMock(spec=Politician)
        mock_politician.name = "テスト政治家"

        presenter.membership_repo = MagicMock()
        presenter.membership_repo.get_by_group = AsyncMock(
            side_effect=[mock_memberships_group1, mock_memberships_group2]
        )
        presenter.politician_repo = MagicMock()
        presenter.politician_repo.get_by_id = AsyncMock(return_value=mock_politician)

        # Act
        result = await presenter._get_memberships_for_groups_async([100, 101])

        # Assert
        assert len(result) == 3

    async def test_get_memberships_for_groups_empty(self, presenter):
        """空のグループIDリストで空リストを返すことを確認"""
        # Act
        result = await presenter._get_memberships_for_groups_async([])

        # Assert
        assert result == []


class TestCreatedGroupsManagement:
    """作成した議員団の管理テスト"""

    def test_add_created_group(self, presenter):
        """作成した議員団を追加できることを確認"""
        # Arrange
        presenter._save_form_state = MagicMock()
        group = ParliamentaryGroup(
            id=1,
            name="新規会派",
            governing_body_id=100,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        )

        # Act
        presenter.add_created_group(group, "東京都議会")

        # Assert
        created = presenter.form_state["created_parliamentary_groups"]
        assert len(created) == 1
        assert created[0]["start_date"] == date(2024, 4, 1)
        assert created[0]["end_date"] == date(2025, 3, 31)
        presenter._save_form_state.assert_called_once()

    def test_remove_created_group(self, presenter):
        """作成した議員団を削除できることを確認"""
        # Arrange
        presenter.form_state["created_parliamentary_groups"] = [
            {"id": 1, "name": "会派A"},
            {"id": 2, "name": "会派B"},
        ]
        presenter._save_form_state = MagicMock()

        # Act - indexで削除する
        presenter.remove_created_group(0)

        # Assert
        assert len(presenter.form_state["created_parliamentary_groups"]) == 1
        presenter._save_form_state.assert_called_once()

    def test_get_created_groups(self, presenter):
        """作成した議員団リストを取得できることを確認"""
        # Arrange
        presenter.form_state["created_parliamentary_groups"] = [
            {"id": 1, "name": "会派A"},
            {"id": 2, "name": "会派B"},
        ]

        # Act
        result = presenter.get_created_groups()

        # Assert
        assert len(result) == 2
