{#
  カスタムジェネリックテスト: Main VIEWのカラムがsourceテーブルのカラムと一致することを検証

  使い方:
    schema.ymlで以下のように指定:
      tests:
        - schema_matches_source:
            arguments:
              source_table: politicians

  検証内容:
    1. sourceテーブルの全カラムがMain VIEWに存在すること
    2. Main VIEWのカラム順がsourceテーブルのカラム順と一致すること
    3. Main VIEWに余分なカラムがないこと

  実装:
    INFORMATION_SCHEMAから両テーブルの実カラム情報を取得して比較する。
    dbt Fusion 2.0互換のため、source()の属性アクセスではなくvar/env_varで
    プロジェクトID・データセット名を解決する。
#}

{% test schema_matches_source(model, source_table) %}

{# ソーステーブルのプロジェクト・データセットをsources.ymlの定義から取得 #}
{% set src_ref = source('sagebase_source', source_table) %}
{% set source_dataset = 'sagebase_source' %}

WITH source_columns AS (
    {# ソーステーブルの実際のカラム情報をINFORMATION_SCHEMAから取得 #}
    SELECT
        column_name,
        ordinal_position
    FROM `{{ target.database }}`.`{{ source_dataset }}`.INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = '{{ source_table }}'
),

model_columns AS (
    {# Main VIEWの実際のカラム情報をINFORMATION_SCHEMAから取得 #}
    SELECT
        column_name,
        ordinal_position
    FROM `{{ target.database }}`.`{{ model.schema }}`.INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = '{{ model.identifier }}'
),

column_order_diff AS (
    {# カラム順序の差異を検出 #}
    SELECT
        s.column_name,
        s.ordinal_position AS expected_position,
        m.ordinal_position AS actual_position,
        'カラム順序不一致' AS error_type
    FROM source_columns s
    LEFT JOIN model_columns m
        ON LOWER(s.column_name) = LOWER(m.column_name)
    WHERE m.ordinal_position IS NULL
       OR s.ordinal_position != m.ordinal_position
),

extra_columns_in_model AS (
    {# Main VIEWにあってsourceにないカラムを検出 #}
    SELECT
        m.column_name,
        0 AS expected_position,
        m.ordinal_position AS actual_position,
        'Main VIEWに余分なカラム' AS error_type
    FROM model_columns m
    LEFT JOIN source_columns s
        ON LOWER(m.column_name) = LOWER(s.column_name)
    WHERE s.column_name IS NULL
)

SELECT * FROM column_order_diff
UNION ALL
SELECT * FROM extra_columns_in_model

{% endtest %}
