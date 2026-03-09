-- GovernmentOfficial ↔ Speaker 紐付けシードデータ
-- Generated from database on 2026-03-09
-- 官僚とSpeakerの紐付け（government_official_id, is_politician, skip_reason を更新）
-- 旧字体の表記揺れ（大池眞/大池真、吉國二郎/吉国二郎 等）も含む

UPDATE speakers SET
    government_official_id = 4,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 676 AND name = '大池眞';

UPDATE speakers SET
    government_official_id = 1,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 855 AND name = '佐藤達夫';

UPDATE speakers SET
    government_official_id = 3,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 856 AND name = '平田敬一郎';

UPDATE speakers SET
    government_official_id = 16,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 979 AND name = '下田武三';

UPDATE speakers SET
    government_official_id = 23,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 1210 AND name = '河野通一';

UPDATE speakers SET
    government_official_id = 22,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 1255 AND name = '原純夫';

UPDATE speakers SET
    government_official_id = 9,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 1409 AND name = '小倉武一';

UPDATE speakers SET
    government_official_id = 8,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 1667 AND name = '福田繁';

UPDATE speakers SET
    government_official_id = 20,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 2139 AND name = '柴田護';

UPDATE speakers SET
    government_official_id = 21,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 2296 AND name = '吉國二郎';

UPDATE speakers SET
    government_official_id = 4,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 2968 AND name = '大池真';

UPDATE speakers SET
    government_official_id = 18,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 3408 AND name = '藤井貞夫';

UPDATE speakers SET
    government_official_id = 19,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 3479 AND name = '長野士郎';

UPDATE speakers SET
    government_official_id = 7,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 3819 AND name = '泉美之松';

UPDATE speakers SET
    government_official_id = 5,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 4696 AND name = '磯崎叡';

UPDATE speakers SET
    government_official_id = 6,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 4975 AND name = '渡部伍良';

UPDATE speakers SET
    government_official_id = 21,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 5228 AND name = '吉国二郎';

UPDATE speakers SET
    government_official_id = 2,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 7281 AND name = '高木文雄';

UPDATE speakers SET
    government_official_id = 11,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 7557 AND name = '安原美穂';

UPDATE speakers SET
    government_official_id = 13,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 8198 AND name = '竹内壽平';

UPDATE speakers SET
    government_official_id = 13,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 8327 AND name = '竹内寿平';

UPDATE speakers SET
    government_official_id = 15,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 10163 AND name = '木田宏';

UPDATE speakers SET
    government_official_id = 10,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 12068 AND name = '久保卓也';

UPDATE speakers SET
    government_official_id = 12,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 12906 AND name = '伊藤栄樹';

UPDATE speakers SET
    government_official_id = 5,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 13253 AND name = '磯﨑叡';

UPDATE speakers SET
    government_official_id = 12,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 13997 AND name = '伊藤榮樹';

UPDATE speakers SET
    government_official_id = 14,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 19182 AND name = '塩田章';

UPDATE speakers SET
    government_official_id = 17,
    is_politician = false,
    skip_reason = 'government_official'
WHERE id = 24610 AND name = '黒田東彦';
