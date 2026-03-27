{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposal_deliberations") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSAL_DELIBERATIONS_HK") }},
    {{ automate_dv.hash(["PROPOSAL_ID", "CONFERENCE_ID", "MEETING_ID", "STAGE"], alias="PROPOSAL_DELIBERATIONS_HASHDIFF", is_hashdiff=true) }},
    id,
    proposal_id,
    conference_id,
    meeting_id,
    stage,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
