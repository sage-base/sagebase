{{- config(materialized="table") -}}

-- 議案メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    title,
    detail_url,
    status_url,
    meeting_id,
    votes_url,
    conference_id,
    proposal_category,
    proposal_type,
    governing_body_id,
    session_number,
    proposal_number,
    external_id,
    deliberation_status,
    deliberation_result,
    submitted_date,
    voted_date,
    created_at,
    updated_at
FROM {{ ref('stg_proposals') }}
