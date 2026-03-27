{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "election_members") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="ELECTION_MEMBERS_HK") }},
    {{ automate_dv.hash(["ELECTION_ID", "POLITICIAN_ID", "RESULT", "VOTES", "RANK"], alias="ELECTION_MEMBERS_HASHDIFF", is_hashdiff=true) }},
    id,
    election_id,
    politician_id,
    result,
    votes,
    rank,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
