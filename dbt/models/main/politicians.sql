{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する政治家VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY POLITICIANS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_politician') }}
)

SELECT
    h.id,
    s.name,
    s.prefecture,
    s.furigana,
    s.district,
    s.profile_page_url
FROM {{ ref('hub_politician') }} h
INNER JOIN latest_sat s
    ON h.POLITICIANS_HK = s.POLITICIANS_HK
    AND s._row_num = 1
