{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposal_judge_parliamentary_groups") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSAL_JUDGE_PARLIAMENTARY_GROUPS_HK") }},
    {{ automate_dv.hash(["JUDGE_ID", "PARLIAMENTARY_GROUP_ID"], alias="PROPOSAL_JUDGE_PARLIAMENTARY_GROUPS_HASHDIFF", is_hashdiff=true) }},
    id,
    judge_id,
    parliamentary_group_id,
    created_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
