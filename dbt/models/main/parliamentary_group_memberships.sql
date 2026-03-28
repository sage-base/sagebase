{{- config(materialized="view") -}}

{# Vault Link+Satelliteから最新状態を射影する議員団所属VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY LINK_PG_MEMBERSHIP_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_pg_membership') }}
)

SELECT
    h_politician.id AS politician_id,
    h_pg.id AS parliamentary_group_id,
    s.start_date,
    s.end_date,
    s.role,
    s.is_manually_verified
FROM {{ ref('link_pg_membership') }} l
INNER JOIN latest_sat s
    ON l.LINK_PG_MEMBERSHIP_HK = s.LINK_PG_MEMBERSHIP_HK
    AND s._row_num = 1
INNER JOIN {{ ref('hub_parliamentary_group') }} h_pg
    ON l.PARLIAMENTARY_GROUPS_HK = h_pg.PARLIAMENTARY_GROUPS_HK
INNER JOIN {{ ref('hub_politician') }} h_politician
    ON l.POLITICIANS_HK = h_politician.POLITICIANS_HK
