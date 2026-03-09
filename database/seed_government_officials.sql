-- GovernmentOfficial（非政治家・官僚）シードデータ
-- Generated from database on 2026-03-09
-- 国会議事録に登場する官僚（政府委員・参考人等）の初期データ

INSERT INTO government_officials (id, name) VALUES
    (1, '佐藤達夫'),
    (2, '高木文雄'),
    (3, '平田敬一郎'),
    (4, '大池眞'),
    (5, '磯崎叡'),
    (6, '渡部伍良'),
    (7, '泉美之松'),
    (8, '福田繁'),
    (9, '小倉武一'),
    (10, '久保卓也'),
    (11, '安原美穂'),
    (12, '伊藤榮樹'),
    (13, '竹内壽平'),
    (14, '塩田章'),
    (15, '木田宏'),
    (16, '下田武三'),
    (17, '黒田東彦'),
    (18, '藤井貞夫'),
    (19, '長野士郎'),
    (20, '柴田護'),
    (21, '吉國二郎'),
    (22, '原純夫'),
    (23, '河野通一')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name;

-- シーケンスを最大ID+1にリセット
SELECT setval('government_officials_id_seq',
    COALESCE((SELECT MAX(id) FROM government_officials), 0) + 1, false);
