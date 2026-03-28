{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する会議VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY MEETINGS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_meeting') }}
)

SELECT
    h.id,
    s.conference_id,
    s.date,
    s.url,
    s.name
FROM {{ ref('hub_meeting') }} h
INNER JOIN latest_sat s
    ON h.MEETINGS_HK = s.MEETINGS_HK
    AND s._row_num = 1
