{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "parliamentary_group_parties") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PARLIAMENTARY_GROUP_PARTIES_HK") }},
    {{ automate_dv.hash(["PARLIAMENTARY_GROUP_ID", "POLITICAL_PARTY_ID", "IS_PRIMARY"], alias="PARLIAMENTARY_GROUP_PARTIES_HASHDIFF", is_hashdiff=true) }},
    id,
    parliamentary_group_id,
    political_party_id,
    is_primary,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
