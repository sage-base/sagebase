{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "conferences") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="CONFERENCES_HK") }},
    {{ automate_dv.hash(["NAME", "GOVERNING_BODY_ID", "TERM", "ELECTION_ID"], alias="CONFERENCES_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    governing_body_id,
    term,
    election_id,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
