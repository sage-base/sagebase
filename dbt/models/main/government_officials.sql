{{- config(materialized="table") -}}

-- 政府関係者マスタメインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    created_at,
    updated_at
FROM {{ ref('stg_government_officials') }}
