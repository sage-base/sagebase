"""データベースのJSONダンプ/リストアコマンド.

全データをJSON形式でダンプし、GCSに保存して開発者間で共有する。
Alembic revisionと紐付けてスキーマ互換性を管理する。
"""

import gzip
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

# GCSのダンプ保存先プレフィックス
GCS_DUMPS_PREFIX = "database-dumps/"

# 現在のメタデータフォーマットバージョン
DUMP_FORMAT_VERSION = 1

# ストリーミングダンプのバッチサイズ（サーバーサイドカーソルのyield_per）
_DUMP_BATCH_SIZE = 10_000
# リストアのバッチINSERTサイズ
_RESTORE_BATCH_SIZE = 1_000
# ストリーミングパースに切り替えるファイルサイズ閾値
_STREAMING_THRESHOLD = 10 * 1024 * 1024  # 10MB

# FK制約を考慮した投入順序（固定リスト）
TABLE_INSERT_ORDER = [
    # 1. 独立テーブル（FK依存なし）
    "governing_bodies",
    "political_parties",
    "users",
    "government_officials",
    # 2. 第1レベルFK依存
    "elections",
    "conferences",
    "politicians",
    "government_official_positions",
    # 3. 第2レベルFK依存
    "election_members",
    "meetings",
    "parliamentary_groups",
    "parliamentary_group_parties",
    "pledges",
    "party_membership_history",
    # 4. 第3レベルFK依存
    "minutes",
    "proposals",
    "speakers",
    "conference_members",
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


def get_current_alembic_revision(engine: Any) -> str | None:
    """現在のDBのAlembic revisionを取得."""
    try:
        inspector = inspect(engine)
        if "alembic_version" not in inspector.get_table_names():
            return None
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _get_gcs_storage() -> Any:
    """GCSStorageインスタンスを取得. GCS未設定の場合はNoneを返す."""
    try:
        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.storage.gcs_client import HAS_GCS, GCSStorage

        if not HAS_GCS:
            return None

        settings = get_settings()
        if not settings.gcs_upload_enabled:
            return None

        return GCSStorage(
            bucket_name=settings.gcs_bucket_name,
            project_id=settings.gcs_project_id,
        )
    except Exception as e:
        logger.warning(f"GCSStorage初期化失敗: {e}")
        return None


class DumpCommand(Command, BaseCommand):
    """データベースをJSON形式でダンプするコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """データベースダンプを実行."""
        from src.infrastructure.config.database import get_db_engine

        tables_arg: str | None = kwargs.get("tables")
        use_gcs: bool = kwargs.get("gcs", False)
        description: str | None = kwargs.get("description")
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
        alembic_revision = get_current_alembic_revision(engine)

        total_records = 0
        table_stats: dict[str, int] = {}

        for table_name in sorted(target_tables):
            self.show_progress(f"  ダンプ中: {table_name}...")
            output_path = dump_dir / f"{table_name}.json.gz"
            count = self._dump_table_streaming(engine, table_name, output_path)
            table_stats[table_name] = count
            total_records += count
            self.show_progress(f"    {count} レコード")

        # メタデータを出力
        metadata: dict[str, Any] = {
            "dump_version": DUMP_FORMAT_VERSION,
            "dump_timestamp": datetime.now().isoformat(),
            "alembic_revision": alembic_revision,
            "table_count": len(target_tables),
            "total_records": total_records,
            "tables": table_stats,
        }
        if description:
            metadata["description"] = description

        metadata_path = dump_dir / "_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        self.success(
            f"ダンプ完了: {len(target_tables)} テーブル, "
            f"{total_records} レコード -> {dump_dir}"
        )

        # GCSへアップロード
        if use_gcs:
            self._upload_to_gcs(dump_dir, timestamp)

    @staticmethod
    def _dump_table_streaming(
        engine: Any,
        table_name: str,
        output_path: Path,
        batch_size: int = _DUMP_BATCH_SIZE,
    ) -> int:
        """テーブルをサーバーサイドカーソル+ストリーミングでgzip圧縮JSONに書き出す."""
        count = 0
        with gzip.open(output_path, "wt", encoding="utf-8") as f:
            f.write("[\n")
            first = True
            with engine.connect().execution_options(
                stream_results=True, yield_per=batch_size
            ) as conn:
                result = conn.execute(
                    text(f'SELECT * FROM "{table_name}"')  # noqa: S608
                )
                columns = list(result.keys())
                for row in result:
                    record = dict(zip(columns, row, strict=True))
                    if not first:
                        f.write(",\n")
                    json.dump(
                        record,
                        f,
                        ensure_ascii=False,
                        default=json_serializer,
                    )
                    first = False
                    count += 1
            f.write("\n]\n")
        return count

    def _upload_to_gcs(self, dump_dir: Path, timestamp: str) -> None:
        """ダンプディレクトリをGCSにアップロード."""
        gcs = _get_gcs_storage()
        if not gcs:
            self.warning("GCSが利用できないため、ローカルダンプのみ作成しました")
            return

        self.show_progress("GCSにアップロード中...")
        gcs_prefix = f"{GCS_DUMPS_PREFIX}{timestamp}"

        for file_path in dump_dir.iterdir():
            if file_path.is_file():
                gcs_path = f"{gcs_prefix}/{file_path.name}"
                if file_path.suffix == ".gz":
                    content_type = "application/gzip"
                else:
                    content_type = "application/json"
                gcs.upload_file(
                    local_path=file_path,
                    gcs_path=gcs_path,
                    content_type=content_type,
                )

        self.success(f"GCSアップロード完了: {gcs_prefix}")


class RestoreDumpCommand(Command, BaseCommand):
    """JSONダンプからデータベースをリストアするコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """ダンプからリストアを実行."""
        from src.infrastructure.config.database import get_db_engine

        dump_dir_str: str | None = kwargs.get("dump_dir")
        truncate: bool = kwargs.get("truncate", False)
        force: bool = kwargs.get("force", False)
        skip_confirm: bool = kwargs.get("skip_confirm", False)

        if not dump_dir_str:
            self.error("ダンプディレクトリを指定してください")
            return

        # GCS URIの場合はダウンロード
        if dump_dir_str.startswith("gs://"):
            dump_dir = self._download_from_gcs(dump_dir_str)
            if not dump_dir:
                return
        else:
            dump_dir = Path(dump_dir_str)
            if not dump_dir.is_absolute():
                dump_dir = DUMPS_BASE_DIR / dump_dir_str

        if not dump_dir.exists():
            self.error(f"ダンプディレクトリが見つかりません: {dump_dir}")
            return

        engine = get_db_engine()

        # メタデータ読み込みとrevisionチェック
        metadata = self._load_and_check_metadata(dump_dir, engine, force)
        if metadata is False:
            return

        inspector = inspect(engine)
        current_tables = inspector.get_table_names()

        # ダンプファイル一覧を取得（.json.gz優先、.jsonも後方互換でサポート）
        dump_files: dict[str, Path] = {}
        for f in dump_dir.iterdir():
            if f.name == "_metadata.json" or not f.is_file():
                continue
            if f.name.endswith(".json.gz"):
                table_name = f.name.removesuffix(".json.gz")
                dump_files[table_name] = f
            elif f.suffix == ".json" and f.stem not in dump_files:
                dump_files[f.stem] = f

        if not dump_files:
            self.error("ダンプファイルが見つかりません")
            return

        # FK制約を考慮した投入順序でソート
        ordered_tables = get_ordered_tables(list(dump_files.keys()))

        # truncateオプション
        if truncate:
            if not skip_confirm:
                if not self.confirm("既存データを削除してからリストアしますか？"):
                    self.show_progress("キャンセルしました")
                    return
            self._truncate_tables(engine, ordered_tables, current_tables)

        total_inserted = 0

        for table_name in ordered_tables:
            if table_name not in dump_files:
                continue

            if table_name not in current_tables:
                self.warning(f"テーブルが存在しません（スキップ）: {table_name}")
                continue

            file_path = dump_files[table_name]
            self.show_progress(f"  リストア中: {table_name}...")
            inserted = self._restore_table_streaming(
                engine, inspector, table_name, file_path
            )
            if inserted == 0:
                self.show_progress(f"  スキップ（空）: {table_name}")
            else:
                self.show_progress(f"  リストア: {table_name} ({inserted} レコード)")
            total_inserted += inserted

        self.success(f"リストア完了: {total_inserted} レコード")

    def _load_and_check_metadata(
        self, dump_dir: Path, engine: Any, force: bool
    ) -> dict[str, Any] | bool:
        """メタデータを読み込み、revision互換性をチェック.

        Returns:
            メタデータdict（成功時）、False（チェック失敗で中断時）
        """
        metadata_path = dump_dir / "_metadata.json"
        if not metadata_path.exists():
            self.warning("メタデータファイルがありません（revisionチェックをスキップ）")
            return {}

        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        self.show_progress("ダンプ情報:")
        self.show_progress(f"  日時: {metadata.get('dump_timestamp', '不明')}")
        self.show_progress(f"  テーブル数: {metadata.get('table_count', '不明')}")
        self.show_progress(f"  レコード数: {metadata.get('total_records', '不明')}")
        self.show_progress(
            f"  Alembic revision: {metadata.get('alembic_revision', '不明')}"
        )
        if metadata.get("description"):
            self.show_progress(f"  説明: {metadata['description']}")

        # Alembic revision互換性チェック
        dump_revision = metadata.get("alembic_revision")
        if dump_revision:
            current_revision = get_current_alembic_revision(engine)
            if current_revision and dump_revision != current_revision:
                self.warning(
                    f"Alembic revisionが一致しません: "
                    f"DUMP={dump_revision}, DB={current_revision}"
                )
                if not force:
                    self.error(
                        "revisionが異なるためリストアを中断します。"
                        "--force オプションで強制リストアできます"
                    )
                    return False
                self.warning("--force が指定されたため、強制リストアを実行します")

        return metadata

    def _truncate_tables(
        self, engine: Any, ordered_tables: list[str], current_tables: list[str]
    ) -> None:
        """テーブルをFK制約の逆順でTRUNCATE."""
        self.show_progress("既存データを削除中...")
        with engine.begin() as conn:
            for table_name in reversed(ordered_tables):
                if table_name in current_tables:
                    conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                    self.show_progress(f"  TRUNCATE: {table_name}")

    def _restore_table_streaming(
        self,
        engine: Any,
        inspector: Any,
        table_name: str,
        json_path: Path,
        batch_size: int = _RESTORE_BATCH_SIZE,
    ) -> int:
        """JSONファイルをストリーミングでパースしてバッチINSERTする.

        ダンプ形式（1行1レコード: [{...},\\n{...},...\\n]）を行単位で読み込み、
        メモリを節約する。小さなファイルは通常のjson.loadにフォールバック。
        """
        current_columns = {col["name"] for col in inspector.get_columns(table_name)}
        insert_sql: str | None = None
        sorted_columns: list[str] | None = None
        skipped_logged = False
        inserted = 0
        batch: list[dict[str, Any]] = []

        for record in self._iter_json_records(json_path):
            # 初回レコードでSQL文を構築
            if insert_sql is None:
                dump_columns = set(record.keys())
                valid_columns = dump_columns & current_columns
                skipped_columns = dump_columns - current_columns

                if skipped_columns and not skipped_logged:
                    cols = ", ".join(sorted(skipped_columns))
                    self.warning(f"  {table_name}: 存在しないカラムをスキップ: {cols}")
                    skipped_logged = True

                if not valid_columns:
                    self.warning(
                        f"  {table_name}: 有効なカラムがありません（スキップ）"
                    )
                    return 0

                sorted_columns = sorted(valid_columns)
                columns_str = ", ".join(f'"{c}"' for c in sorted_columns)
                placeholders = ", ".join(f":{c}" for c in sorted_columns)
                insert_sql = (
                    f'INSERT INTO "{table_name}" ({columns_str})'
                    f" VALUES ({placeholders})"
                )

            params = {
                c: self._adapt_value(record.get(c))
                for c in sorted_columns  # type: ignore[union-attr]
            }
            batch.append(params)

            if len(batch) >= batch_size:
                inserted += self._flush_batch(engine, insert_sql, batch, table_name)
                batch = []

        # 残りのバッチを処理
        if batch and insert_sql:
            inserted += self._flush_batch(engine, insert_sql, batch, table_name)

        if sorted_columns and "id" in sorted_columns:
            self._reset_sequence(engine, table_name)

        return inserted

    @staticmethod
    def _open_dump_file(path: Path) -> Any:
        """ダンプファイルを開く（.gz対応）."""
        if path.name.endswith(".gz"):
            return gzip.open(path, "rt", encoding="utf-8")
        return open(path, encoding="utf-8")  # noqa: SIM115

    @staticmethod
    def _iter_json_records(json_path: Path) -> Any:
        """JSONファイルからレコードをストリーミングで読み出すジェネレータ.

        ダンプ形式（1行1レコード）は行単位でパースし、
        それ以外の形式はjson.loadにフォールバックする。
        .json.gzと.jsonの両方に対応。
        """
        file_size = json_path.stat().st_size
        is_gzip = json_path.name.endswith(".gz")
        # 10MB以下（gzipの場合はファイルサイズが圧縮後なので常にストリーミング）
        if not is_gzip and file_size < _STREAMING_THRESHOLD:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            yield from data
            return

        # 大きなファイル/gzipは行単位でストリーミングパース
        opener = gzip.open if is_gzip else open
        with opener(json_path, "rt", encoding="utf-8") as f:  # type: ignore[call-overload]
            for line in f:
                line = line.strip().rstrip(",")
                if not line or line in ("[", "]"):
                    continue
                try:
                    record = json.loads(line)
                    if isinstance(record, dict):
                        yield record
                except json.JSONDecodeError:
                    continue

    def _flush_batch(
        self,
        engine: Any,
        insert_sql: str,
        batch: list[dict[str, Any]],
        table_name: str,
    ) -> int:
        """バッチをまとめてINSERTする.

        まずバッチ全体を一括INSERTし、失敗した場合のみ
        SAVEPOINTを使ったper-recordフォールバックに切り替える。
        """
        # 一括INSERT（高速パス）
        try:
            with engine.begin() as conn:
                conn.execute(text(insert_sql), batch)
            return len(batch)
        except Exception:
            pass

        # フォールバック: per-record INSERT with SAVEPOINT
        inserted = 0
        with engine.begin() as conn:
            for params in batch:
                nested = conn.begin_nested()
                try:
                    conn.execute(text(insert_sql), params)
                    nested.commit()
                    inserted += 1
                except Exception as e:
                    nested.rollback()
                    logger.warning(f"INSERT失敗 ({table_name}): {e}")
        return inserted

    def _download_from_gcs(self, gcs_uri: str) -> Path | None:
        """GCSからダンプをダウンロードしてローカルの一時ディレクトリに保存."""
        gcs = _get_gcs_storage()
        if not gcs:
            self.error("GCSが利用できません")
            return None

        # gs://bucket/database-dumps/2026-03-08_090000 形式をパース
        if not gcs_uri.startswith("gs://"):
            self.error(f"無効なGCS URI: {gcs_uri}")
            return None

        uri_parts = gcs_uri[5:].split("/", 1)
        if len(uri_parts) != 2:
            self.error(f"無効なGCS URI: {gcs_uri}")
            return None

        prefix = uri_parts[1].rstrip("/") + "/"

        self.show_progress(f"GCSからダウンロード中: {gcs_uri}")

        # ファイル一覧を取得
        files = gcs.list_files(prefix=prefix)
        if not files:
            self.error(f"GCSにダンプが見つかりません: {gcs_uri}")
            return None

        # ローカルにダウンロード
        local_dir = DUMPS_BASE_DIR / "gcs_restore_tmp"
        local_dir.mkdir(parents=True, exist_ok=True)

        for gcs_path in files:
            filename = gcs_path.split("/")[-1]
            if not filename:
                continue
            local_path = local_dir / filename
            gcs.download_file(gcs_path, local_path)

        self.show_progress("ダウンロード完了")
        return local_dir

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


class RestoreLatestCommand(Command, BaseCommand):
    """GCSから最新のダンプを取得してリストアするコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """最新ダンプをリストア."""
        force: bool = kwargs.get("force", False)
        gcs = _get_gcs_storage()
        if not gcs:
            self.error("GCSが利用できません。GCS設定を確認してください")
            return

        self.show_progress("GCSから最新のダンプを検索中...")

        # ダンプディレクトリの一覧を取得
        files = gcs.list_files(prefix=GCS_DUMPS_PREFIX)
        if not files:
            self.error("GCSにダンプが見つかりません")
            return

        # _metadata.jsonを含むディレクトリ名を抽出
        dump_dirs: set[str] = set()
        for f in files:
            parts = f.removeprefix(GCS_DUMPS_PREFIX).split("/")
            if len(parts) >= 2 and parts[0]:
                dump_dirs.add(parts[0])

        if not dump_dirs:
            self.error("GCSにダンプが見つかりません")
            return

        # タイムスタンプ順で最新を選択
        latest_dir = sorted(dump_dirs)[-1]
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()
        gcs_uri = f"gs://{settings.gcs_bucket_name}/{GCS_DUMPS_PREFIX}{latest_dir}"

        self.show_progress(f"最新ダンプ: {latest_dir}")

        # RestoreDumpCommandに委譲（confirmスキップ：restore-latestは明示的コマンド）
        restore_cmd = RestoreDumpCommand()
        restore_cmd.execute(
            dump_dir=gcs_uri, truncate=True, force=force, skip_confirm=True
        )


class ListDumpsCommand(Command, BaseCommand):
    """過去のダンプ一覧を表示するコマンド."""

    def execute(self, **kwargs: Any) -> None:
        """ダンプ一覧を表示."""
        show_gcs: bool = kwargs.get("gcs", False)

        # ローカルダンプ一覧
        self._list_local_dumps()

        # GCSダンプ一覧
        if show_gcs:
            self._list_gcs_dumps()

    def _list_local_dumps(self) -> None:
        """ローカルのダンプ一覧を表示."""
        self.show_progress("--- ローカルダンプ ---")
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
        self._display_dump_list(dump_dirs)

    def _list_gcs_dumps(self) -> None:
        """GCS上のダンプ一覧を表示."""
        self.show_progress("")
        self.show_progress("--- GCSダンプ ---")
        gcs = _get_gcs_storage()
        if not gcs:
            self.warning("GCSが利用できません")
            return

        files = gcs.list_files(prefix=GCS_DUMPS_PREFIX)
        if not files:
            self.show_progress("GCSにダンプはまだありません")
            return

        # _metadata.jsonを持つディレクトリを検出
        metadata_files = [f for f in files if f.endswith("_metadata.json")]

        if not metadata_files:
            self.show_progress("GCSにダンプはまだありません")
            return

        self.show_progress(f"ダンプ一覧 ({len(metadata_files)} 件):")
        self.show_progress("-" * 70)

        for metadata_path in sorted(metadata_files, reverse=True):
            dir_name = metadata_path.removeprefix(GCS_DUMPS_PREFIX).split("/")[0]
            try:
                content = gcs.download_content(
                    f"gs://{gcs.bucket_name}/{metadata_path}"
                )
                if content:
                    metadata = json.loads(content)
                    self.show_progress(self._format_dump_info(dir_name, metadata))
                else:
                    self.show_progress(f"  {dir_name}  (メタデータ読み込み失敗)")
            except Exception:
                self.show_progress(f"  {dir_name}  (メタデータ読み込み失敗)")

    @staticmethod
    def _format_dump_info(name: str, metadata: dict[str, Any]) -> str:
        """ダンプのメタデータを1行の表示文字列にフォーマットする."""
        table_count = metadata.get("table_count", "?")
        total_records = metadata.get("total_records", "?")
        revision = metadata.get("alembic_revision", "不明")
        desc = metadata.get("description", "")
        desc_str = f"  [{desc}]" if desc else ""
        return (
            f"  {name}  "
            f"テーブル: {table_count}, "
            f"レコード: {total_records}, "
            f"rev: {revision}{desc_str}"
        )

    def _display_dump_list(self, dump_dirs: list[Path]) -> None:
        """ダンプディレクトリ一覧を整形表示."""
        self.show_progress("-" * 70)
        for dump_dir in dump_dirs:
            metadata_path = dump_dir / "_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, encoding="utf-8") as f:
                    metadata = json.load(f)
                self.show_progress(self._format_dump_info(dump_dir.name, metadata))
            else:
                self.show_progress(f"  {dump_dir.name}  (メタデータなし)")
