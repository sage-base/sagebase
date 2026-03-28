{{- config(materialized="table") -}}

-- 政治家メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    name,
    prefecture,
    furigana,
    district,
    profile_page_url,
    created_at,
    updated_at
FROM {{ ref('stg_politicians') }}
