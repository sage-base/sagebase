{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "proposal_judge_politicians") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PROPOSAL_JUDGE_POLITICIANS_HK") }},
    {{ automate_dv.hash(["JUDGE_ID", "POLITICIAN_ID"], alias="PROPOSAL_JUDGE_POLITICIANS_HASHDIFF", is_hashdiff=true) }},
    id,
    judge_id,
    politician_id,
    created_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
