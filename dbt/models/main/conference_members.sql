{{- config(materialized="table") -}}

-- 会議体メンバーメインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    politician_id,
    conference_id,
    start_date,
    end_date,
    role,
    is_manually_verified,
    created_at,
    updated_at
FROM {{ ref('stg_conference_members') }}
