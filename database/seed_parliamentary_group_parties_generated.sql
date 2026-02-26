-- Generated for parliamentary_group_parties seed data
-- 会派⇔政党の多対多リレーション中間テーブル
-- Issue #1244: フレッシュDBでの中間テーブルデータ投入

-- ============================================================
-- セクション1: Primary政党（is_primary=true）
-- 既存 parliamentary_groups.political_party_id からの一括移行
-- ============================================================

INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT pg.id, pg.political_party_id, true
FROM parliamentary_groups pg
WHERE pg.political_party_id IS NOT NULL
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- 減税保守こども → 減税日本（シードではpolitical_party_id=NULLだが、Primary政党として登録）
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '減税保守こども' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '減税日本'),
    true
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- ============================================================
-- セクション2: Secondary政党（is_primary=false）
-- 連立会派の構成政党を個別INSERT
-- ============================================================

-- 国民の生活が第一・きづな → 新党きづな
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '国民の生活が第一・きづな' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '新党きづな'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 平和・改革 → 改革クラブ
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '平和・改革' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '改革クラブ'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 公明党・改革クラブ → 改革クラブ
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '公明党・改革クラブ' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '改革クラブ'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 国民新党・大地・無所属の会 → 新党大地
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '国民新党・大地・無所属の会' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '新党大地'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 国民新党・新党日本 → 新党日本
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '国民新党・新党日本' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '新党日本'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 国民新党・日本・無所属の会 → 新党日本
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '国民新党・日本・無所属の会' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '新党日本'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 民主党・無所属クラブ・国民新党 → 国民新党
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '民主党・無所属クラブ・国民新党' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '国民新党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 民主・維新・無所属クラブ → 日本維新の会
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '民主・維新・無所属クラブ' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '日本維新の会'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 立憲民主・国民・社保・無所属フォーラム → 国民民主党
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '立憲民主・国民・社保・無所属フォーラム' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '国民民主党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 立憲民主・国民・社保・無所属フォーラム → 社会民主党
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '立憲民主・国民・社保・無所属フォーラム' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '社会民主党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 立憲民主党・社民・無所属 → 社会民主党
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '立憲民主党・社民・無所属' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '社会民主党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 自由民主党・改革クラブ → 改革クラブ
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '自由民主党・改革クラブ' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '改革クラブ'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 減税保守こども → 日本保守党
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '減税保守こども' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = '日本保守党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- チームみらい・無所属の会 → チームみらい
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = 'チームみらい・無所属の会' AND gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'),
    (SELECT id FROM political_parties WHERE name = 'チームみらい'),
    true
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- ============================================================
-- セクション3: シーケンスリセット
-- ============================================================
SELECT setval('parliamentary_group_parties_id_seq',
    COALESCE((SELECT MAX(id) FROM parliamentary_group_parties), 0) + 1, false);
