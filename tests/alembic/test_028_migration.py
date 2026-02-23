"""マイグレーション028のテスト: 政党所属データのparty_membership_historyへの移行."""

import importlib.util

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def migration_028():
    """マイグレーションモジュールをimportlibでロードする."""
    migration_path = (
        Path(__file__).parent.parent.parent
        / "alembic"
        / "versions"
        / "028_migrate_political_party_to_history.py"
    )
    spec = importlib.util.spec_from_file_location("migration_028", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigration028:
    """マイグレーション028の正当性テスト."""

    def test_revision_chain(self, migration_028) -> None:
        """リビジョンチェーンが正しいこと."""
        assert migration_028.revision == "028"
        assert migration_028.down_revision == "027"

    def test_upgrade_executes_insert(self, migration_028) -> None:
        """upgradeがINSERT文を実行すること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()

            mock_op.execute.assert_called_once()
            sql = mock_op.execute.call_args[0][0]

            assert "INSERT INTO party_membership_history" in sql
            assert "politician_id" in sql
            assert "political_party_id" in sql
            assert "start_date" in sql

    def test_upgrade_uses_election_date_as_primary_start_date(
        self, migration_028
    ) -> None:
        """upgradeが選挙日を第1優先のstart_dateとして使用すること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "election_members" in sql
            assert "elections" in sql
            assert "MIN(e.election_date)" in sql

    def test_upgrade_uses_created_at_as_fallback(self, migration_028) -> None:
        """upgradeがcreated_atをフォールバックとして使用すること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "COALESCE" in sql
            assert "created_at::date" in sql

    def test_upgrade_is_idempotent(self, migration_028) -> None:
        """upgradeが冪等であること（NOT EXISTSで重複スキップ）."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "NOT EXISTS" in sql
            assert "end_date IS NULL" in sql

    def test_upgrade_filters_non_null_party_id(self, migration_028) -> None:
        """upgradeがpolitical_party_idがNULLでないレコードのみ対象とすること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "political_party_id IS NOT NULL" in sql

    def test_upgrade_logs_migrated_count(self, migration_028) -> None:
        """upgradeが移行件数をRAISE NOTICEで出力すること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "RAISE NOTICE" in sql
            assert "GET DIAGNOSTICS" in sql

    def test_downgrade_deletes_migrated_records(self, migration_028) -> None:
        """downgradeが移行したレコードのみを削除すること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.downgrade()

            mock_op.execute.assert_called_once()
            sql = mock_op.execute.call_args[0][0]

            assert "DELETE FROM party_membership_history" in sql

    def test_downgrade_only_deletes_matching_records(self, migration_028) -> None:
        """downgradeがpoliticiansと一致するend_date IS NULLのみ削除."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.downgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "end_date IS NULL" in sql
            assert "p.political_party_id = pmh.political_party_id" in sql

    def test_downgrade_logs_deleted_count(self, migration_028) -> None:
        """downgradeが削除件数をRAISE NOTICEで出力すること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.downgrade()
            sql = mock_op.execute.call_args[0][0]

            assert "RAISE NOTICE" in sql
            assert "GET DIAGNOSTICS" in sql

    def test_upgrade_downgrade_symmetry(self, migration_028) -> None:
        """upgradeとdowngradeが対称であること."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            upgrade_sql = mock_op.execute.call_args[0][0]

        with patch.object(migration_028, "op") as mock_op:
            migration_028.downgrade()
            downgrade_sql = mock_op.execute.call_args[0][0]

        assert "INSERT INTO party_membership_history" in upgrade_sql
        assert "DELETE FROM party_membership_history" in downgrade_sql

    def test_idempotency_double_upgrade(self, migration_028) -> None:
        """upgradeを2回実行してもエラーにならないこと（NOT EXISTS句による保護）."""
        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            first_sql = mock_op.execute.call_args[0][0]

        with patch.object(migration_028, "op") as mock_op:
            migration_028.upgrade()
            second_sql = mock_op.execute.call_args[0][0]

        assert first_sql == second_sql
        assert "NOT EXISTS" in second_sql
