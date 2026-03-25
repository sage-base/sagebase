-- Generated for parliamentary_group_parties seed data
-- 会派⇔政党の多対多リレーション中間テーブル
-- Issue #1244: フレッシュDBでの中間テーブルデータ投入
-- Issue #1390: 会派⇔政党マッピング補完（カバレッジ35%→90%）

-- ============================================================
-- セクション0: 不足する歴史的政党の追加
-- 選挙インポートで作成済みの場合はスキップ
-- ============================================================
INSERT INTO political_parties (name) VALUES
    ('沖縄の風'),
    ('おおさか維新の会'),
    ('みんなの党'),
    ('保守新党'),
    ('たちあがれ日本'),
    ('次世代の党'),
    ('結いの党'),
    ('維新の党'),
    ('自由党'),
    ('新進党'),
    ('太陽党'),
    ('新党さきがけ'),
    ('生活の党'),
    ('国民の生活が第一'),
    ('民進党'),
    ('京都党')
ON CONFLICT (name) DO NOTHING;

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
    ('自由民主党京都市会議員団', '自由民主党'),
    -- Issue #1403 追加分
    ('改新京都', '立憲民主党'),
    ('民主・市民フォーラム京都市会議員団', '立憲民主党'),
    ('維新・京都・国民市会議員団', '日本維新の会')
)
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- 国会・衆議院（現行会派）
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
    ('有志の会', '無所属'),
    ('改革の会', '無所属'),
    ('れいわ新選組', 'れいわ新選組'),
    ('公明党', '公明党'),
    ('参政党', '参政党'),
    ('社会民主党・護憲連合', '社会民主党'),
    ('減税保守こども', '減税日本'),
    -- Issue #1390 追加分
    ('日本保守党', '日本保守党'),
    ('無所属', '無所属')
)
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- 国会・参議院（現行会派）
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
    ('無所属', '無所属'),
    -- Issue #1390 追加分
    ('国民民主党・新緑風会', '国民民主党'),
    ('沖縄の風', '沖縄の風'),
    ('社会民主党', '社会民主党'),
    ('立憲民主・無所属', '立憲民主党'),
    ('各派に属しない議員', '無所属')
)
ON CONFLICT (parliamentary_group_id, political_party_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

-- 国会・衆議院（歴史的会派） - Issue #1390 追加
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT pg.id, pp.id, true
FROM parliamentary_groups pg
JOIN governing_bodies gb ON pg.governing_body_id = gb.id
CROSS JOIN political_parties pp
WHERE gb.name = '国会' AND gb.type = '国' AND pg.chamber = '衆議院'
AND (pg.name, pp.name) IN (
    -- 完全一致系
    ('たちあがれ日本', 'たちあがれ日本'),
    ('みんなの党', 'みんなの党'),
    ('保守党', '保守党'),
    ('保守新党', '保守新党'),
    ('国民新党', '国民新党'),
    ('太陽党', '太陽党'),
    ('希望の党', '希望の党'),
    ('新党きづな', '新党きづな'),
    ('新党さきがけ', '新党さきがけ'),
    ('新進党', '新進党'),
    ('日本維新の会', '日本維新の会'),
    ('次世代の党', '次世代の党'),
    ('民主党', '民主党'),
    ('結いの党', '結いの党'),
    ('自由党', '自由党'),
    ('自由民主党', '自由民主党'),
    ('生活の党', '生活の党'),
    -- 略称→正式名系
    ('さきがけ', '新党さきがけ'),
    ('おおさか維新の会', '日本維新の会'),
    ('維新の党', '日本維新の会'),
    -- 連立会派のPrimary政党
    ('国民新党・そうぞう・無所属の会', '国民新党'),
    ('国民新党・大地・無所属の会', '国民新党'),
    ('国民新党・新党日本', '国民新党'),
    ('国民新党・日本・無所属の会', '国民新党'),
    ('国民新党・無所属の会', '国民新党'),
    ('国民新党・無所属会', '国民新党'),
    ('国民の生活が第一・きづな', '国民の生活が第一'),
    ('希望の党・無所属クラブ', '希望の党'),
    ('平和・改革', '公明党'),
    ('公明党・改革クラブ', '公明党'),
    ('新党大地・真民主', '新党大地'),
    ('日本維新の会・無所属の会', '日本維新の会'),
    ('民主・維新・無所属クラブ', '民主党'),
    ('民主党・無所属クラブ', '民主党'),
    ('民主党・無所属クラブ・国民新党', '民主党'),
    ('民友連', '民主党'),
    ('民進党・無所属クラブ', '民進党'),
    ('減税日本・平安', '減税日本'),
    ('無所属の会', '無所属'),
    ('生活の党と山本太郎となかまたち', '生活の党'),
    ('社会民主党・市民連合', '社会民主党'),
    ('立憲民主・国民・社保・無所属フォーラム', '立憲民主党'),
    ('立憲民主党・市民クラブ', '立憲民主党'),
    ('立憲民主党・無所属フォーラム', '立憲民主党'),
    ('立憲民主党・社民・無所属', '立憲民主党'),
    ('自由民主党・改革クラブ', '自由民主党'),
    ('自由民主党・無所属会', '自由民主党'),
    -- Issue #1403 追加分: 無所属系会派
    ('21世紀クラブ', '無所属'),
    ('国益と国民の生活を守る会', '無所属'),
    ('改革無所属の会', '無所属'),
    ('改革結集の会', '無所属'),
    ('未来日本', '無所属'),
    ('社会保障を立て直す国民会議', '無所属'),
    ('２１世紀', '無所属')
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

-- Issue #1403: 京都市会のSecondary政党

-- 改新京都 → 国民民主党（Secondary: 小島信太郎議員）
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '改新京都' AND gb.name = '京都府京都市' AND gb.type = '市町村'),
    (SELECT id FROM political_parties WHERE name = '国民民主党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 維新・京都・国民市会議員団 → 京都党（Secondary）
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '維新・京都・国民市会議員団' AND gb.name = '京都府京都市' AND gb.type = '市町村'),
    (SELECT id FROM political_parties WHERE name = '京都党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- 維新・京都・国民市会議員団 → 国民民主党（Secondary）
INSERT INTO parliamentary_group_parties (parliamentary_group_id, political_party_id, is_primary)
SELECT
    (SELECT pg.id FROM parliamentary_groups pg
     JOIN governing_bodies gb ON pg.governing_body_id = gb.id
     WHERE pg.name = '維新・京都・国民市会議員団' AND gb.name = '京都府京都市' AND gb.type = '市町村'),
    (SELECT id FROM political_parties WHERE name = '国民民主党'),
    false
ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;

-- ============================================================
-- セクション3: シーケンスリセット
-- ============================================================
SELECT setval('parliamentary_group_parties_id_seq',
    COALESCE((SELECT MAX(id) FROM parliamentary_group_parties), 0) + 1, false);
