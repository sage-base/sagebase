{{- config(materialized="view") -}}

{# Vault Link+Satelliteから最新状態を射影する会議体メンバーVIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY LINK_CONFERENCE_MEMBER_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_conference_member') }}
)

SELECT
    h_politician.id AS politician_id,
    h_conference.id AS conference_id,
    s.start_date,
    s.end_date,
    s.role,
    s.is_manually_verified
FROM {{ ref('link_conference_member') }} l
INNER JOIN latest_sat s
    ON l.LINK_CONFERENCE_MEMBER_HK = s.LINK_CONFERENCE_MEMBER_HK
    AND s._row_num = 1
INNER JOIN {{ ref('hub_conference') }} h_conference
    ON l.CONFERENCES_HK = h_conference.CONFERENCES_HK
INNER JOIN {{ ref('hub_politician') }} h_politician
    ON l.POLITICIANS_HK = h_politician.POLITICIANS_HK
