-- マイグレーション: 040_add_extraction_log_fields_to_extracted_members.sql
-- 目的: 抽出メンバーテーブルに手動検証フィールドと抽出ログ参照を追加
-- 対象: extracted_conference_members, extracted_parliamentary_group_members
-- 関連Issue: #867 [PBI-007] ConferenceMember/ParliamentaryGroupMember処理への抽出ログ統合

-- extracted_conference_members テーブル
ALTER TABLE extracted_conference_members
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- extracted_parliamentary_group_members テーブル
ALTER TABLE extracted_parliamentary_group_members
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- インデックスの作成（is_manually_verifiedでフィルタリングするクエリを高速化）
CREATE INDEX idx_extracted_conference_members_manually_verified ON extracted_conference_members(is_manually_verified);
CREATE INDEX idx_extracted_parliamentary_group_members_manually_verified ON extracted_parliamentary_group_members(is_manually_verified);

-- コメント追加
COMMENT ON COLUMN extracted_conference_members.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN extracted_conference_members.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';

COMMENT ON COLUMN extracted_parliamentary_group_members.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN extracted_parliamentary_group_members.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';
