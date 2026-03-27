{{- config(materialized="view") -}}

WITH source AS (
    SELECT * FROM {{ source("sagebase_source", "conversations") }}
)

SELECT
    {{ automate_dv.hash("ID", alias="CONVERSATIONS_HK") }},
    {{ automate_dv.hash("MINUTES_ID", alias="MINUTES_HK") }},
    {{ automate_dv.hash("SPEAKER_ID", alias="SPEAKERS_HK") }},
    {{ automate_dv.hash(["ID", "SPEAKER_ID"], alias="LINK_CONVERSATION_SPEAKER_HK") }},
    {{ automate_dv.hash(["MINUTES_ID", "SPEAKER_ID", "SPEAKER_NAME", "COMMENT", "SEQUENCE_NUMBER", "CHAPTER_NUMBER", "SUB_CHAPTER_NUMBER", "IS_MANUALLY_VERIFIED"], alias="CONVERSATIONS_HASHDIFF", is_hashdiff=true) }},
    id,
    minutes_id,
    speaker_id,
    speaker_name,
    comment,
    sequence_number,
    chapter_number,
    sub_chapter_number,
    is_manually_verified,
    created_at,
    updated_at,
    'sagebase_source' AS record_source,
    CURRENT_TIMESTAMP() AS load_date
FROM source
