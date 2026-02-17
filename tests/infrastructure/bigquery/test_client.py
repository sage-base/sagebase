"""BigQueryクライアントのテスト."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.bigquery.schema import BQColumnDef, BQTableDef
from src.infrastructure.exceptions import StorageError


@pytest.fixture
def mock_bq_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sample_table_def() -> BQTableDef:
    return BQTableDef(
        table_id="test_table",
        description="テストテーブル",
        columns=(
            BQColumnDef("id", "INT64", "REQUIRED", "ID"),
            BQColumnDef("name", "STRING", description="名前"),
            BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        ),
    )


class TestBigQueryClientInit:
    """BigQueryClient初期化テスト."""

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_init_success(self, mock_bigquery: MagicMock) -> None:
        from src.infrastructure.bigquery.client import BigQueryClient

        client = BigQueryClient(
            project_id="test-project",
            dataset_id="test_dataset",
            location="asia-northeast1",
        )
        assert client.project_id == "test-project"
        assert client.dataset_id == "test_dataset"
        assert client.location == "asia-northeast1"
        mock_bigquery.Client.assert_called_once_with(
            project="test-project", location="asia-northeast1"
        )

    @patch("src.infrastructure.bigquery.client.HAS_BIGQUERY", False)
    def test_init_raises_when_library_not_installed(self) -> None:
        from src.infrastructure.bigquery.client import BigQueryClient

        with pytest.raises(StorageError, match="not installed"):
            BigQueryClient(project_id="test-project")

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_init_raises_on_auth_error(self, mock_bigquery: MagicMock) -> None:
        from google.auth.exceptions import RefreshError

        from src.infrastructure.bigquery.client import BigQueryClient

        mock_bigquery.Client.side_effect = RefreshError("token expired")

        from src.infrastructure.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            BigQueryClient(project_id="test-project")


class TestEnsureDataset:
    """ensure_dataset テスト."""

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_ensure_dataset_success(self, mock_bigquery: MagicMock) -> None:
        from src.infrastructure.bigquery.client import BigQueryClient

        mock_dataset = MagicMock()
        mock_bigquery.Dataset.return_value = mock_dataset

        client = BigQueryClient(project_id="test-project")
        client.ensure_dataset()

        mock_bigquery.Dataset.assert_called_with("test-project.sagebase_gold")
        client.client.create_dataset.assert_called_once_with(
            mock_dataset, exists_ok=True
        )

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_ensure_dataset_permission_error(self, mock_bigquery: MagicMock) -> None:
        from google.api_core.exceptions import Forbidden

        from src.infrastructure.bigquery.client import BigQueryClient

        client = BigQueryClient(project_id="test-project")
        client.client.create_dataset.side_effect = Forbidden("denied")

        with pytest.raises(StorageError, match="Permission denied"):
            client.ensure_dataset()


class TestCreateTable:
    """create_table テスト."""

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_create_table_success(
        self, mock_bigquery: MagicMock, sample_table_def: BQTableDef
    ) -> None:
        from src.infrastructure.bigquery.client import BigQueryClient

        mock_table = MagicMock()
        mock_bigquery.Table.return_value = mock_table

        client = BigQueryClient(project_id="test-project")
        client.create_table(sample_table_def)

        client.client.create_table.assert_called_once_with(mock_table, exists_ok=True)

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_create_table_permission_error(
        self, mock_bigquery: MagicMock, sample_table_def: BQTableDef
    ) -> None:
        from google.api_core.exceptions import Forbidden

        from src.infrastructure.bigquery.client import BigQueryClient

        client = BigQueryClient(project_id="test-project")
        client.client.create_table.side_effect = Forbidden("denied")

        with pytest.raises(StorageError, match="Permission denied"):
            client.create_table(sample_table_def)

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_create_table_general_error(
        self, mock_bigquery: MagicMock, sample_table_def: BQTableDef
    ) -> None:
        from google.cloud.exceptions import GoogleCloudError

        from src.infrastructure.bigquery.client import BigQueryClient

        client = BigQueryClient(project_id="test-project")
        client.client.create_table.side_effect = GoogleCloudError("error")

        with pytest.raises(StorageError, match="Failed to create table"):
            client.create_table(sample_table_def)


class TestCreateAllTables:
    """create_all_tables テスト."""

    @patch("src.infrastructure.bigquery.client.bigquery")
    def test_create_all_tables_calls_ensure_dataset_and_create_table(
        self, mock_bigquery: MagicMock, sample_table_def: BQTableDef
    ) -> None:
        from src.infrastructure.bigquery.client import BigQueryClient

        mock_dataset = MagicMock()
        mock_bigquery.Dataset.return_value = mock_dataset
        mock_table = MagicMock()
        mock_bigquery.Table.return_value = mock_table

        client = BigQueryClient(project_id="test-project")
        table_defs = [sample_table_def, sample_table_def]
        client.create_all_tables(table_defs)

        # ensure_dataset が1回呼ばれる
        client.client.create_dataset.assert_called_once()
        # create_table がテーブル数分呼ばれる
        assert client.client.create_table.call_count == 2
