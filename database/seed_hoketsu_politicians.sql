-- 参議院議員補欠選挙で新たに必要な政治家 SEED データ
-- Generated from go2senkyo.com on 2026-03-09
-- 既存の seed_politicians_generated.sql に含まれない 31 名
--
-- 注意: 本ファイルを seed_hoketsu_elections.sql より先に実行すること

INSERT INTO politicians (name, prefecture, furigana, district, profile_page_url) VALUES
('前園喜一郎', '鹿児島県', NULL, '鹿児島県', NULL),
('岡元義人', '鹿児島県', NULL, '鹿児島県', NULL),
('溝渕春次', '大阪府', NULL, '大阪府', NULL),
('斉藤昇', '三重県', NULL, '三重県', NULL),
('柴野和喜夫', '石川県', NULL, '石川県', NULL),
('野上進', '熊本県', NULL, '熊本県', NULL),
('北口竜徳', '熊本県', NULL, '熊本県', NULL),
('小宮市太郎', '福岡県', NULL, '福岡県', NULL),
('鈴木一司', '茨城県', NULL, '茨城県', NULL),
('星野重次', '山梨県', NULL, '山梨県', NULL),
('中村登美', '茨城県', NULL, '茨城県', NULL),
('斉藤十朗', '三重県', NULL, '三重県', NULL),
('斉藤寿夫', '静岡県', NULL, '静岡県', NULL),
('君健男', '新潟県', NULL, '新潟県', NULL),
('沓脱タケ子', '大阪府', NULL, '大阪府', NULL),
('林有', '高知県', NULL, '高知県', NULL),
('佐多宗二', '鹿児島県', NULL, '鹿児島県', NULL),
('三浦八水', '熊本県', NULL, '熊本県', NULL),
('藤井孝男', '岐阜県', NULL, '岐阜県', NULL),
('沖外夫', '富山県', NULL, '富山県', NULL),
('添田増太郎', '福島県', NULL, '福島県', NULL),
('重富吉之助', '福岡県', NULL, '福岡県', NULL),
('笠原潤一', '岐阜県', NULL, '岐阜県', NULL),
('岩崎昭弥', '岐阜県', NULL, '岐阜県', NULL),
('上吉原一天', '栃木県', NULL, '栃木県', NULL),
('芦尾長司', '兵庫県', NULL, '兵庫県', NULL),
('黒岩宇洋', '新潟県', NULL, '新潟県', NULL),
('宮口はるこ', '広島県', NULL, '広島県', NULL),
('北村つねお', '山口県', NULL, '山口県', NULL),
('宮本しゅうじ', '石川県', NULL, '石川県', NULL),
('白坂あき', '大分県', NULL, '大分県', NULL)
ON CONFLICT DO NOTHING;
