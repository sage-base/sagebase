{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する発言VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY CONVERSATIONS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_conversation') }}
)

SELECT
    h.id,
    s.minutes_id,
    s.speaker_id,
    s.speaker_name,
    s.comment,
    s.sequence_number,
    s.chapter_number,
    s.sub_chapter_number,
    s.is_manually_verified
FROM {{ ref('hub_conversation') }} h
INNER JOIN latest_sat s
    ON h.CONVERSATIONS_HK = s.CONVERSATIONS_HK
    AND s._row_num = 1
