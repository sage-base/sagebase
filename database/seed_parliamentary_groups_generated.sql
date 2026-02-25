-- Generated from database on 2026-02-15 01:55:09
-- parliamentary_groups seed data
-- Updated: 2026-02-25 Issue #1231 会派⇔政党マッピング充実化

INSERT INTO parliamentary_groups (name, governing_body_id, url, description, is_active, political_party_id) VALUES
-- 京都府京都市 (市町村)
(' 日本共産党京都市会議員団', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://cpgkyoto.jp/', NULL, true, (SELECT id FROM political_parties WHERE name = '日本共産党')),
('公明党京都市会議員団', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www.komeito-kyotocity.com/#member', NULL, true, (SELECT id FROM political_parties WHERE name = '公明党')),
('改新京都', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/kaishinkyoto.html', NULL, true, NULL),
('民主・市民フォーラム京都市会議員団', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/minsyu-kyoto.html', NULL, true, NULL),
('無所属', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/mushozoku.html', NULL, true, NULL),
('維新・京都・国民市会議員団', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/ishin-kyoto-kokumin.html', NULL, true, NULL),
('自由民主党京都市会議員団', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://jimin-kyoto.jp/member_list/', NULL, true, (SELECT id FROM political_parties WHERE name = '自由民主党')),

-- 国会 (国) - 衆議院・参議院共通
-- ※ is_active: gian_summary.json（215回次以降）またはkaiha.json/giin.jsonに出現するものをtrue
-- ※ political_party_id: 会派の主要構成政党を設定（連立会派は筆頭政党）

-- 歴史的会派（is_active = false）
('21世紀クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('おおさか維新の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '日本維新の会')),
('さきがけ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '新党さきがけ')),
('たちあがれ日本', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = 'たちあがれ日本')),
('みんなの党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = 'みんなの党')),
('保守党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '保守党')),
('保守新党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '保守新党')),
('公明党・改革クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '公明党')),
('国民の生活が第一・きづな', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('国民新党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国民新党・そうぞう・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国民新党・大地・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国民新党・新党日本', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国民新党・日本・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国民新党・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国民新党・無所属会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '国民新党')),
('国益と国民の生活を守る会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('太陽党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '太陽党')),
('希望の党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '希望の党')),
('希望の党・無所属クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '希望の党')),
('平和・改革', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('改革無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('改革結集の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('新党きづな', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '新党きづな')),
('新党さきがけ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '新党さきがけ')),
('新党大地・真民主', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '新党大地')),
('新進党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '新進党')),
('日本維新の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '日本維新の会')),
('日本維新の会・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '日本維新の会')),
('未来日本', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('次世代の党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '次世代の党')),
('民主・維新・無所属クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '民主党')),
('民主党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '民主党')),
('民主党・無所属クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '民主党')),
('民主党・無所属クラブ・国民新党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '民主党')),
('民友連', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('民進党・無所属クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '民主党')),
('減税日本・平安', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '減税日本')),
('無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '無所属')),
('生活の党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '生活の党')),
('生活の党と山本太郎となかまたち', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '生活の党')),
('社会保障を立て直す国民会議', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),
('社会民主党・市民連合', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '社会民主党')),
('立憲民主・国民・社保・無所属フォーラム', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '立憲民主党')),
('立憲民主党・市民クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '立憲民主党')),
('立憲民主党・無所属フォーラム', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '立憲民主党')),
('立憲民主党・社民・無所属', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '立憲民主党')),
('結いの党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '結いの党')),
('維新の党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '日本維新の会')),
('自由党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '自由党')),
('自由民主党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '自由民主党')),
('自由民主党・改革クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '自由民主党')),
('自由民主党・無所属会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, (SELECT id FROM political_parties WHERE name = '自由民主党')),
('２１世紀', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, false, NULL),

-- 現行会派（is_active = true）- 衆議院
('れいわ新選組', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = 'れいわ新選組')),
('チームみらい・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '衆議院219回次〜', true, NULL),
('公明党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '公明党')),
('参政党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '参政党')),
('国民民主党・無所属クラブ', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '国民民主党')),
('改革の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '衆議院219回次〜', true, NULL),
('日本保守党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '日本保守党')),
('日本共産党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '日本共産党')),
('日本維新の会・教育無償化を実現する会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '日本維新の会')),
('有志の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, NULL),
('減税保守こども', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, NULL),
('無所属', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '無所属')),
('立憲民主党・無所属', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '立憲民主党')),
('自由民主党・無所属の会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, NULL, true, (SELECT id FROM political_parties WHERE name = '自由民主党')),

-- 現行会派（is_active = true）- 参議院（kaiha.json/giin.jsonより）
('各派に属しない議員', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '参議院', true, NULL),
('国民民主党・新緑風会', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '参議院', true, (SELECT id FROM political_parties WHERE name = '国民民主党')),
('沖縄の風', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '参議院', true, (SELECT id FROM political_parties WHERE name = '沖縄の風')),
('社会民主党', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '参議院（衆議院では社会民主党・市民連合）', true, (SELECT id FROM political_parties WHERE name = '社会民主党')),
('立憲民主・無所属', (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), NULL, '参議院', true, (SELECT id FROM political_parties WHERE name = '立憲民主党'))
ON CONFLICT (name, governing_body_id) DO UPDATE SET url = EXCLUDED.url, description = EXCLUDED.description, is_active = EXCLUDED.is_active, political_party_id = EXCLUDED.political_party_id;

-- シーケンスリセット（IDを明示指定していないためON CONFLICTで既存IDが使われるが、新規INSERTに備えてリセット）
SELECT setval('parliamentary_groups_id_seq', COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);
