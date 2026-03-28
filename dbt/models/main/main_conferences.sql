{{- config(materialized="table") -}}

-- 会議体メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    governing_body_id,
    term,
    election_id,
    created_at,
    updated_at
FROM {{ ref('stg_conferences') }}
