{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する政党VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY POLITICAL_PARTIES_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_political_party') }}
)

SELECT
    h.id,
    s.name,
    s.members_list_url
FROM {{ ref('hub_political_party') }} h
INNER JOIN latest_sat s
    ON h.POLITICAL_PARTIES_HK = s.POLITICAL_PARTIES_HK
    AND s._row_num = 1
