{{- config(materialized="table") -}}

-- 議案賛否（個人）メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    proposal_id,
    politician_id,
    approve,
    parliamentary_group_id,
    source_type,
    source_group_judge_id,
    is_defection,
    created_at,
    updated_at
FROM {{ ref('stg_proposal_judges') }}
