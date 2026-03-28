{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する議員団VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY PARLIAMENTARY_GROUPS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_parliamentary_group') }}
)

SELECT
    h.id,
    s.name,
    s.governing_body_id,
    s.url,
    s.description,
    s.is_active,
    s.chamber,
    s.start_date,
    s.end_date
FROM {{ ref('hub_parliamentary_group') }} h
INNER JOIN latest_sat s
    ON h.PARLIAMENTARY_GROUPS_HK = s.PARLIAMENTARY_GROUPS_HK
    AND s._row_num = 1
