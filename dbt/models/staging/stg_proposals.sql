{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposals") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSALS_HK") }},
    {{ automate_dv.hash(["TITLE", "DETAIL_URL", "STATUS_URL", "MEETING_ID", "VOTES_URL", "CONFERENCE_ID", "PROPOSAL_CATEGORY", "PROPOSAL_TYPE", "GOVERNING_BODY_ID", "SESSION_NUMBER", "PROPOSAL_NUMBER", "EXTERNAL_ID", "DELIBERATION_STATUS", "DELIBERATION_RESULT", "SUBMITTED_DATE", "VOTED_DATE"], alias="PROPOSALS_HASHDIFF", is_hashdiff=true) }},
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
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
