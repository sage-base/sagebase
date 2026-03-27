{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "conference_members") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="CONFERENCE_MEMBERS_HK") }},
    {{ automate_dv.hash(["POLITICIAN_ID", "CONFERENCE_ID", "START_DATE", "END_DATE", "ROLE", "IS_MANUALLY_VERIFIED"], alias="CONFERENCE_MEMBERS_HASHDIFF", is_hashdiff=true) }},
    id,
    politician_id,
    conference_id,
    start_date,
    end_date,
    role,
    is_manually_verified,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
