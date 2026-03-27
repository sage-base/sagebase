{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "political_parties") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="POLITICAL_PARTIES_HK") }},
    {{ automate_dv.hash(["NAME", "MEMBERS_LIST_URL"], alias="POLITICAL_PARTIES_HASHDIFF", is_hashdiff=true) }},
    id,
    name,
    members_list_url,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
