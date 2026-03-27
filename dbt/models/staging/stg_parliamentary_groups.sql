{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "parliamentary_groups") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PARLIAMENTARY_GROUPS_HK") }},
    {{ automate_dv.hash(["NAME", "GOVERNING_BODY_ID", "URL", "DESCRIPTION", "IS_ACTIVE", "CHAMBER", "START_DATE", "END_DATE"], alias="PARLIAMENTARY_GROUPS_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    governing_body_id,
    url,
    description,
    is_active,
    chamber,
    start_date,
    end_date,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
