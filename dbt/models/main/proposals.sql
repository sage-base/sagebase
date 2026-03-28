{{- config(materialized="view") -}}

{# Vault Satelliteから最新状態を射影する議案VIEW #}

WITH latest_sat AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY PROPOSALS_HK ORDER BY load_date DESC) AS _row_num
    FROM {{ ref('sat_proposal') }}
)

SELECT
    h.id,
    s.title,
    s.detail_url,
    s.status_url,
    s.meeting_id,
    s.votes_url,
    s.conference_id,
    s.proposal_category,
    s.proposal_type,
    s.governing_body_id,
    s.session_number,
    s.proposal_number,
    s.external_id,
    s.deliberation_status,
    s.deliberation_result,
    s.submitted_date,
    s.voted_date
FROM {{ ref('hub_proposal') }} h
INNER JOIN latest_sat s
    ON h.PROPOSALS_HK = s.PROPOSALS_HK
    AND s._row_num = 1
