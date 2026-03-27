{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "government_officials") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="GOVERNMENT_OFFICIALS_HK") }},
    {{ automate_dv.hash(["NAME"], alias="GOVERNMENT_OFFICIALS_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
