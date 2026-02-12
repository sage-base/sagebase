-- Parliamentary Groups Seed Data
-- Generated from current database

INSERT INTO parliamentary_groups (id, name, governing_body_id, url, description, is_active, political_party_id) VALUES
    (1, ' 日本共産党京都市会議員団', 88, 'https://cpgkyoto.jp/', NULL, true, 9),
    (2, '公明党京都市会議員団', 88, 'https://www.komeito-kyotocity.com/#member', NULL, true, 5),
    (3, '改新京都', 88, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/kaishinkyoto.html', NULL, true, NULL),
    (4, '民主・市民フォーラム京都市会議員団', 88, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/minsyu-kyoto.html', NULL, true, NULL),
    (5, '無所属', 88, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/mushozoku.html', NULL, true, NULL),
    (6, '維新・京都・国民市会議員団', 88, 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/ishin-kyoto-kokumin.html', NULL, true, NULL),
    (7, '自由民主党京都市会議員団', 88, 'https://jimin-kyoto.jp/member_list/', NULL, true, 15),
    (9, '立憲民主党・無所属', 1, NULL, NULL, true, 14),
    (8, '自由民主党・無所属の会', 1, NULL, NULL, true, 15)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    governing_body_id = EXCLUDED.governing_body_id,
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    political_party_id = EXCLUDED.political_party_id;

-- Reset sequence to max id + 1 (Issue #1036)
SELECT setval('parliamentary_groups_id_seq',
    COALESCE((SELECT MAX(id) FROM parliamentary_groups), 0) + 1, false);
