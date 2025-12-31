-- マイグレーション: 039_add_verification_fields_to_gold_entities.sql
-- 目的: 5つのGoldエンティティテーブルに手動検証フィールドを追加
-- 対象: conversations, politicians, speakers, politician_affiliations, parliamentary_group_memberships
-- 関連Issue: #862 [PBI-002] 全Goldエンティティへの手動検証フラグ追加

-- conversations テーブル (Statement相当)
ALTER TABLE conversations
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- politicians テーブル
ALTER TABLE politicians
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- speakers テーブル
ALTER TABLE speakers
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- politician_affiliations テーブル (ConferenceMember相当)
ALTER TABLE politician_affiliations
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- parliamentary_group_memberships テーブル (ParliamentaryGroupMember相当)
ALTER TABLE parliamentary_group_memberships
ADD COLUMN is_manually_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN latest_extraction_log_id INTEGER REFERENCES extraction_logs(id);

-- インデックスの作成（is_manually_verifiedでフィルタリングするクエリを高速化）
CREATE INDEX idx_conversations_manually_verified ON conversations(is_manually_verified);
CREATE INDEX idx_politicians_manually_verified ON politicians(is_manually_verified);
CREATE INDEX idx_speakers_manually_verified ON speakers(is_manually_verified);
CREATE INDEX idx_politician_affiliations_manually_verified ON politician_affiliations(is_manually_verified);
CREATE INDEX idx_parliamentary_group_memberships_manually_verified ON parliamentary_group_memberships(is_manually_verified);

-- コメント追加
COMMENT ON COLUMN conversations.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN conversations.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';

COMMENT ON COLUMN politicians.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN politicians.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';

COMMENT ON COLUMN speakers.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN speakers.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';

COMMENT ON COLUMN politician_affiliations.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN politician_affiliations.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';

COMMENT ON COLUMN parliamentary_group_memberships.is_manually_verified IS '人間による手動検証済みフラグ。Trueの場合、AI更新から保護される。';
COMMENT ON COLUMN parliamentary_group_memberships.latest_extraction_log_id IS '最新のLLM抽出ログへの参照。抽出履歴のトレーサビリティを確保。';
