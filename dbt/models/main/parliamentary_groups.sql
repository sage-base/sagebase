{{- config(materialized="table") -}}

-- 議員団（会派）メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    governing_body_id,
    url,
    description,
    is_active,
    chamber,
    start_date,
    end_date,
    created_at,
    updated_at
FROM {{ ref('stg_parliamentary_groups') }}
