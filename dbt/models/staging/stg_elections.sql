{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "elections") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="ELECTIONS_HK") }},
    {{ automate_dv.hash(["GOVERNING_BODY_ID", "TERM_NUMBER", "ELECTION_DATE", "ELECTION_TYPE"], alias="ELECTIONS_HASHDIFF", is_hashdiff=true) }},
    id,
    governing_body_id,
    term_number,
    election_date,
    election_type,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
