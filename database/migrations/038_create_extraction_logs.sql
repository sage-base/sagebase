-- 汎用抽出ログテーブルの作成
-- 全エンティティ（Statement, Politician, Speaker, ConferenceMember, ParliamentaryGroupMember）の
-- LLM抽出結果を統一的に履歴管理するためのテーブル

-- エンティティタイプのENUM型を作成（冪等性対応）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'entity_type') THEN
        CREATE TYPE entity_type AS ENUM (
            'statement',
            'politician',
            'speaker',
            'conference_member',
            'parliamentary_group_member'
        );
    END IF;
END$$;

-- 抽出ログテーブルの作成（冪等性対応）
CREATE TABLE IF NOT EXISTS extraction_logs (
    id SERIAL PRIMARY KEY,

    -- 抽出対象エンティティの情報
    entity_type entity_type NOT NULL,
    entity_id INTEGER NOT NULL,

    -- パイプライン情報
    pipeline_version VARCHAR(100) NOT NULL,

    -- 抽出データ
    extracted_data JSONB NOT NULL,
    confidence_score FLOAT,

    -- 追加メタデータ（モデル名、トークン数、処理時間など）
    extraction_metadata JSONB NOT NULL DEFAULT '{}',

    -- 標準タイムスタンプ
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- パフォーマンス向上のためのインデックス作成（冪等性対応）
CREATE INDEX IF NOT EXISTS idx_extraction_logs_entity ON extraction_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_pipeline ON extraction_logs(pipeline_version);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_created_at ON extraction_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_entity_type ON extraction_logs(entity_type);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_confidence ON extraction_logs(confidence_score);

-- テーブルとカラムへのコメント追加
COMMENT ON TABLE extraction_logs IS 'LLM抽出結果の履歴を記録するテーブル（全エンティティタイプ対応）';
COMMENT ON COLUMN extraction_logs.entity_type IS '抽出対象のエンティティタイプ（statement, politician, speaker等）';
COMMENT ON COLUMN extraction_logs.entity_id IS '抽出対象のエンティティID';
COMMENT ON COLUMN extraction_logs.pipeline_version IS 'パイプラインのバージョン（例: gemini-2.0-flash-v1）';
COMMENT ON COLUMN extraction_logs.extracted_data IS 'LLMが出力した生データ（JSON形式）';
COMMENT ON COLUMN extraction_logs.confidence_score IS '抽出の信頼度スコア（0.0〜1.0）';
COMMENT ON COLUMN extraction_logs.extraction_metadata IS '抽出に関する追加メタデータ（モデル名、トークン数、処理時間など）';

-- updated_at自動更新トリガーの作成（CREATE OR REPLACEで冪等性対応済み）
CREATE OR REPLACE FUNCTION update_extraction_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- トリガーの作成（冪等性対応）
DROP TRIGGER IF EXISTS trigger_update_extraction_logs_updated_at ON extraction_logs;
CREATE TRIGGER trigger_update_extraction_logs_updated_at
    BEFORE UPDATE ON extraction_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_extraction_logs_updated_at();
