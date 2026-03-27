{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "meetings") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="MEETINGS_HK") }},
    {{ automate_dv.hash(["CONFERENCE_ID", "DATE", "URL", "NAME"], alias="MEETINGS_HASHDIFF", is_hashdiff=true) }},
    id,
    conference_id,
    date,
    url,
    name,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
