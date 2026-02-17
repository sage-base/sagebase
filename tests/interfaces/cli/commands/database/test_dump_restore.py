"""データベースダンプ/リストアコマンドのテスト."""

import json

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.interfaces.cli.commands.database.dump_restore import (
    DumpCommand,
    ListDumpsCommand,
    RestoreDumpCommand,
    get_ordered_tables,
    json_serializer,
)


class TestJsonSerializer:
    """JSONシリアライザのテスト."""

    def test_datetime_serialization(self) -> None:
        from datetime import datetime

        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert json_serializer(dt) == "2024-01-15T10:30:00"

    def test_date_serialization(self) -> None:
        from datetime import date

        d = date(2024, 1, 15)
        assert json_serializer(d) == "2024-01-15"

    def test_uuid_serialization(self) -> None:
        from uuid import UUID

        uuid = UUID("12345678-1234-5678-1234-567812345678")
        assert json_serializer(uuid) == "12345678-1234-5678-1234-567812345678"

    def test_decimal_serialization(self) -> None:
        from decimal import Decimal

        d = Decimal("3.14")
        assert json_serializer(d) == 3.14

    def test_bytes_serialization(self) -> None:
        b = b"hello"
        assert json_serializer(b) == "hello"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            json_serializer(set())


class TestGetOrderedTables:
    """テーブル順序のテスト."""

    def test_known_tables_ordered(self) -> None:
        tables = ["speakers", "governing_bodies", "conferences"]
        result = get_ordered_tables(tables)
        assert result == ["governing_bodies", "conferences", "speakers"]

    def test_unknown_tables_appended(self) -> None:
        tables = ["speakers", "new_table", "governing_bodies"]
        result = get_ordered_tables(tables)
        assert result == ["governing_bodies", "speakers", "new_table"]

    def test_alembic_version_excluded(self) -> None:
        tables = ["governing_bodies", "alembic_version"]
        result = get_ordered_tables(tables)
        assert "alembic_version" not in result
        assert result == ["governing_bodies"]

    def test_empty_list(self) -> None:
        result = get_ordered_tables([])
        assert result == []


def _make_connect_side_effect(
    mock_result: MagicMock,
    mock_alembic_result: MagicMock,
) -> Any:
    """テスト用のengine.connect()のside_effectを作成."""

    def connect_side_effect() -> MagicMock:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        def execute_side_effect(query: Any, *args: Any, **kwargs: Any) -> MagicMock:
            if "alembic_version" in str(query):
                return mock_alembic_result
            return mock_result

        mock_conn.execute = MagicMock(side_effect=execute_side_effect)
        return mock_conn

    return connect_side_effect


