{{- config(materialized="table") -}}

-- 会議メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    conference_id,
    date,
    url,
    name,
    created_at,
    updated_at
FROM {{ ref('stg_meetings') }}
