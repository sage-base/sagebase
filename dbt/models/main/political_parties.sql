{{- config(materialized="table") -}}

-- 政党メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    members_list_url,
    created_at,
    updated_at
FROM {{ ref('stg_political_parties') }}
