{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposal_judges") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSAL_JUDGES_HK") }},
    {{ automate_dv.hash(["PROPOSAL_ID", "POLITICIAN_ID", "APPROVE", "PARLIAMENTARY_GROUP_ID", "SOURCE_TYPE", "SOURCE_GROUP_JUDGE_ID", "IS_DEFECTION"], alias="PROPOSAL_JUDGES_HASHDIFF", is_hashdiff=true) }},
    id,
    proposal_id,
    politician_id,
    approve,
    parliamentary_group_id,
    source_type,
    source_group_judge_id,
    is_defection,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
