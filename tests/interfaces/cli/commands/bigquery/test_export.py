"""ExportToBigQueryCommand のテスト."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from click.testing import CliRunner

from src.interfaces.cli.commands.bigquery.export import (
    ExportToBigQueryCommand,
    serialize_row,
    serialize_value,
)


class TestSerializeValue:
    """serialize_value のテスト."""

    def test_none(self) -> None:
        assert serialize_value(None) is None

    def test_datetime(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert serialize_value(dt) == "2024-01-15T10:30:00"

    def test_date(self) -> None:
        d = date(2024, 1, 15)
        assert serialize_value(d) == "2024-01-15"

    def test_uuid(self) -> None:
        u = UUID("12345678-1234-5678-1234-567812345678")
        assert serialize_value(u) == "12345678-1234-5678-1234-567812345678"

    def test_decimal(self) -> None:
        assert serialize_value(Decimal("3.14")) == 3.14

    def test_bytes(self) -> None:
        assert serialize_value(b"hello") == "hello"

    def test_string_passthrough(self) -> None:
        assert serialize_value("test") == "test"

    def test_int_passthrough(self) -> None:
        assert serialize_value(42) == 42

    def test_bool_passthrough(self) -> None:
        assert serialize_value(True) is True

    def test_dict_passthrough(self) -> None:
        d = {"key": "value"}
        assert serialize_value(d) == {"key": "value"}

    def test_list_passthrough(self) -> None:
        lst = [1, 2, 3]
        assert serialize_value(lst) == [1, 2, 3]


class TestSerializeRow:
    """serialize_row のテスト."""

    def test_mixed_types(self) -> None:
        row = {
            "id": 1,
            "name": "test",
            "created_at": datetime(2024, 1, 15, 10, 30, 0),
            "score": Decimal("0.95"),
            "is_active": True,
            "deleted_at": None,
        }
        result = serialize_row(row)
        assert result == {
            "id": 1,
            "name": "test",
            "created_at": "2024-01-15T10:30:00",
            "score": 0.95,
            "is_active": True,
            "deleted_at": None,
        }

    def test_empty_row(self) -> None:
        assert serialize_row({}) == {}


class TestExportToBigQueryCommand:
    """ExportToBigQueryCommand のテスト."""

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project", "BQ_DATASET_ID": "test_dataset"},
    )
    @patch("src.interfaces.cli.commands.bigquery.export.inspect")
    @patch("src.interfaces.cli.commands.bigquery.export.get_db_engine")
    @patch("src.interfaces.cli.commands.bigquery.export.BigQueryClient")
    def test_export_single_table(
        self,
        mock_bq_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_inspect: MagicMock,
    ) -> None:
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq
        mock_bq.load_table_data.return_value = 2

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_inspect.return_value.get_table_names.return_value = ["politicians"]
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # COUNT(*)クエリ用とSELECTクエリ用のモック
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2
        mock_select_result = MagicMock()
        mock_select_result.keys.return_value = ["id", "name"]
        mock_select_result.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
        mock_conn.execute.side_effect = [mock_count_result, mock_select_result]

        cmd = ExportToBigQueryCommand()
        cmd.execute(table="politicians", export_all=False, dataset=None)

        mock_bq.ensure_dataset.assert_called_once()
        mock_bq.load_table_data.assert_called_once()

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    @patch("src.interfaces.cli.commands.bigquery.export.inspect")
    @patch("src.interfaces.cli.commands.bigquery.export.get_db_engine")
    @patch("src.interfaces.cli.commands.bigquery.export.BigQueryClient")
    def test_export_all_tables(
        self,
        mock_bq_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_inspect: MagicMock,
    ) -> None:
        from src.infrastructure.bigquery.schema import GOLD_LAYER_TABLES

        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq
        mock_bq.load_table_data.return_value = 0

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_inspect.return_value.get_table_names.return_value = [
            t.table_id for t in GOLD_LAYER_TABLES
        ]
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # COUNT(*)は0を返す、SELECTは空リストを返す（各テーブルで繰り返し）
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_select_result = MagicMock()
        mock_select_result.keys.return_value = ["id"]
        mock_select_result.fetchall.return_value = []
        mock_conn.execute.side_effect = lambda _q: (
            mock_count_result if "COUNT" in str(_q) else mock_select_result
        )

        cmd = ExportToBigQueryCommand()
        cmd.execute(table=None, export_all=True, dataset=None)

        mock_bq.ensure_dataset.assert_called_once()

    def test_no_table_and_no_all_exits(self) -> None:
        cmd = ExportToBigQueryCommand()
        with pytest.raises(SystemExit):
            cmd.execute(table=None, export_all=False)

    @patch.dict("os.environ", {}, clear=False)
    def test_missing_project_id_exits(self) -> None:
        import os

        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        cmd = ExportToBigQueryCommand()
        with pytest.raises(SystemExit):
            cmd.execute(table="politicians", export_all=False)

    def test_invalid_table_name_exits(self) -> None:
        cmd = ExportToBigQueryCommand()
        with pytest.raises(SystemExit):
            cmd.execute(table="nonexistent_table", export_all=False)

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    @patch("src.interfaces.cli.commands.bigquery.export.inspect")
    @patch("src.interfaces.cli.commands.bigquery.export.get_db_engine")
    @patch("src.interfaces.cli.commands.bigquery.export.BigQueryClient")
    def test_empty_table_creates_table_without_load(
        self,
        mock_bq_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_inspect: MagicMock,
    ) -> None:
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_inspect.return_value.get_table_names.return_value = ["politicians"]
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # COUNT(*)は0を返す、SELECTは空リストを返す
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_select_result = MagicMock()
        mock_select_result.keys.return_value = ["id", "name"]
        mock_select_result.fetchall.return_value = []
        mock_conn.execute.side_effect = [mock_count_result, mock_select_result]

        cmd = ExportToBigQueryCommand()
        cmd.execute(table="politicians", export_all=False, dataset=None)

        mock_bq.load_table_data.assert_not_called()
        mock_bq.create_table.assert_called_once()

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    @patch("src.interfaces.cli.commands.bigquery.export.inspect")
    @patch("src.interfaces.cli.commands.bigquery.export.get_db_engine")
    @patch("src.interfaces.cli.commands.bigquery.export.BigQueryClient")
    def test_missing_pg_table_is_skipped(
        self,
        mock_bq_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_inspect: MagicMock,
    ) -> None:
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_inspect.return_value.get_table_names.return_value = []

        cmd = ExportToBigQueryCommand()
        cmd.execute(table="politicians", export_all=False, dataset=None)

        mock_bq.load_table_data.assert_not_called()
        mock_engine.connect.assert_not_called()


class TestExportToBqClickCommand:
    """Click コマンドの結合テスト."""

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project", "BQ_DATASET_ID": "test_dataset"},
    )
    @patch("src.interfaces.cli.commands.bigquery.export.inspect")
    @patch("src.interfaces.cli.commands.bigquery.export.get_db_engine")
    @patch("src.interfaces.cli.commands.bigquery.export.BigQueryClient")
    def test_click_command_with_all_flag(
        self,
        mock_bq_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_inspect: MagicMock,
    ) -> None:
        from src.infrastructure.bigquery.schema import GOLD_LAYER_TABLES
        from src.interfaces.cli.commands.bigquery import export_to_bq

        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq
        mock_bq.load_table_data.return_value = 0

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_inspect.return_value.get_table_names.return_value = [
            t.table_id for t in GOLD_LAYER_TABLES
        ]
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_select_result = MagicMock()
        mock_select_result.keys.return_value = ["id"]
        mock_select_result.fetchall.return_value = []
        mock_conn.execute.side_effect = lambda _q: (
            mock_count_result if "COUNT" in str(_q) else mock_select_result
        )

        runner = CliRunner()
        result = runner.invoke(export_to_bq, ["--all"])
        assert result.exit_code == 0

    @patch.dict(
        "os.environ",
        {"GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    @patch("src.interfaces.cli.commands.bigquery.export.inspect")
    @patch("src.interfaces.cli.commands.bigquery.export.get_db_engine")
    @patch("src.interfaces.cli.commands.bigquery.export.BigQueryClient")
    def test_click_command_with_table_and_dataset(
        self,
        mock_bq_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_inspect: MagicMock,
    ) -> None:
        from src.interfaces.cli.commands.bigquery import export_to_bq

        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq
        mock_bq.load_table_data.return_value = 1

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_inspect.return_value.get_table_names.return_value = ["politicians"]
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # COUNT(*)は1を返す、SELECTは1行返す
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_select_result = MagicMock()
        mock_select_result.keys.return_value = ["id", "name"]
        mock_select_result.fetchall.return_value = [(1, "test")]
        mock_conn.execute.side_effect = [mock_count_result, mock_select_result]

        runner = CliRunner()
        result = runner.invoke(
            export_to_bq, ["--table", "politicians", "--dataset", "custom_dataset"]
        )
        assert result.exit_code == 0
        mock_bq_cls.assert_called_once_with(
            project_id="test-project",
            dataset_id="custom_dataset",
            location="asia-northeast1",
        )
