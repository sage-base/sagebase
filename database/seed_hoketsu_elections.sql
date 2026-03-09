-- 参議院議員補欠選挙 SEED データ
-- Generated from go2senkyo.com on 2026-03-09
-- 全151件の補欠選挙レコード (1947-2024)
--
-- election_type = '参議院議員補欠選挙' として登録
-- term_number は補欠選挙の通し番号（1=最古, 151=最新）
-- 通常選挙の term_number とは独立した番号体系
--
-- 適用手順:
--   1. seed_hoketsu_politicians.sql を先に実行（新規政治家31名の追加）
--   2. 本ファイルを実行（選挙レコード151件の追加）
--   3. seed_hoketsu_election_members.sql を実行（当選者173件の紐付け）

INSERT INTO elections (id, governing_body_id, term_number, election_date, election_type) VALUES
(35001, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 1, '1947-08-11', '参議院議員補欠選挙'),  -- 滋賀選挙区
(35002, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 2, '1947-08-15', '参議院議員補欠選挙'),  -- 栃木選挙区・群馬選挙区・徳島選挙区・鹿児島選挙区
(35003, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 3, '1947-10-07', '参議院議員補欠選挙'),  -- 岩手選挙区
(35004, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 4, '1948-01-11', '参議院議員補欠選挙'),  -- 長崎選挙区
(35005, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 5, '1948-02-05', '参議院議員補欠選挙'),  -- 長野選挙区
(35006, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 6, '1948-02-15', '参議院議員補欠選挙'),  -- 熊本選挙区
(35007, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 7, '1948-06-18', '参議院議員補欠選挙'),  -- 奈良選挙区
(35008, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 8, '1949-06-03', '参議院議員補欠選挙'),  -- 兵庫選挙区
(35009, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 9, '1949-12-24', '参議院議員補欠選挙'),  -- 福島選挙区
(35010, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 10, '1950-01-12', '参議院議員補欠選挙'),  -- 兵庫選挙区
(35011, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 11, '1950-01-17', '参議院議員補欠選挙'),  -- 福岡選挙区
(35012, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 12, '1950-11-03', '参議院議員補欠選挙'),  -- 茨城選挙区
(35013, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 13, '1950-12-13', '参議院議員補欠選挙'),  -- 千葉選挙区
(35014, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 14, '1950-12-20', '参議院議員補欠選挙'),  -- 広島選挙区
(35015, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 15, '1951-02-12', '参議院議員補欠選挙'),  -- 福島選挙区
(35016, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 16, '1951-05-16', '参議院議員補欠選挙'),  -- 大阪選挙区
(35017, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 17, '1951-05-21', '参議院議員補欠選挙'),  -- 愛媛選挙区
(35018, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 18, '1951-11-16', '参議院議員補欠選挙'),  -- 富山選挙区
(35019, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 19, '1952-05-06', '参議院議員補欠選挙'),  -- 静岡選挙区
(35020, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 20, '1952-10-20', '参議院議員補欠選挙'),  -- 熊本選挙区
(35021, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 21, '1953-07-30', '参議院議員補欠選挙'),  -- 青森選挙区
(35022, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 22, '1954-01-20', '参議院議員補欠選挙'),  -- 千葉選挙区
(35023, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 23, '1954-06-03', '参議院議員補欠選挙'),  -- 和歌山選挙区
(35024, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 24, '1955-03-10', '参議院議員補欠選挙'),  -- 福井選挙区
(35025, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 25, '1955-03-17', '参議院議員補欠選挙'),  -- 福岡選挙区
(35026, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 26, '1955-05-15', '参議院議員補欠選挙'),  -- 新潟選挙区
(35027, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 27, '1955-06-05', '参議院議員補欠選挙'),  -- 埼玉選挙区
(35028, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 28, '1955-08-07', '参議院議員補欠選挙'),  -- 三重選挙区
(35029, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 29, '1955-11-11', '参議院議員補欠選挙'),  -- 島根選挙区
(35030, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 30, '1956-01-15', '参議院議員補欠選挙'),  -- 京都選挙区
(35031, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 31, '1956-04-04', '参議院議員補欠選挙'),  -- 鳥取選挙区
(35032, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 32, '1956-11-30', '参議院議員補欠選挙'),  -- 鹿児島選挙区
(35033, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 33, '1957-04-23', '参議院議員補欠選挙'),  -- 大阪選挙区
(35034, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 34, '1957-06-28', '参議院議員補欠選挙'),  -- 香川選挙区
(35035, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 35, '1958-06-22', '参議院議員補欠選挙'),  -- 秋田選挙区
(35036, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 36, '1958-07-06', '参議院議員補欠選挙'),  -- 島根選挙区
(35037, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 37, '1958-08-24', '参議院議員補欠選挙'),  -- 福岡選挙区
(35038, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 38, '1958-12-07', '参議院議員補欠選挙'),  -- 石川選挙区
(35039, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 39, '1959-04-30', '参議院議員補欠選挙'),  -- 大阪選挙区
(35040, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 40, '1959-07-24', '参議院議員補欠選挙'),  -- 山形選挙区
(35041, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 41, '1959-08-20', '参議院議員補欠選挙'),  -- 兵庫選挙区
(35042, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 42, '1960-05-18', '参議院議員補欠選挙'),  -- 熊本選挙区
(35043, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 43, '1960-11-20', '参議院議員補欠選挙'),  -- 埼玉選挙区
(35044, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 44, '1960-12-01', '参議院議員補欠選挙'),  -- 千葉選挙区
(35045, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 45, '1961-12-10', '参議院議員補欠選挙'),  -- 宮崎選挙区
(35046, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 46, '1962-11-30', '参議院議員補欠選挙'),  -- 熊本選挙区
(35047, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 47, '1963-01-29', '参議院議員補欠選挙'),  -- 熊本選挙区
(35048, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 48, '1963-04-06', '参議院議員補欠選挙'),  -- 栃木選挙区
(35049, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 49, '1963-04-09', '参議院議員補欠選挙'),  -- 福岡選挙区
(35050, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 50, '1963-09-18', '参議院議員補欠選挙'),  -- 茨城選挙区
(35051, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 51, '1963-10-28', '参議院議員補欠選挙'),  -- 愛知選挙区
(35052, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 52, '1963-12-10', '参議院議員補欠選挙'),  -- 京都選挙区
(35053, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 53, '1964-06-21', '参議院議員補欠選挙'),  -- 和歌山選挙区
(35054, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 54, '1964-12-09', '参議院議員補欠選挙'),  -- 岡山選挙区
(35055, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 55, '1965-04-11', '参議院議員補欠選挙'),  -- 宮城選挙区
(35056, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 56, '1966-01-30', '参議院議員補欠選挙'),  -- 広島選挙区
(35057, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 57, '1966-04-27', '参議院議員補欠選挙'),  -- 京都選挙区
(35058, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 58, '1966-11-05', '参議院議員補欠選挙'),  -- 愛知選挙区
(35059, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 59, '1967-02-12', '参議院議員補欠選挙'),  -- 神奈川選挙区
(35060, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 60, '1967-04-30', '参議院議員補欠選挙'),  -- 福岡選挙区
(35061, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 61, '1967-06-25', '参議院議員補欠選挙'),  -- 滋賀選挙区
(35062, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 62, '1967-08-20', '参議院議員補欠選挙'),  -- 群馬選挙区
(35063, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 63, '1967-09-15', '参議院議員補欠選挙'),  -- 秋田選挙区
(35064, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 64, '1967-11-05', '参議院議員補欠選挙'),  -- 千葉選挙区・新潟選挙区
(35065, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 65, '1968-06-09', '参議院議員補欠選挙'),  -- 岩手選挙区
(35066, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 66, '1970-03-15', '参議院議員補欠選挙'),  -- 長崎選挙区
(35067, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 67, '1970-11-01', '参議院議員補欠選挙'),  -- 山梨選挙区
(35068, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 68, '1970-11-15', '参議院議員補欠選挙'),  -- 沖縄選挙区
(35069, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 69, '1971-02-07', '参議院議員補欠選挙'),  -- 石川選挙区
(35070, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 70, '1972-02-06', '参議院議員補欠選挙'),  -- 茨城選挙区
(35071, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 71, '1972-10-22', '参議院議員補欠選挙'),  -- 三重選挙区
(35072, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 72, '1972-11-05', '参議院議員補欠選挙'),  -- 兵庫選挙区
(35073, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 73, '1972-12-10', '参議院議員補欠選挙'),  -- 静岡選挙区
(35074, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 74, '1972-12-17', '参議院議員補欠選挙'),  -- 新潟選挙区
(35075, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 75, '1973-06-17', '参議院議員補欠選挙'),  -- 青森選挙区・大阪選挙区
(35076, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 76, '1974-01-27', '参議院議員補欠選挙'),  -- 香川選挙区
(35077, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 77, '1974-04-21', '参議院議員補欠選挙'),  -- 京都選挙区
(35078, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 78, '1974-05-12', '参議院議員補欠選挙'),  -- 高知選挙区
(35079, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 79, '1974-12-08', '参議院議員補欠選挙'),  -- 栃木選挙区
(35080, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 80, '1975-04-27', '参議院議員補欠選挙'),  -- 茨城選挙区・愛知選挙区
(35081, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 81, '1975-09-21', '参議院議員補欠選挙'),  -- 鹿児島選挙区
(35082, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 82, '1976-05-23', '参議院議員補欠選挙'),  -- 秋田選挙区
(35083, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 83, '1976-09-26', '参議院議員補欠選挙'),  -- 奈良選挙区・大分選挙区
(35084, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 84, '1976-12-12', '参議院議員補欠選挙'),  -- 新潟選挙区・宮崎選挙区
(35085, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 85, '1977-05-22', '参議院議員補欠選挙'),  -- 新潟選挙区
(35086, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 86, '1977-09-04', '参議院議員補欠選挙'),  -- 熊本選挙区
(35087, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 87, '1978-02-05', '参議院議員補欠選挙'),  -- 茨城選挙区
(35088, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 88, '1978-02-19', '参議院議員補欠選挙'),  -- 和歌山選挙区
(35089, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 89, '1978-04-23', '参議院議員補欠選挙'),  -- 京都選挙区
(35090, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 90, '1979-04-22', '参議院議員補欠選挙'),  -- 熊本選挙区
(35091, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 91, '1980-06-01', '参議院議員補欠選挙'),  -- 青森選挙区
(35092, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 92, '1981-02-01', '参議院議員補欠選挙'),  -- 岐阜選挙区
(35093, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 93, '1981-03-08', '参議院議員補欠選挙'),  -- 千葉選挙区
(35094, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 94, '1981-06-28', '参議院議員補欠選挙'),  -- 岐阜選挙区
(35095, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 95, '1981-11-01', '参議院議員補欠選挙'),  -- 鳥取選挙区
(35096, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 96, '1981-11-29', '参議院議員補欠選挙'),  -- 広島選挙区
(35097, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 97, '1982-01-10', '参議院議員補欠選挙'),  -- 佐賀選挙区
(35098, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 98, '1982-11-14', '参議院議員補欠選挙'),  -- 沖縄選挙区
(35099, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 99, '1982-12-26', '参議院議員補欠選挙'),  -- 富山選挙区
(35100, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 100, '1983-02-13', '参議院議員補欠選挙'),  -- 栃木選挙区
(35101, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 101, '1983-12-18', '参議院議員補欠選挙'),  -- 静岡選挙区
(35102, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 102, '1985-02-03', '参議院議員補欠選挙'),  -- 奈良選挙区
(35103, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 103, '1985-02-17', '参議院議員補欠選挙'),  -- 福島選挙区
(35104, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 104, '1985-10-20', '参議院議員補欠選挙'),  -- 熊本選挙区
(35105, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 105, '1986-08-10', '参議院議員補欠選挙'),  -- 佐賀選挙区
(35106, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 106, '1987-03-08', '参議院議員補欠選挙'),  -- 岩手選挙区
(35107, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 107, '1987-07-12', '参議院議員補欠選挙'),  -- 山口選挙区
(35108, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 108, '1987-11-01', '参議院議員補欠選挙'),  -- 神奈川選挙区
(35109, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 109, '1987-12-27', '参議院議員補欠選挙'),  -- 大阪選挙区
(35110, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 110, '1988-02-28', '参議院議員補欠選挙'),  -- 大阪選挙区
(35111, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 111, '1988-04-10', '参議院議員補欠選挙'),  -- 佐賀選挙区
(35112, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 112, '1988-09-04', '参議院議員補欠選挙'),  -- 福島選挙区
(35113, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 113, '1989-02-12', '参議院議員補欠選挙'),  -- 福岡選挙区
(35114, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 114, '1989-06-25', '参議院議員補欠選挙'),  -- 新潟選挙区
(35115, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 115, '1989-10-01', '参議院議員補欠選挙'),  -- 茨城選挙区
(35116, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 116, '1990-06-10', '参議院議員補欠選挙'),  -- 福岡選挙区
(35117, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 117, '1990-11-04', '参議院議員補欠選挙'),  -- 愛知選挙区
(35118, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 118, '1990-12-09', '参議院議員補欠選挙'),  -- 新潟選挙区
(35119, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 119, '1991-02-24', '参議院議員補欠選挙'),  -- 青森選挙区
(35120, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 120, '1991-06-16', '参議院議員補欠選挙'),  -- 埼玉選挙区
(35121, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 121, '1991-09-29', '参議院議員補欠選挙'),  -- 福岡選挙区
(35122, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 122, '1992-02-09', '参議院議員補欠選挙'),  -- 奈良選挙区
(35123, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 123, '1992-03-08', '参議院議員補欠選挙'),  -- 宮城選挙区
(35124, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 124, '1992-04-12', '参議院議員補欠選挙'),  -- 茨城選挙区
(35125, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 125, '1993-07-18', '参議院議員補欠選挙'),  -- 福島選挙区・岐阜選挙区・愛知選挙区・広島選挙区
(35126, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 126, '1995-11-19', '参議院議員補欠選挙'),  -- 佐賀選挙区
(35127, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 127, '1996-03-25', '参議院議員補欠選挙'),  -- 岐阜選挙区
(35128, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 128, '1996-10-20', '参議院議員補欠選挙'),  -- 栃木選挙区
(35129, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 129, '1996-11-17', '参議院議員補欠選挙'),  -- 兵庫選挙区
(35130, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 130, '1997-11-16', '参議院議員補欠選挙'),  -- 宮城選挙区
(35131, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 131, '1998-11-08', '参議院議員補欠選挙'),  -- 和歌山選挙区
(35132, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 132, '1999-10-17', '参議院議員補欠選挙'),  -- 長野選挙区
(35133, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 133, '2000-04-16', '参議院議員補欠選挙'),  -- 熊本選挙区
(35134, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 134, '2000-06-25', '参議院議員補欠選挙'),  -- 石川選挙区・三重選挙区・愛媛選挙区
(35135, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 135, '2000-10-22', '参議院議員補欠選挙'),  -- 滋賀選挙区
(35136, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 136, '2001-07-29', '参議院議員補欠選挙'),  -- 新潟選挙区
(35137, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 137, '2002-10-27', '参議院議員補欠選挙'),  -- 千葉選挙区・鳥取選挙区
(35138, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 138, '2003-04-27', '参議院議員補欠選挙'),  -- 茨城選挙区
(35139, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 139, '2003-10-26', '参議院議員補欠選挙'),  -- 埼玉選挙区
(35140, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 140, '2005-10-23', '参議院議員補欠選挙'),  -- 神奈川選挙区
(35141, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 141, '2007-04-22', '参議院議員補欠選挙'),  -- 福島選挙区・沖縄選挙区
(35142, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 142, '2009-10-25', '参議院議員補欠選挙'),  -- 神奈川選挙区・静岡選挙区
(35143, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 143, '2013-04-28', '参議院議員補欠選挙'),  -- 山口選挙区
(35144, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 144, '2019-10-27', '参議院議員補欠選挙'),  -- 埼玉選挙区
(35145, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 145, '2021-04-25', '参議院議員補欠選挙'),  -- 長野選挙区
(35146, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 146, '2021-04-25', '参議院議員補欠選挙'),  -- 広島選挙区
(35147, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 147, '2021-10-24', '参議院議員補欠選挙'),  -- 静岡選挙区・山口選挙区
(35148, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 148, '2022-04-24', '参議院議員補欠選挙'),  -- 石川選挙区
(35149, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 149, '2023-04-23', '参議院議員補欠選挙'),  -- 大分選挙区
(35150, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 150, '2023-10-22', '参議院議員補欠選挙'),  -- 徳島・高知選挙区
(35151, (SELECT id FROM governing_bodies WHERE name = '国会' AND type = '国'), 151, '2024-10-27', '参議院議員補欠選挙')   -- 岩手選挙区
ON CONFLICT (governing_body_id, term_number, election_type) DO UPDATE SET election_date = EXCLUDED.election_date;

-- Reset sequence
SELECT setval('elections_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM elections), false);
