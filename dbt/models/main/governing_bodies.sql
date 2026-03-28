{{- config(materialized="table") -}}

-- 開催主体メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    organization_code,
    organization_type,
    prefecture,
    created_at,
    updated_at
FROM {{ ref('stg_governing_bodies') }}
