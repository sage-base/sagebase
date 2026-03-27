{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "parliamentary_group_memberships") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="PARLIAMENTARY_GROUP_MEMBERSHIPS_HK") }},
    {{ automate_dv.hash("PARLIAMENTARY_GROUP_ID", alias="PARLIAMENTARY_GROUPS_HK") }},
    {{ automate_dv.hash("POLITICIAN_ID", alias="POLITICIANS_HK") }},
    {{ automate_dv.hash(["PARLIAMENTARY_GROUP_ID", "POLITICIAN_ID"], alias="LINK_PG_MEMBERSHIP_HK") }},
    {{ automate_dv.hash(["POLITICIAN_ID", "PARLIAMENTARY_GROUP_ID", "START_DATE", "END_DATE", "ROLE", "IS_MANUALLY_VERIFIED"], alias="PARLIAMENTARY_GROUP_MEMBERSHIPS_HASHDIFF", is_hashdiff=true) }},
    id,
    politician_id,
    parliamentary_group_id,
    start_date,
    end_date,
    role,
    is_manually_verified,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
