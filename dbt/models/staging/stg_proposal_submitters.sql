{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposal_submitters") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSAL_SUBMITTERS_HK") }},
    {{ automate_dv.hash("PROPOSAL_ID", alias="PROPOSALS_HK") }},
    {{ automate_dv.hash("POLITICIAN_ID", alias="POLITICIANS_HK") }},
    {{ automate_dv.hash(["PROPOSAL_ID", "POLITICIAN_ID"], alias="LINK_PROPOSAL_SUBMITTER_HK") }},
    {{ automate_dv.hash(["PROPOSAL_ID", "SUBMITTER_TYPE", "POLITICIAN_ID", "PARLIAMENTARY_GROUP_ID", "CONFERENCE_ID", "RAW_NAME", "IS_REPRESENTATIVE", "DISPLAY_ORDER"], alias="PROPOSAL_SUBMITTERS_HASHDIFF", is_hashdiff=true) }},
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
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
