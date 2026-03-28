{#
  カスタムスキーマ名生成マクロ

  dbt_project.yml で指定した +schema をそのまま BigQuery データセット名として使用する。
  カスタムスキーマが未指定の場合はターゲットのデフォルトデータセットを使用。

  これにより以下のマッピングが実現される:
    - staging: sagebase_vault_staging
    - vault: sagebase_vault（ターゲットデフォルト）
    - main: sagebase
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is not none -%}
        {{ custom_schema_name }}
    {%- else -%}
        {{ target.schema }}
    {%- endif -%}
{%- endmacro %}
