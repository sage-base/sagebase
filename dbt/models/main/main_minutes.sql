{{- config(materialized="table") -}}

-- 議事録メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    meeting_id,
    url,
    processed_at,
    created_at,
    updated_at
FROM {{ ref('stg_minutes') }}
