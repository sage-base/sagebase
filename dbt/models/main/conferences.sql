{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する会議体VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY CONFERENCES_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_conference') }}
)

SELECT
    h.id,
    s.name,
    s.governing_body_id,
    s.term,
    s.election_id
FROM {{ ref('hub_conference') }} h
INNER JOIN latest_sat s
    ON h.CONFERENCES_HK = s.CONFERENCES_HK
    AND s._row_num = 1
