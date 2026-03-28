{{- config(materialized="table") -}}

-- 議員団所属履歴メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    politician_id,
    parliamentary_group_id,
    start_date,
    end_date,
    role,
    is_manually_verified,
    created_at,
    updated_at
FROM {{ ref('stg_parliamentary_group_memberships') }}
