"""インポーターモジュール共通の定数."""

# 比例代表11ブロック名
PROPORTIONAL_BLOCKS: list[str] = [
    "北海道",
    "東北",
    "北関東",
    "南関東",
    "東京",
    "北陸信越",
    "東海",
    "近畿",
    "中国",
    "四国",
    "九州",
]

# 比例代表PDFファイルURL（総務省main_content）
PROPORTIONAL_PDF_URLS: dict[int, str] = {
    45: "https://www.soumu.go.jp/main_content/000037486.pdf",
    46: "https://www.soumu.go.jp/main_content/000194203.pdf",
    47: "https://www.soumu.go.jp/main_content/000328953.pdf",
    49: "https://www.soumu.go.jp/main_content/000776977.pdf",
    50: "https://www.soumu.go.jp/main_content/000979132.pdf",
}

# 比例代表XLSファイルURL（第48回のみ）
PROPORTIONAL_XLS_URLS: dict[int, str] = {
    48: "https://www.soumu.go.jp/main_content/000516729.xls",
}

# 比例代表対応選挙回次
PROPORTIONAL_SUPPORTED_ELECTIONS: list[int] = [45, 46, 47, 48, 49, 50]

# 都道府県名リスト（コード順、1:北海道〜47:沖縄県）
PREFECTURE_NAMES: list[str] = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]

# Wikipediaカラーコード→政党名フォールバックマッピング（第41-44回衆議院選挙用）
# Wikitext凡例から抽出できない場合に使用する
WIKIPEDIA_COLOR_PARTY_FALLBACK: dict[str, str] = {
    "9E9": "自由民主党",
    "F9B": "民主党",
    "F6C": "新進党",
    "FDF": "公明党",
    "ABD": "自由党",
    "0FF": "社会民主党",
    "F66": "日本共産党",
    "CCF": "新党さきがけ",
    "9CF": "保守党",
    "DDD": "諸派",
    "FFF": "無所属",
    "FA0": "国民新党",
    "FCF": "保守新党",
    "CF9": "新党日本",
    "FF9": "国民民主党",
}
