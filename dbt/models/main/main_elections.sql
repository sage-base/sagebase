{{- config(materialized="table") -}}

-- 選挙メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    governing_body_id,
    term_number,
    election_date,
    election_type,
    created_at,
    updated_at
FROM {{ ref('stg_elections') }}
