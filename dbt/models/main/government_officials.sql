{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する政府関係者VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY GOVERNMENT_OFFICIALS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_government_official') }}
)

SELECT
    h.id,
    s.name
FROM {{ ref('hub_government_official') }} h
INNER JOIN latest_sat s
    ON h.GOVERNMENT_OFFICIALS_HK = s.GOVERNMENT_OFFICIALS_HK
    AND s._row_num = 1
