{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "speakers") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="SPEAKERS_HK") }},
    {{ automate_dv.hash(["NAME", "TYPE", "POLITICAL_PARTY_NAME", "POSITION", "IS_POLITICIAN", "POLITICIAN_ID", "MATCHING_CONFIDENCE", "MATCHING_REASON", "IS_MANUALLY_VERIFIED", "NAME_YOMI", "GOVERNMENT_OFFICIAL_ID"], alias="SPEAKERS_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    type,
    political_party_name,
    position,
    is_politician,
    politician_id,
    matching_confidence,
    matching_reason,
    is_manually_verified,
    name_yomi,
    government_official_id,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
