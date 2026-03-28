{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する選挙VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY ELECTIONS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_election') }}
)

SELECT
    h.id,
    s.governing_body_id,
    s.term_number,
    s.election_date,
    s.election_type
FROM {{ ref('hub_election') }} h
INNER JOIN latest_sat s
    ON h.ELECTIONS_HK = s.ELECTIONS_HK
    AND s._row_num = 1
