{{- config(materialized="table") -}}

-- 議案提出者メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    proposal_id,
    submitter_type,
    politician_id,
    parliamentary_group_id,
    conference_id,
    raw_name,
    is_representative,
    display_order,
    created_at,
    updated_at
FROM {{ ref('stg_proposal_submitters') }}
