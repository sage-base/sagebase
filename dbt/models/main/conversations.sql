{{- config(materialized="table") -}}

-- 発言メインビュー: sourceスキーマと一致するビジネスビュー
SELECT
    id,
    minutes_id,
    speaker_id,
    speaker_name,
    comment,
    sequence_number,
    chapter_number,
    sub_chapter_number,
    is_manually_verified,
    created_at,
    updated_at
FROM {{ ref('stg_conversations') }}
