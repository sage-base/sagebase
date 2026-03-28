{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する発言者VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY SPEAKERS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_speaker') }}
)

SELECT
    h.id,
    s.name,
    s.type,
    s.political_party_name,
    s.position,
    s.is_politician,
    s.politician_id,
    s.matching_confidence,
    s.matching_reason,
    s.is_manually_verified,
    s.name_yomi,
    s.government_official_id
FROM {{ ref('hub_speaker') }} h
INNER JOIN latest_sat s
    ON h.SPEAKERS_HK = s.SPEAKERS_HK
    AND s._row_num = 1
