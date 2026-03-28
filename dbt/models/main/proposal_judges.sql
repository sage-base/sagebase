{{- config(materialized="view") -}}

{# Vault Link+Satelliteから最新状態を射影する議案賛否VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY LINK_PROPOSAL_JUDGE_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_proposal_judge') }}
)

SELECT
    h_proposal.id AS proposal_id,
    h_politician.id AS politician_id,
    s.approve,
    s.parliamentary_group_id,
    s.source_type,
    s.source_group_judge_id,
    s.is_defection
FROM {{ ref('link_proposal_judge') }} l
INNER JOIN latest_sat s
    ON l.LINK_PROPOSAL_JUDGE_HK = s.LINK_PROPOSAL_JUDGE_HK
    AND s._row_num = 1
INNER JOIN {{ ref('hub_proposal') }} h_proposal
    ON l.PROPOSALS_HK = h_proposal.PROPOSALS_HK
INNER JOIN {{ ref('hub_politician') }} h_politician
    ON l.POLITICIANS_HK = h_politician.POLITICIANS_HK
