{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する議事録VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY MINUTES_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_minutes') }}
)

SELECT
    h.id,
    s.meeting_id,
    s.url,
    s.processed_at
FROM {{ ref('hub_minutes') }} h
INNER JOIN latest_sat s
    ON h.MINUTES_HK = s.MINUTES_HK
    AND s._row_num = 1
