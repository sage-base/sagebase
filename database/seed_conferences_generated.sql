-- Generated from database on 2025-09-13 01:38:32
-- conferences seed data
-- Updated: members_introduction_url カラム削除に対応 (Issue #1119)

INSERT INTO conferences (name, governing_body_id) VALUES
-- 開催主体未設定
('静岡市議会', NULL),

-- 日本国 (国)
('参議院', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院予算委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院内閣委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院厚生労働委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院国土交通委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院外交防衛委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院懲罰委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院文教科学委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院本会議', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院決算委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院法務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院環境委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院経済産業委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院総務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院行政監視委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院議院運営委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院財政金融委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('参議院農林水産委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('国会合同審査会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('国政調査特別委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院予算委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院内閣委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院厚生労働委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院国土交通委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院外務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院安全保障委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院懲罰委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院文部科学委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院本会議', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院決算行政監視委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院法務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院環境委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院経済産業委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院総務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院議院運営委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院財務金融委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),
('衆議院農林水産委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国')),

-- 兵庫県 (都道府県)
('兵庫県議会', (SELECT id FROM governing_bodies WHERE name = '兵庫県' AND type = '都道府県')),

-- 北海道 (都道府県)
('北海道議会', (SELECT id FROM governing_bodies WHERE name = '北海道' AND type = '都道府県')),

-- 千葉県 (都道府県)
('千葉県議会', (SELECT id FROM governing_bodies WHERE name = '千葉県' AND type = '都道府県')),

-- 埼玉県 (都道府県)
('埼玉県議会', (SELECT id FROM governing_bodies WHERE name = '埼玉県' AND type = '都道府県')),

-- 大阪府 (都道府県)
('大阪府議会', (SELECT id FROM governing_bodies WHERE name = '大阪府' AND type = '都道府県')),

-- 愛知県 (都道府県)
('愛知県議会', (SELECT id FROM governing_bodies WHERE name = '愛知県' AND type = '都道府県')),

-- 東京都 (都道府県)
('東京都議会', (SELECT id FROM governing_bodies WHERE name = '東京都' AND type = '都道府県')),

-- 神奈川県 (都道府県)
('神奈川県議会', (SELECT id FROM governing_bodies WHERE name = '神奈川県' AND type = '都道府県')),

-- 福岡県 (都道府県)
('福岡県議会', (SELECT id FROM governing_bodies WHERE name = '福岡県' AND type = '都道府県')),

-- 静岡県 (都道府県)
('静岡県議会', (SELECT id FROM governing_bodies WHERE name = '静岡県' AND type = '都道府県')),

-- 世田谷区 (市町村)
('世田谷区議会', (SELECT id FROM governing_bodies WHERE name = '世田谷区' AND type = '市町村')),

-- 中央区 (市町村)
('中央区議会', (SELECT id FROM governing_bodies WHERE name = '中央区' AND type = '市町村')),

-- 中野区 (市町村)
('中野区議会', (SELECT id FROM governing_bodies WHERE name = '中野区' AND type = '市町村')),

-- 京都府京都市 (市町村)
('まちづくり委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')),
('京都市議会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')),
('文教はぐくみ委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')),
('環境福祉委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')),
('産業交通水道委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')),
('総務消防委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村')),

-- 北区 (市町村)
('北区議会', (SELECT id FROM governing_bodies WHERE name = '北区' AND type = '市町村')),

-- 千代田区 (市町村)
('千代田区議会', (SELECT id FROM governing_bodies WHERE name = '千代田区' AND type = '市町村')),

-- 台東区 (市町村)
('台東区議会', (SELECT id FROM governing_bodies WHERE name = '台東区' AND type = '市町村')),

-- 品川区 (市町村)
('品川区議会', (SELECT id FROM governing_bodies WHERE name = '品川区' AND type = '市町村')),

-- 墨田区 (市町村)
('墨田区議会', (SELECT id FROM governing_bodies WHERE name = '墨田区' AND type = '市町村')),

-- 大田区 (市町村)
('大田区議会', (SELECT id FROM governing_bodies WHERE name = '大田区' AND type = '市町村')),

-- 文京区 (市町村)
('文京区議会', (SELECT id FROM governing_bodies WHERE name = '文京区' AND type = '市町村')),

-- 新宿区 (市町村)
('新宿区議会', (SELECT id FROM governing_bodies WHERE name = '新宿区' AND type = '市町村')),

-- 杉並区 (市町村)
('杉並区議会', (SELECT id FROM governing_bodies WHERE name = '杉並区' AND type = '市町村')),

-- 板橋区 (市町村)
('板橋区議会', (SELECT id FROM governing_bodies WHERE name = '板橋区' AND type = '市町村')),

-- 江戸川区 (市町村)
('江戸川区議会', (SELECT id FROM governing_bodies WHERE name = '江戸川区' AND type = '市町村')),

-- 江東区 (市町村)
('江東区議会', (SELECT id FROM governing_bodies WHERE name = '江東区' AND type = '市町村')),

-- 渋谷区 (市町村)
('渋谷区議会', (SELECT id FROM governing_bodies WHERE name = '渋谷区' AND type = '市町村')),

-- 港区 (市町村)
('港区議会', (SELECT id FROM governing_bodies WHERE name = '港区' AND type = '市町村')),

-- 目黒区 (市町村)
('目黒区議会', (SELECT id FROM governing_bodies WHERE name = '目黒区' AND type = '市町村')),

-- 練馬区 (市町村)
('練馬区議会', (SELECT id FROM governing_bodies WHERE name = '練馬区' AND type = '市町村')),

-- 荒川区 (市町村)
('荒川区議会', (SELECT id FROM governing_bodies WHERE name = '荒川区' AND type = '市町村')),

-- 葛飾区 (市町村)
('葛飾区議会', (SELECT id FROM governing_bodies WHERE name = '葛飾区' AND type = '市町村')),

-- 豊島区 (市町村)
('豊島区議会', (SELECT id FROM governing_bodies WHERE name = '豊島区' AND type = '市町村')),

-- 足立区 (市町村)
('足立区議会', (SELECT id FROM governing_bodies WHERE name = '足立区' AND type = '市町村'))
ON CONFLICT (name, governing_body_id) DO NOTHING;
