"""データベースのJSONダンプ/リストアコマンド.

スキーマ変更（Alembic migration）時にDockerボリュームが削除されても、
Seedファイルで復旧できないフロー情報を保全するための機能。
"""

import json
import logging

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import inspect, text

from src.interfaces.cli.base import BaseCommand, Command


logger = logging.getLogger(__name__)

# プロジェクトルートのdumps/ディレクトリ
DUMPS_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "dumps"

# FK制約を考慮した投入順序（固定リスト）
TABLE_INSERT_ORDER = [
    # 1. 独立テーブル（FK依存なし）
    "governing_bodies",
    "political_parties",
    "users",
    # 2. 第1レベルFK依存
    "elections",
    "conferences",
    "politicians",
    # 3. 第2レベルFK依存
    "election_members",
    "meetings",
    "parliamentary_groups",
    "pledges",
    "party_membership_history",
    # 4. 第3レベルFK依存
    "minutes",
    "proposals",
    "speakers",
    "politician_affiliations",
    # 5. 第4レベルFK依存
    "conversations",
    "proposal_submitters",
    "proposal_judges",
    "proposal_parliamentary_group_judges",
    "proposal_meeting_occurrences",
    "proposal_deliberations",
    # 6. 第5レベルFK依存
    "proposal_judge_parliamentary_groups",
    "proposal_judge_politicians",
    "extracted_parliamentary_group_members",
    "extracted_conference_members",
    "extracted_proposal_judges",
    "parliamentary_group_memberships",
    # 7. ログ・履歴テーブル
    "llm_processing_history",
    "prompt_versions",
    "extraction_logs",
    "politician_operation_logs",
    "proposal_operation_logs",
]


def json_serializer(obj: Any) -> Any:
    """JSON非対応型のシリアライザ."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def get_ordered_tables(all_tables: list[str]) -> list[str]:
    """FK制約を考慮した投入順序でテーブルリストをソート."""
    order_map = {name: i for i, name in enumerate(TABLE_INSERT_ORDER)}

    known = [t for t in all_tables if t in order_map]
    unknown = [t for t in all_tables if t not in order_map]

    known.sort(key=lambda t: order_map[t])
    unknown.sort()

    # 不明テーブルは末尾に追加（alembic_versionは除外）
    return known + [t for t in unknown if t != "alembic_version"]


class DumpCommand(Command, BaseCommand):
    """データベースをJSON形式でダンプするコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """データベースダンプを実行."""
        from src.infrastructure.config.database import get_db_engine

        tables_arg: str | None = kwargs.get("tables")
        engine = get_db_engine()

        # テーブル一覧を取得
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()

        if tables_arg:
            target_tables = [t.strip() for t in tables_arg.split(",")]
            missing = [t for t in target_tables if t not in all_tables]
            if missing:
                self.warning(f"存在しないテーブル: {', '.join(missing)}")
            target_tables = [t for t in target_tables if t in all_tables]
        else:
            target_tables = [t for t in all_tables if t != "alembic_version"]

        if not target_tables:
            self.error("ダンプ対象のテーブルがありません")
            return

        # ダンプディレクトリ作成
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dump_dir = DUMPS_BASE_DIR / timestamp
        dump_dir.mkdir(parents=True, exist_ok=True)

        self.show_progress(f"ダンプ先: {dump_dir}")

        # Alembic revisionを取得
        alembic_revision = None
        if "alembic_version" in all_tables:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                if row:
                    alembic_revision = row[0]

        total_records = 0
        table_stats: dict[str, int] = {}

        for table_name in sorted(target_tables):
            self.show_progress(f"  ダンプ中: {table_name}...")
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT * FROM "{table_name}"'))  # noqa: S608
                columns = list(result.keys())
                rows = [
                    dict(zip(columns, row, strict=True)) for row in result.fetchall()
                ]

            # JSONファイルに出力
            output_path = dump_dir / f"{table_name}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    rows, f, ensure_ascii=False, indent=2, default=json_serializer
                )

            table_stats[table_name] = len(rows)
            total_records += len(rows)
            self.show_progress(f"    {len(rows)} レコード")

        # メタデータを出力
        metadata: dict[str, Any] = {
            "dump_timestamp": datetime.now().isoformat(),
            "table_count": len(target_tables),
            "total_records": total_records,
            "alembic_revision": alembic_revision,
            "tables": table_stats,
        }
        metadata_path = dump_dir / "_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        self.success(
            f"ダンプ完了: {len(target_tables)} テーブル, "
            f"{total_records} レコード -> {dump_dir}"
        )


