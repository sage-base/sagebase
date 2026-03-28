{{- config(materialized="view") -}}

{# Vault Link+Satelliteから最新状態を射影する議案提出者VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY LINK_PROPOSAL_SUBMITTER_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_proposal_submitter') }}
)

SELECT
    h_proposal.id AS proposal_id,
    h_politician.id AS politician_id,
    s.submitter_type,
    s.parliamentary_group_id,
    s.conference_id,
    s.raw_name,
    s.is_representative,
    s.display_order
FROM {{ ref('link_proposal_submitter') }} l
INNER JOIN latest_sat s
    ON l.LINK_PROPOSAL_SUBMITTER_HK = s.LINK_PROPOSAL_SUBMITTER_HK
    AND s._row_num = 1
INNER JOIN {{ ref('hub_proposal') }} h_proposal
    ON l.PROPOSALS_HK = h_proposal.PROPOSALS_HK
INNER JOIN {{ ref('hub_politician') }} h_politician
    ON l.POLITICIANS_HK = h_politician.POLITICIANS_HK
