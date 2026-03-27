{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "minutes") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="MINUTES_HK") }},
    {{ automate_dv.hash("MEETING_ID", alias="MEETINGS_HK") }},
    {{ automate_dv.hash(["MEETING_ID", "ID"], alias="LINK_MEETING_MINUTES_HK") }},
    {{ automate_dv.hash(["MEETING_ID", "URL", "PROCESSED_AT"], alias="MINUTES_HASHDIFF", is_hashdiff=true) }},
    id,
    meeting_id,
    url,
    processed_at,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