class RestoreDumpCommand(Command, BaseCommand):
    """JSONダンプからデータベースをリストアするコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """ダンプからリストアを実行."""
        from src.infrastructure.config.database import get_db_engine

        dump_dir_str: str | None = kwargs.get("dump_dir")
        truncate: bool = kwargs.get("truncate", False)

        if not dump_dir_str:
            self.error("ダンプディレクトリを指定してください")
            return

        dump_dir = Path(dump_dir_str)
        if not dump_dir.is_absolute():
            dump_dir = DUMPS_BASE_DIR / dump_dir_str

        if not dump_dir.exists():
            self.error(f"ダンプディレクトリが見つかりません: {dump_dir}")
            return

        # メタデータ読み込み
        metadata_path = dump_dir / "_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
            self.show_progress("ダンプ情報:")
            self.show_progress(f"  日時: {metadata.get('dump_timestamp', '不明')}")
            self.show_progress(f"  テーブル数: {metadata.get('table_count', '不明')}")
            self.show_progress(f"  レコード数: {metadata.get('total_records', '不明')}")
            self.show_progress(
                f"  Alembic revision: {metadata.get('alembic_revision', '不明')}"
            )

        engine = get_db_engine()
        inspector = inspect(engine)
        current_tables = inspector.get_table_names()

        # JSONファイル一覧を取得
        json_files = [f for f in dump_dir.glob("*.json") if f.name != "_metadata.json"]
        if not json_files:
            self.error("ダンプファイルが見つかりません")
            return

        # FK制約を考慮した投入順序でソート
        dump_table_names = [f.stem for f in json_files]
        ordered_tables = get_ordered_tables(dump_table_names)

        # truncateオプション
        if truncate:
            if not self.confirm("既存データを削除してからリストアしますか？"):
                self.show_progress("キャンセルしました")
                return
            self.show_progress("既存データを削除中...")
            # 逆順でTRUNCATE（FK制約を考慮）
            with engine.begin() as conn:
                for table_name in reversed(ordered_tables):
                    if table_name in current_tables:
                        conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                        self.show_progress(f"  TRUNCATE: {table_name}")

        total_inserted = 0

        for table_name in ordered_tables:
            json_path = dump_dir / f"{table_name}.json"
            if not json_path.exists():
                continue

            if table_name not in current_tables:
                self.warning(f"テーブルが存在しません（スキップ）: {table_name}")
                continue

            with open(json_path, encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                self.show_progress(f"  スキップ（空）: {table_name}")
                continue

            # 現在のカラム一覧を取得
            current_columns = {col["name"] for col in inspector.get_columns(table_name)}

            # 最初のレコードのキーと現在のカラムの交差を取得
            dump_columns = set(records[0].keys())
            valid_columns = dump_columns & current_columns
            skipped_columns = dump_columns - current_columns

            if skipped_columns:
                cols = ", ".join(sorted(skipped_columns))
                self.warning(f"  {table_name}: 存在しないカラムをスキップ: {cols}")

            if not valid_columns:
                self.warning(f"  {table_name}: 有効なカラムがありません（スキップ）")
                continue

            # INSERT実行
            sorted_columns = sorted(valid_columns)
            columns_str = ", ".join(f'"{c}"' for c in sorted_columns)
            placeholders = ", ".join(f":{c}" for c in sorted_columns)
            insert_sql = (
                f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
            )

            inserted = 0
            with engine.begin() as conn:
                for record in records:
                    params = {
                        c: self._adapt_value(record.get(c)) for c in sorted_columns
                    }
                    try:
                        conn.execute(text(insert_sql), params)
                        inserted += 1
                    except Exception as e:
                        self.warning(f"  {table_name}: レコード挿入エラー: {e}")
                        logger.warning(f"INSERT失敗 ({table_name}): {e}")

            # シーケンスリセット（idカラムがある場合）
            if "id" in valid_columns:
                self._reset_sequence(engine, table_name)

            total_inserted += inserted
            self.show_progress(f"  リストア: {table_name} ({inserted} レコード)")

        self.success(f"リストア完了: {total_inserted} レコード")

    @staticmethod
    def _adapt_value(value: Any) -> Any:
        """JSONB型カラム用にdict/listをpsycopg2.extras.Jsonでラップ."""
        if isinstance(value, (dict, list)):
            from psycopg2.extras import Json

            return Json(value)
        return value

    @staticmethod
    def _reset_sequence(engine: Any, table_name: str) -> None:
        """テーブルのシーケンスをリセット."""
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        f"SELECT pg_get_serial_sequence('{table_name}', 'id')"  # noqa: S608
                    )
                )
                row = result.fetchone()
                if row and row[0]:
                    seq_name = row[0]
                    setval_sql = (
                        f"SELECT setval('{seq_name}', "  # noqa: S608
                        f'COALESCE((SELECT MAX(id) FROM "{table_name}"), 1))'
                    )
                    conn.execute(text(setval_sql))
        except Exception as e:
            logger.warning(f"シーケンスリセット失敗 ({table_name}): {e}")


class ListDumpsCommand(Command, BaseCommand):
    """過去のダンプ一覧を表示するコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """ダンプ一覧を表示."""
        if not DUMPS_BASE_DIR.exists():
            self.show_progress("ダンプはまだありません")
            return

        dump_dirs = sorted(
            [d for d in DUMPS_BASE_DIR.iterdir() if d.is_dir()],
            reverse=True,
        )

        if not dump_dirs:
            self.show_progress("ダンプはまだありません")
            return

        self.show_progress(f"ダンプ一覧 ({len(dump_dirs)} 件):")
        self.show_progress("-" * 70)

        for dump_dir in dump_dirs:
            metadata_path = dump_dir / "_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, encoding="utf-8") as f:
                    metadata = json.load(f)
                table_count = metadata.get("table_count", "?")
                total_records = metadata.get("total_records", "?")
                revision = metadata.get("alembic_revision", "不明")
                self.show_progress(
                    f"  {dump_dir.name}  "
                    f"テーブル: {table_count}, "
                    f"レコード: {total_records}, "
                    f"revision: {revision}"
                )
            else:
                self.show_progress(f"  {dump_dir.name}  (メタデータなし)")
