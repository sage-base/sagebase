{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "politicians") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="POLITICIANS_HK") }},
    {{ automate_dv.hash(["NAME", "PREFECTURE", "FURIGANA", "DISTRICT", "PROFILE_PAGE_URL"], alias="POLITICIANS_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    prefecture,
    furigana,
    district,
    profile_page_url,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
