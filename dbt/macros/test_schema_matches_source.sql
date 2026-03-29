{#
  カスタムジェネリックテスト: Main VIEWのカラムがsourceテーブルのカラムと一致することを検証

  使い方:
    schema.ymlで以下のように指定:
      tests:
        - schema_matches_source:
            source_table: politicians

  検証内容:
    1. sourceテーブルの全カラムがMain VIEWに存在すること（欠落カラムがあればSQLエラー）
    2. Main VIEWのカラム順がsourceテーブルのカラム順と一致すること（EXCEPT句で差異検出）

  除外対象:
    - Vault固有カラム（hash key, hashdiff, load_date, record_source等）はsourceに含まれないため対象外
#}

{% test schema_matches_source(model, source_table) %}

{# graph.sourcesはexecuteフェーズでのみ確実に利用可能。
   dbt Fusion 2.0ではdbt run時にもテストSQLをコンパイルするため、
   executeガードでコンパイルフェーズをスキップする。 #}
{% if execute %}

{# sources.ymlからソーステーブルのカラム定義を取得 #}
{% set source_node_id = 'source.sagebase_dbt.sagebase_source.' ~ source_table %}
{% set src_node = graph.sources.get(source_node_id) %}

{% if not src_node %}
  {{ exceptions.raise_compiler_error(
    "ソーステーブル '" ~ source_table ~ "' がsources.ymlに見つかりません。"
    ~ " source_node_id: " ~ source_node_id
  ) }}
{% endif %}

{% set expected_columns = src_node.columns.keys() | list %}

{% if expected_columns | length == 0 %}
  {{ exceptions.raise_compiler_error(
    "ソーステーブル '" ~ source_table ~ "' にカラム定義がありません。sources.ymlにcolumnsを定義してください。"
  ) }}
{% endif %}

{#
  検証クエリ:
  1. sourceの全カラムをMain VIEWからSELECTして存在確認（コンパイル時/実行時にカラム不在ならエラー）
  2. カラム順の一致をORDINAL_POSITIONで検証（差異があれば行を返す = テスト失敗）
#}

WITH source_expected_columns AS (
    {# sourceカラム定義に基づく期待値（順序付き） #}
    {% for col_name in expected_columns %}
    SELECT '{{ col_name }}' AS column_name, {{ loop.index }} AS expected_position
    {% if not loop.last %}UNION ALL{% endif %}
    {% endfor %}
),

model_column_check AS (
    {# Main VIEWからsourceの全カラムをSELECT — 欠落カラムがあればSQLエラーになる #}
    SELECT
        {% for col_name in expected_columns %}
        {{ col_name }}{% if not loop.last %},{% endif %}
        {% endfor %}
    FROM {{ model }}
    WHERE FALSE
),

model_actual_columns AS (
    {# INFORMATION_SCHEMAからMain VIEWの実際のカラム順序を取得 #}
    SELECT
        column_name,
        ordinal_position
    FROM `{{ model.database }}`.`{{ model.schema }}`.INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = '{{ model.identifier }}'
),

column_order_diff AS (
    {# カラム順序の差異を検出 #}
    SELECT
        e.column_name,
        e.expected_position,
        a.ordinal_position AS actual_position,
        'カラム順序不一致' AS error_type
    FROM source_expected_columns e
    LEFT JOIN model_actual_columns a
        ON LOWER(e.column_name) = LOWER(a.column_name)
    WHERE a.ordinal_position IS NULL
       OR e.expected_position != a.ordinal_position
),

extra_columns_in_model AS (
    {# Main VIEWにあってsourceにないカラムを検出 #}
    SELECT
        a.column_name,
        0 AS expected_position,
        a.ordinal_position AS actual_position,
        'Main VIEWに余分なカラム' AS error_type
    FROM model_actual_columns a
    LEFT JOIN source_expected_columns e
        ON LOWER(a.column_name) = LOWER(e.column_name)
    WHERE e.column_name IS NULL
)

SELECT * FROM column_order_diff
UNION ALL
SELECT * FROM extra_columns_in_model

{% else %}

{# コンパイルフェーズ（dbt run等）ではダミークエリを返す #}
SELECT CAST(NULL AS STRING) AS column_name, 0 AS expected_position, 0 AS actual_position, '' AS error_type
WHERE FALSE

{% endif %}

{% endtest %}
