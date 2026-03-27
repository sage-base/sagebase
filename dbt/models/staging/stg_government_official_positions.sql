{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "government_official_positions") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="GOVERNMENT_OFFICIAL_POSITIONS_HK") }},
    {{ automate_dv.hash(["GOVERNMENT_OFFICIAL_ID", "ORGANIZATION", "POSITION", "START_DATE", "END_DATE", "SOURCE_NOTE"], alias="GOVERNMENT_OFFICIAL_POSITIONS_HASHDIFF", is_hashdiff=true) }},
    id,
    government_official_id,
    organization,
    position,
    start_date,
    end_date,
    source_note,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
