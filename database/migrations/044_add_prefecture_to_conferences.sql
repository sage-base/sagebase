-- 会議体テーブルに都道府県カラムを追加
-- 国会は「全国」、地方議会はそれぞれの都道府県を設定

ALTER TABLE conferences
ADD COLUMN IF NOT EXISTS prefecture VARCHAR(10);

-- インデックスを追加（都道府県での絞り込みを高速化）
CREATE INDEX IF NOT EXISTS idx_conferences_prefecture ON conferences(prefecture);

-- コメント追加
COMMENT ON COLUMN conferences.prefecture IS '都道府県（全国は国会を表す）';
