{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposal_parliamentary_group_judges") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSAL_PARLIAMENTARY_GROUP_JUDGES_HK") }},
    {{ automate_dv.hash(["PROPOSAL_ID", "JUDGMENT", "MEMBER_COUNT", "NOTE", "JUDGE_TYPE"], alias="PROPOSAL_PARLIAMENTARY_GROUP_JUDGES_HASHDIFF", is_hashdiff=true) }},
    id,
    proposal_id,
    judgment,
    member_count,
    note,
    judge_type,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