class TestDumpCommand:
    """DumpCommandのテスト."""

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_dump_creates_json_files(
        self, mock_get_engine: MagicMock, tmp_path: Path
    ) -> None:
        """正常ダンプ: テーブルデータがJSONファイルに出力される."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["test_table", "alembic_version"]
        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            mock_result = MagicMock()
            mock_result.keys.return_value = ["id", "name"]
            mock_result.fetchall.return_value = [(1, "テスト")]

            mock_alembic_result = MagicMock()
            mock_alembic_result.fetchone.return_value = ("abc123",)

            mock_engine.connect = _make_connect_side_effect(
                mock_result, mock_alembic_result
            )

            with patch(
                "src.interfaces.cli.commands.database.dump_restore.DUMPS_BASE_DIR",
                tmp_path,
            ):
                command = DumpCommand()
                command.execute()

        dump_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
        assert len(dump_dirs) == 1

        dump_dir = dump_dirs[0]

        json_file = dump_dir / "test_table.json"
        assert json_file.exists()

        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "テスト"

        metadata_file = dump_dir / "_metadata.json"
        assert metadata_file.exists()

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        assert metadata["table_count"] == 1
        assert metadata["total_records"] == 1
        assert metadata["alembic_revision"] == "abc123"

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_dump_with_tables_option(
        self, mock_get_engine: MagicMock, tmp_path: Path
    ) -> None:
        """--tablesオプションで指定テーブルのみダンプ."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = [
            "table_a",
            "table_b",
            "alembic_version",
        ]
        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            mock_result = MagicMock()
            mock_result.keys.return_value = ["id"]
            mock_result.fetchall.return_value = [(1,)]

            mock_alembic_result = MagicMock()
            mock_alembic_result.fetchone.return_value = None

            mock_engine.connect = _make_connect_side_effect(
                mock_result, mock_alembic_result
            )

            with patch(
                "src.interfaces.cli.commands.database.dump_restore.DUMPS_BASE_DIR",
                tmp_path,
            ):
                command = DumpCommand()
                command.execute(tables="table_a")

        dump_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
        dump_dir = dump_dirs[0]

        assert (dump_dir / "table_a.json").exists()
        assert not (dump_dir / "table_b.json").exists()

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_dump_empty_table(self, mock_get_engine: MagicMock, tmp_path: Path) -> None:
        """空テーブルのダンプ（空配列のJSONが出力される）."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = [
            "empty_table",
            "alembic_version",
        ]
        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            mock_result = MagicMock()
            mock_result.keys.return_value = ["id"]
            mock_result.fetchall.return_value = []

            mock_alembic_result = MagicMock()
            mock_alembic_result.fetchone.return_value = None

            mock_engine.connect = _make_connect_side_effect(
                mock_result, mock_alembic_result
            )

            with patch(
                "src.interfaces.cli.commands.database.dump_restore.DUMPS_BASE_DIR",
                tmp_path,
            ):
                command = DumpCommand()
                command.execute()

        dump_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
        dump_dir = dump_dirs[0]

        json_file = dump_dir / "empty_table.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data == []


class TestRestoreDumpCommand:
    """RestoreDumpCommandのテスト."""

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_restore_inserts_records(
        self, mock_get_engine: MagicMock, tmp_path: Path
    ) -> None:
        """正常リストア: JSONファイルからデータが投入される."""
        dump_dir = tmp_path / "test_dump"
        dump_dir.mkdir()
        (dump_dir / "_metadata.json").write_text(
            json.dumps(
                {
                    "dump_timestamp": "2024-01-15T10:00:00",
                    "table_count": 1,
                    "total_records": 2,
                    "alembic_revision": "abc123",
                    "tables": {"test_table": 2},
                }
            ),
            encoding="utf-8",
        )
        (dump_dir / "test_table.json").write_text(
            json.dumps([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]),
            encoding="utf-8",
        )

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["test_table"]
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "name"},
        ]

        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_engine.begin.return_value = mock_conn

            mock_seq_result = MagicMock()
            mock_seq_result.fetchone.return_value = ("test_table_id_seq",)
            mock_conn.execute.return_value = mock_seq_result

            command = RestoreDumpCommand()
            command.execute(dump_dir=str(dump_dir))

        # INSERT(2レコード) + シーケンスリセット(2クエリ) = 少なくとも4回
        assert mock_conn.execute.call_count >= 2
        # INSERT呼び出しを確認（TextClauseの.textプロパティで検証）
        insert_calls = [
            c
            for c in mock_conn.execute.call_args_list
            if hasattr(c[0][0], "text") and "INSERT" in c[0][0].text
        ]
        assert len(insert_calls) == 2

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_restore_skips_missing_columns(
        self, mock_get_engine: MagicMock, tmp_path: Path
    ) -> None:
        """スキーマ変更耐性: 存在しないカラムのスキップ."""
        dump_dir = tmp_path / "test_dump"
        dump_dir.mkdir()
        (dump_dir / "_metadata.json").write_text(
            json.dumps({"dump_timestamp": "2024-01-15T10:00:00"}),
            encoding="utf-8",
        )
        (dump_dir / "test_table.json").write_text(
            json.dumps([{"id": 1, "name": "A", "old_column": "removed"}]),
            encoding="utf-8",
        )

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["test_table"]
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "name"},
        ]

        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_engine.begin.return_value = mock_conn

            mock_seq_result = MagicMock()
            mock_seq_result.fetchone.return_value = ("test_table_id_seq",)
            mock_conn.execute.return_value = mock_seq_result

            command = RestoreDumpCommand()
            command.execute(dump_dir=str(dump_dir))

        insert_calls = [
            c
            for c in mock_conn.execute.call_args_list
            if hasattr(c[0][0], "text") and "INSERT" in c[0][0].text
        ]
        assert len(insert_calls) == 1
        insert_sql = insert_calls[0][0][0].text
        assert "old_column" not in insert_sql

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_restore_skips_missing_table(
        self, mock_get_engine: MagicMock, tmp_path: Path
    ) -> None:
        """存在しないテーブルのスキップ + 警告."""
        dump_dir = tmp_path / "test_dump"
        dump_dir.mkdir()
        (dump_dir / "_metadata.json").write_text(
            json.dumps({"dump_timestamp": "2024-01-15T10:00:00"}),
            encoding="utf-8",
        )
        (dump_dir / "deleted_table.json").write_text(
            json.dumps([{"id": 1}]),
            encoding="utf-8",
        )

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["other_table"]

        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            command = RestoreDumpCommand()
            command.execute(dump_dir=str(dump_dir))

        mock_engine.begin.assert_not_called()

    @patch("src.infrastructure.config.database.get_db_engine")
    def test_restore_with_truncate(
        self, mock_get_engine: MagicMock, tmp_path: Path
    ) -> None:
        """--truncateオプション."""
        dump_dir = tmp_path / "test_dump"
        dump_dir.mkdir()
        (dump_dir / "_metadata.json").write_text(
            json.dumps({"dump_timestamp": "2024-01-15T10:00:00"}),
            encoding="utf-8",
        )
        (dump_dir / "test_table.json").write_text(
            json.dumps([{"id": 1, "name": "A"}]),
            encoding="utf-8",
        )

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["test_table"]
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "name"},
        ]

        with patch(
            "src.interfaces.cli.commands.database.dump_restore.inspect",
            return_value=mock_inspector,
        ):
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_engine.begin.return_value = mock_conn

            mock_seq_result = MagicMock()
            mock_seq_result.fetchone.return_value = ("test_table_id_seq",)
            mock_conn.execute.return_value = mock_seq_result

            with patch.object(RestoreDumpCommand, "confirm", return_value=True):
                command = RestoreDumpCommand()
                command.execute(dump_dir=str(dump_dir), truncate=True)

        truncate_calls = [
            c
            for c in mock_conn.execute.call_args_list
            if hasattr(c[0][0], "text") and "TRUNCATE" in c[0][0].text
        ]
        assert len(truncate_calls) == 1

    def test_restore_nonexistent_dir(self) -> None:
        """存在しないダンプディレクトリでエラー."""
        command = RestoreDumpCommand()
        with pytest.raises(SystemExit):
            command.execute(dump_dir="/nonexistent/path")

    def test_fk_insert_order(self) -> None:
        """FK投入順序の検証."""
        tables = [
            "speakers",
            "governing_bodies",
            "conversations",
            "conferences",
        ]
        ordered = get_ordered_tables(tables)
        gov_idx = ordered.index("governing_bodies")
        conf_idx = ordered.index("conferences")
        spk_idx = ordered.index("speakers")
        conv_idx = ordered.index("conversations")
        assert gov_idx < conf_idx < spk_idx < conv_idx


class TestListDumpsCommand:
    """ListDumpsCommandのテスト."""

    def test_list_dumps_with_data(self, tmp_path: Path) -> None:
        """ダンプ一覧の表示."""
        dump_dir = tmp_path / "2024-01-15_100000"
        dump_dir.mkdir()
        (dump_dir / "_metadata.json").write_text(
            json.dumps(
                {
                    "dump_timestamp": "2024-01-15T10:00:00",
                    "table_count": 5,
                    "total_records": 100,
                    "alembic_revision": "abc123",
                }
            ),
            encoding="utf-8",
        )

        with patch(
            "src.interfaces.cli.commands.database.dump_restore.DUMPS_BASE_DIR",
            tmp_path,
        ):
            command = ListDumpsCommand()
            command.execute()

    def test_list_dumps_empty_directory(self, tmp_path: Path) -> None:
        """空ディレクトリの場合."""
        with patch(
            "src.interfaces.cli.commands.database.dump_restore.DUMPS_BASE_DIR",
            tmp_path,
        ):
            command = ListDumpsCommand()
            command.execute()

    def test_list_dumps_no_directory(self, tmp_path: Path) -> None:
        """ダンプディレクトリが存在しない場合."""
        non_existent = tmp_path / "non_existent"
        with patch(
            "src.interfaces.cli.commands.database.dump_restore.DUMPS_BASE_DIR",
            non_existent,
        ):
            command = ListDumpsCommand()
            command.execute()
