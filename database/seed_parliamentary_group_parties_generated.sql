-- Generated for parliamentary_group_parties seed data
-- 会派⇔政党の多対多リレーション中間テーブル
-- Issue #1244: フレッシュDBでの中間テーブルデータ投入

-- ============================================================
-- セクション1: Primary政党（is_primary=true）
-- 会派名と政党名の対応で直接INSERT
-- ============================================================

-- 京都府京都市
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT pg.id, pp.id, true
FROM parliamentary_groups pg
JOIN governing_bodies gb ON pg.governing_body_id = gb.id
CROSS JOIN political_parties pp
WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
AND (pg.name, pp.name) IN (
    (' 日本共産党京都市会議員団', '日本共産党'),
    ('公明党京都市会議員団', '公明党'),
    ('自由民主党京都市会議員団', '自由民主党')
)
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- 国会・衆議院
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT pg.id, pp.id, true
FROM parliamentary_groups pg
JOIN governing_bodies gb ON pg.governing_body_id = gb.id
CROSS JOIN political_parties pp
WHERE gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'
AND (pg.name, pp.name) IN (
    ('自由民主党・無所属の会', '自由民主党'),
    ('立憲民主党・無所属', '立憲民主党'),
    ('日本維新の会・教育無償化を実現する会', '日本維新の会'),
    ('国民民主党・無所属クラブ', '国民民主党'),
    ('日本共産党', '日本共産党'),
    ('有志の会', '有志の会'),
    ('れいわ新選組', 'れいわ新選組'),
    ('公明党', '公明党'),
    ('参政党', '参政党'),
    ('社会民主党・護憲連合', '社会民主党'),
    ('減税保守こども', '減税日本')
)
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- 国会・参議院
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT pg.id, pp.id, true
FROM parliamentary_groups pg
JOIN governing_bodies gb ON pg.governing_body_id = gb.id
CROSS JOIN political_parties pp
WHERE gb.name = '国会' AND gb.type = '国' AND pg.chamber = '参議院'
AND (pg.name, pp.name) IN (
    ('自由民主党', '自由民主党'),
    ('公明党', '公明党'),
    ('日本共産党', '日本共産党'),
    ('れいわ新選組', 'れいわ新選組'),
    ('日本維新の会', '日本維新の会'),
    ('参政党', '参政党'),
    ('日本保守党', '日本保守党'),
    ('無所属', '無所属')
)
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
