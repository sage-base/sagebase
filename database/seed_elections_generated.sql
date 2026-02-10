-- Generated from database on 2026-02-05 06:49:45
-- elections seed data

-- 京都府京都市 (市町村) - 明示的ID付き
INSERT INTO elections (id, governing_body_id, term_number, election_date, election_type) VALUES
(19, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 1, '1947-04-05', '統一地方選挙'),
(18, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 2, '1951-04-23', '統一地方選挙'),
(17, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 3, '1955-04-23', '統一地方選挙'),
(16, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 4, '1959-04-23', '統一地方選挙'),
(15, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 5, '1963-04-17', '統一地方選挙'),
(14, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 6, '1967-04-15', '統一地方選挙'),
(13, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 7, '1971-04-11', '統一地方選挙'),
(12, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 8, '1975-04-13', '統一地方選挙'),
(11, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 9, '1979-04-08', '統一地方選挙'),
(10, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 10, '1983-04-10', '統一地方選挙'),
(9, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 11, '1987-04-12', '統一地方選挙'),
(8, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 12, '1991-04-07', '統一地方選挙'),
(7, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 14, '1999-04-11', '統一地方選挙'),
(6, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 15, '2003-04-13', '統一地方選挙'),
(5, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 16, '2007-04-08', '統一地方選挙'),
(4, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 17, '2011-04-10', '統一地方選挙'),
(2, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 18, '2015-04-12', '統一地方選挙'),
(3, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 19, '2019-04-07', '統一地方選挙'),
(1, (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 20, '2023-04-09', '統一地方選挙')
ON CONFLICT (governing_body_id, term_number) DO UPDATE SET election_date = EXCLUDED.election_date, election_type = EXCLUDED.election_type;

-- 明示的IDの最大値に合わせてシーケンスを更新（CROSS JOINのID自動採番が衝突しないようにする）
SELECT setval('elections_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM elections), false);

-- 国会・京都府京都市以外の全開催主体に同じ統一地方選挙データを追加
INSERT INTO elections (governing_body_id, term_number, election_date, election_type)
SELECT gb.id, v.term_number, v.election_date::date, v.election_type
FROM governing_bodies gb
CROSS JOIN (VALUES
    (1,  '1947-04-05', '統一地方選挙'),
    (2,  '1951-04-23', '統一地方選挙'),
    (3,  '1955-04-23', '統一地方選挙'),
    (4,  '1959-04-23', '統一地方選挙'),
    (5,  '1963-04-17', '統一地方選挙'),
    (6,  '1967-04-15', '統一地方選挙'),
    (7,  '1971-04-11', '統一地方選挙'),
    (8,  '1975-04-13', '統一地方選挙'),
    (9,  '1979-04-08', '統一地方選挙'),
    (10, '1983-04-10', '統一地方選挙'),
    (11, '1987-04-12', '統一地方選挙'),
    (12, '1991-04-07', '統一地方選挙'),
    (14, '1999-04-11', '統一地方選挙'),
    (15, '2003-04-13', '統一地方選挙'),
    (16, '2007-04-08', '統一地方選挙'),
    (17, '2011-04-10', '統一地方選挙'),
    (18, '2015-04-12', '統一地方選挙'),
    (19, '2019-04-07', '統一地方選挙'),
    (20, '2023-04-09', '統一地方選挙')
) AS v(term_number, election_date, election_type)
WHERE gb.type != '国'
  AND gb.id != (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')
ON CONFLICT (governing_body_id, term_number) DO UPDATE SET election_date = EXCLUDED.election_date, election_type = EXCLUDED.election_type;

-- Reset sequence to max id + 1
SELECT setval('elections_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM elections), false);
