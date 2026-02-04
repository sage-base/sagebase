-- Generated from database on 2025-09-13 01:38:32
-- conferences seed data

INSERT INTO conferences (name, governing_body_id, members_introduction_url) VALUES
-- 開催主体未設定
('静岡市議会', NULL, 'https://www.city.shizuoka.lg.jp/gikai/s900078.html'),

-- 日本国 (国)
('参議院', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/giin/217/giin.htm'),
('参議院予算委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0027.htm'),
('参議院内閣委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0063.htm'),
('参議院厚生労働委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0069.htm'),
('参議院国土交通委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0072.htm'),
('参議院外交防衛委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0066.htm'),
('参議院懲罰委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0031.htm'),
('参議院文教科学委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0068.htm'),
('参議院本会議', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), NULL),
('参議院決算委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0028.htm'),
('参議院法務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0065.htm'),
('参議院環境委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0073.htm'),
('参議院経済産業委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0071.htm'),
('参議院総務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0064.htm'),
('参議院行政監視委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0061.htm'),
('参議院議院運営委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0029.htm'),
('参議院財政金融委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0067.htm'),
('参議院農林水産委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0070.htm'),
('国会合同審査会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), NULL),
('国政調査特別委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), NULL),
('衆議院', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/1giin.htm'),
('衆議院予算委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0140.htm'),
('衆議院内閣委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0010.htm'),
('衆議院厚生労働委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0070.htm'),
('衆議院国土交通委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0100.htm'),
('衆議院外務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0040.htm'),
('衆議院安全保障委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0120.htm'),
('衆議院懲罰委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0170.htm'),
('衆議院文部科学委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0060.htm'),
('衆議院本会議', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), NULL),
('衆議院決算行政監視委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0150.htm'),
('衆議院法務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0030.htm'),
('衆議院環境委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0110.htm'),
('衆議院経済産業委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0090.htm'),
('衆議院総務委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0020.htm'),
('衆議院議院運営委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0160.htm'),
('衆議院財務金融委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0050.htm'),
('衆議院農林水産委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0080.htm'),

-- 兵庫県 (都道府県)
('兵庫県議会', (SELECT id FROM governing_bodies WHERE name = '兵庫県' AND type = '都道府県'), 'https://web.pref.hyogo.lg.jp/gikai/giinshokai/shokai/50on/50on_ichiran23.html'),

-- 北海道 (都道府県)
('北海道議会', (SELECT id FROM governing_bodies WHERE name = '北海道' AND type = '都道府県'), 'https://www.gikai.pref.hokkaido.lg.jp/meibo/pdf-index.html'),

-- 千葉県 (都道府県)
('千葉県議会', (SELECT id FROM governing_bodies WHERE name = '千葉県' AND type = '都道府県'), 'https://www.pref.chiba.lg.jp/gikai/giji/giin/giinshoukai/index.html'),

-- 埼玉県 (都道府県)
('埼玉県議会', (SELECT id FROM governing_bodies WHERE name = '埼玉県' AND type = '都道府県'), 'https://www.pref.saitama.lg.jp/e1601/gikai-member-50on.html'),

-- 大阪府 (都道府県)
('大阪府議会', (SELECT id FROM governing_bodies WHERE name = '大阪府' AND type = '都道府県'), 'https://www.pref.osaka.lg.jp/o170010/gikai_somu/sugatami20/index50.html'),

-- 愛知県 (都道府県)
('愛知県議会', (SELECT id FROM governing_bodies WHERE name = '愛知県' AND type = '都道府県'), 'https://www.pref.aichi.jp/gikai/syoukai/'),

-- 東京都 (都道府県)
('東京都議会', (SELECT id FROM governing_bodies WHERE name = '東京都' AND type = '都道府県'), 'https://www.gikai.metro.tokyo.lg.jp/membership/japanese-syllabary.html'),

-- 神奈川県 (都道府県)
('神奈川県議会', (SELECT id FROM governing_bodies WHERE name = '神奈川県' AND type = '都道府県'), 'https://www.pref.kanagawa.jp/gikai/p80005.html'),

-- 福岡県 (都道府県)
('福岡県議会', (SELECT id FROM governing_bodies WHERE name = '福岡県' AND type = '都道府県'), 'https://www.gikai.pref.fukuoka.lg.jp/site/giin/all.html'),

-- 静岡県 (都道府県)
('静岡県議会', (SELECT id FROM governing_bodies WHERE name = '静岡県' AND type = '都道府県'), 'https://www.pref.shizuoka.jp/kensei/kengikai/giinshokai/1068855/index.html'),

-- 世田谷区 (市町村)
('世田谷区議会', (SELECT id FROM governing_bodies WHERE name = '世田谷区' AND type = '市町村'), 'https://www.city.setagaya.lg.jp/02030/9461.html'),

-- 中央区 (市町村)
('中央区議会', (SELECT id FROM governing_bodies WHERE name = '中央区' AND type = '市町村'), 'https://www.kugikai.city.chuo.lg.jp/kugikai/meibo.html'),

-- 中野区 (市町村)
('中野区議会', (SELECT id FROM governing_bodies WHERE name = '中野区' AND type = '市町村'), 'https://kugikai-nakano.jp/giin_list.html'),

-- 京都府京都市 (市町村)
('まちづくり委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/iinkai/jounin.html'),
('京都市議会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/gojuon.html'),
('文教はぐくみ委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/iinkai/jounin.html'),
('環境福祉委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/iinkai/jounin.html'),
('産業交通水道委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/iinkai/jounin.html'),
('総務消防委員会', (SELECT id FROM governing_bodies WHERE name = '京都府京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/iinkai/jounin.html'),

-- 北区 (市町村)
('北区議会', (SELECT id FROM governing_bodies WHERE name = '北区' AND type = '市町村'), 'https://www.city.kita.lg.jp/assembly/members/1020017.html'),

-- 千代田区 (市町村)
('千代田区議会', (SELECT id FROM governing_bodies WHERE name = '千代田区' AND type = '市町村'), 'https://gikai-chiyoda-tokyo.jp/about/giin/index.html'),

-- 台東区 (市町村)
('台東区議会', (SELECT id FROM governing_bodies WHERE name = '台東区' AND type = '市町村'), 'https://taito.gijiroku.com/voices/g07_giinlistP.asp'),

-- 品川区 (市町村)
('品川区議会', (SELECT id FROM governing_bodies WHERE name = '品川区' AND type = '市町村'), 'https://gikai.city.shinagawa.tokyo.jp/profile/50on'),

-- 墨田区 (市町村)
('墨田区議会', (SELECT id FROM governing_bodies WHERE name = '墨田区' AND type = '市町村'), 'https://www.city.sumida.lg.jp/kugikai/kousei/giinmeibo06.html'),

-- 大田区 (市町村)
('大田区議会', (SELECT id FROM governing_bodies WHERE name = '大田区' AND type = '市町村'), 'https://www.city.ota.tokyo.jp/gikai/shoukai/giinsyokai.html'),

-- 文京区 (市町村)
('文京区議会', (SELECT id FROM governing_bodies WHERE name = '文京区' AND type = '市町村'), 'https://www.city.bunkyo.lg.jp/kugikai/p007041.html'),

-- 新宿区 (市町村)
('新宿区議会', (SELECT id FROM governing_bodies WHERE name = '新宿区' AND type = '市町村'), 'https://www.city.shinjuku.lg.jp/kusei/gikai01_000112.html'),

-- 杉並区 (市町村)
('杉並区議会', (SELECT id FROM governing_bodies WHERE name = '杉並区' AND type = '市町村'), 'https://suginami.gijiroku.com/voices/g07_giinlist_s.asp'),

-- 板橋区 (市町村)
('板橋区議会', (SELECT id FROM governing_bodies WHERE name = '板橋区' AND type = '市町村'), 'https://www.city.itabashi.tokyo.jp/kugikai/giin/1010916.html'),

-- 江戸川区 (市町村)
('江戸川区議会', (SELECT id FROM governing_bodies WHERE name = '江戸川区' AND type = '市町村'), 'https://www.gikai.city.edogawa.tokyo.jp/g07_giinlistP.asp'),

-- 江東区 (市町村)
('江東区議会', (SELECT id FROM governing_bodies WHERE name = '江東区' AND type = '市町村'), 'https://www.city.koto.lg.jp/kuse/kugikai/shokai/gisekijun/index.html'),

-- 渋谷区 (市町村)
('渋谷区議会', (SELECT id FROM governing_bodies WHERE name = '渋谷区' AND type = '市町村'), 'https://shibukugi.tokyo/giin/2023012400017/'),

-- 港区 (市町村)
('港区議会', (SELECT id FROM governing_bodies WHERE name = '港区' AND type = '市町村'), 'https://gikai2.city.minato.tokyo.jp/g07_giinlist_s.asp'),

-- 目黒区 (市町村)
('目黒区議会', (SELECT id FROM governing_bodies WHERE name = '目黒区' AND type = '市町村'), 'https://www.city.meguro.tokyo.jp/kugikai/kusei/kugikai/giseki_jun.html'),

-- 練馬区 (市町村)
('練馬区議会', (SELECT id FROM governing_bodies WHERE name = '練馬区' AND type = '市町村'), 'https://www.city.nerima.tokyo.jp/gikai/giin/50on/index.html'),

-- 荒川区 (市町村)
('荒川区議会', (SELECT id FROM governing_bodies WHERE name = '荒川区' AND type = '市町村'), 'https://www.city.arakawa.tokyo.jp/a053/gikaisenkyo/kugikai/giinmeibo.html'),

-- 葛飾区 (市町村)
('葛飾区議会', (SELECT id FROM governing_bodies WHERE name = '葛飾区' AND type = '市町村'), 'https://smart.discussvision.net/smart/tenant/katsushika/WebView/rd/speaker.html'),

-- 豊島区 (市町村)
('豊島区議会', (SELECT id FROM governing_bodies WHERE name = '豊島区' AND type = '市町村'), 'https://www.city.toshima.lg.jp/366/kuse/gikai/ginichiran/mebo/2404241622.html'),

-- 足立区 (市町村)
('足立区議会', (SELECT id FROM governing_bodies WHERE name = '足立区' AND type = '市町村'), 'https://www.gikai-adachi.jp/g07_giinlist_s.asp')
ON CONFLICT (name, governing_body_id) DO NOTHING;
