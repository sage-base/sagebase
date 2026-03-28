{{- config(materialized="table") -}}

-- 選挙結果メンバーメインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    election_id,
    politician_id,
    result,
    votes,
    rank,
    created_at,
    updated_at
FROM {{ ref('stg_election_members') }}
