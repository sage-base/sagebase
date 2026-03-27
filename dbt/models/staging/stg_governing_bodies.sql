{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "governing_bodies") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="GOVERNING_BODIES_HK") }},
    {{ automate_dv.hash(["NAME", "ORGANIZATION_CODE", "ORGANIZATION_TYPE", "PREFECTURE"], alias="GOVERNING_BODIES_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    organization_code,
    organization_type,
    prefecture,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
