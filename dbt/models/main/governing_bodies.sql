{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する開催主体VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY GOVERNING_BODIES_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_governing_body') }}
)

SELECT
    h.id,
    s.name,
    s.organization_code,
    s.organization_type,
    s.prefecture
FROM {{ ref('hub_governing_body') }} h
INNER JOIN latest_sat s
    ON h.GOVERNING_BODIES_HK = s.GOVERNING_BODIES_HK
    AND s._row_num = 1
