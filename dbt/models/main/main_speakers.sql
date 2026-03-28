{{- config(materialized="table") -}}

-- 発言者メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    type,
    political_party_name,
    position,
    is_politician,
    politician_id,
    matching_confidence,
    matching_reason,
    is_manually_verified,
    name_yomi,
    government_official_id,
    created_at,
    updated_at
FROM {{ ref('stg_speakers') }}
