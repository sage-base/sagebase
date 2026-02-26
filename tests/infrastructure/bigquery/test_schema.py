"""BigQuery Gold Layerスキーマ定義のテスト."""

import pytest

from src.infrastructure.bigquery.schema import (
    GOLD_LAYER_TABLES,
    PG_TO_BQ_TYPE_MAP,
    BQColumnDef,
    BQTableDef,
    to_bigquery_schema,
)


class TestGoldLayerTables:
    """GOLD_LAYER_TABLESの定義テスト."""

    def test_table_count_is_21(self) -> None:
        assert len(GOLD_LAYER_TABLES) == 21

    def test_all_table_ids_are_unique(self) -> None:
        table_ids = [t.table_id for t in GOLD_LAYER_TABLES]
        assert len(table_ids) == len(set(table_ids))

    def test_all_tables_have_id_column(self) -> None:
        for table_def in GOLD_LAYER_TABLES:
            col_names = [c.name for c in table_def.columns]
            assert "id" in col_names, f"{table_def.table_id} に id カラムがありません"

    def test_all_tables_have_created_at_column(self) -> None:
        for table_def in GOLD_LAYER_TABLES:
            col_names = [c.name for c in table_def.columns]
            assert "created_at" in col_names, (
                f"{table_def.table_id} に created_at カラムがありません"
            )

    def test_id_column_is_required(self) -> None:
        for table_def in GOLD_LAYER_TABLES:
            id_col = next(c for c in table_def.columns if c.name == "id")
            assert id_col.mode == "REQUIRED", (
                f"{table_def.table_id} の id カラムが REQUIRED ではありません"
            )

    def test_all_tables_have_description(self) -> None:
        for table_def in GOLD_LAYER_TABLES:
            assert table_def.description, (
                f"{table_def.table_id} に description がありません"
            )

    def test_expected_table_ids(self) -> None:
        expected = {
            "politicians",
            "political_parties",
            "elections",
            "election_members",
            "governing_bodies",
            "conferences",
            "conference_members",
            "parliamentary_groups",
            "parliamentary_group_parties",
            "parliamentary_group_memberships",
            "meetings",
            "minutes",
            "conversations",
            "speakers",
            "proposals",
            "proposal_submitters",
            "proposal_deliberations",
            "proposal_judges",
            "proposal_parliamentary_group_judges",
            "proposal_judge_parliamentary_groups",
            "proposal_judge_politicians",
        }
        actual = {t.table_id for t in GOLD_LAYER_TABLES}
        assert actual == expected


class TestBQColumnDef:
    """BQColumnDefのテスト."""

    def test_default_mode_is_nullable(self) -> None:
        col = BQColumnDef("test", "STRING")
        assert col.mode == "NULLABLE"

    def test_frozen_dataclass(self) -> None:
        col = BQColumnDef("test", "STRING")
        with pytest.raises(AttributeError):
            col.name = "other"  # type: ignore[misc]


class TestBQTableDef:
    """BQTableDefのテスト."""

    def test_frozen_dataclass(self) -> None:
        table = BQTableDef("test", "desc", ())
        with pytest.raises(AttributeError):
            table.table_id = "other"  # type: ignore[misc]


class TestPgToBqTypeMap:
    """型マッピングのテスト."""

    def test_basic_type_mappings(self) -> None:
        assert PG_TO_BQ_TYPE_MAP["SERIAL"] == "INT64"
        assert PG_TO_BQ_TYPE_MAP["INTEGER"] == "INT64"
        assert PG_TO_BQ_TYPE_MAP["VARCHAR"] == "STRING"
        assert PG_TO_BQ_TYPE_MAP["TEXT"] == "STRING"
        assert PG_TO_BQ_TYPE_MAP["BOOLEAN"] == "BOOL"
        assert PG_TO_BQ_TYPE_MAP["DATE"] == "DATE"
        assert PG_TO_BQ_TYPE_MAP["TIMESTAMP"] == "TIMESTAMP"
        assert PG_TO_BQ_TYPE_MAP["JSONB"] == "JSON"
        assert PG_TO_BQ_TYPE_MAP["DECIMAL"] == "NUMERIC"
        assert PG_TO_BQ_TYPE_MAP["FLOAT"] == "FLOAT64"
        assert PG_TO_BQ_TYPE_MAP["UUID"] == "STRING"


class TestToBigquerySchema:
    """to_bigquery_schema変換テスト."""

    def test_converts_columns_to_schema_fields(self) -> None:
        table_def = BQTableDef(
            table_id="test_table",
            description="テスト",
            columns=(
                BQColumnDef("id", "INT64", "REQUIRED", "ID"),
                BQColumnDef("name", "STRING", description="名前"),
            ),
        )
        result = to_bigquery_schema(table_def)

        assert len(result) == 2
        assert result[0].name == "id"
        assert result[0].field_type == "INT64"
        assert result[0].mode == "REQUIRED"
        assert result[0].description == "ID"
        assert result[1].name == "name"
        assert result[1].field_type == "STRING"
        assert result[1].mode == "NULLABLE"
        assert result[1].description == "名前"
