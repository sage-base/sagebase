{{- config(materialized="view") -}}

{# Vault Link+Satelliteから最新状態を射影する選挙候補者VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY LINK_ELECTION_MEMBER_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_election_member') }}
)

SELECT
    h_election.id AS election_id,
    h_politician.id AS politician_id,
    s.result,
    s.votes,
    s.rank
FROM {{ ref('link_election_member') }} l
INNER JOIN latest_sat s
    ON l.LINK_ELECTION_MEMBER_HK = s.LINK_ELECTION_MEMBER_HK
    AND s._row_num = 1
INNER JOIN {{ ref('hub_election') }} h_election
    ON l.ELECTIONS_HK = h_election.ELECTIONS_HK
INNER JOIN {{ ref('hub_politician') }} h_politician
    ON l.POLITICIANS_HK = h_politician.POLITICIANS_HK
