"""名前正規化サービス.

旧字体→新字体変換、Unicode NFKC正規化、敬称除去、
ひらがな混じり名からの漢字姓抽出を提供する。
"""

import re
import unicodedata


# 末尾から除去する敬称（長い順にソート）
_HONORIFICS = sorted(
    [
        "副委員長",
        "委員長",
        "副議長",
        "議長",
        "副市長",
        "市長",
        "副知事",
        "知事",
        "議員",
        "先生",
        "殿",
        "氏",
        "さん",
        "くん",
        "君",
        "様",
    ],
    key=len,
    reverse=True,
)

# 旧字体→新字体変換テーブル（政治家名で出現頻度の高い文字）
_KYUJITAI_TO_SHINJITAI: dict[str, str] = {
    "櫻": "桜",
    "齋": "斎",
    "齊": "斉",
    "髙": "高",
    "﨑": "崎",
    "邊": "辺",
    "邉": "辺",
    "澤": "沢",
    "濱": "浜",
    "廣": "広",
    "國": "国",
    "圀": "国",
    "實": "実",
    "寶": "宝",
    "壽": "寿",
    "學": "学",
    "藝": "芸",
    "應": "応",
    "惠": "恵",
    "德": "徳",
    "榮": "栄",
    "禮": "礼",
    "靈": "霊",
    "靜": "静",
    "龍": "竜",
    "瀨": "瀬",
    "黑": "黒",
    "與": "与",
    "亞": "亜",
    "佛": "仏",
    "假": "仮",
    "僞": "偽",
    "傳": "伝",
    "會": "会",
    "鐵": "鉄",
    "藏": "蔵",
    "盡": "尽",
    "嶋": "島",
    "嶌": "島",
    "條": "条",
    "總": "総",
    "縣": "県",
    "顯": "顕",
    "辯": "弁",
    "瓣": "弁",
    "辨": "弁",
    "戶": "戸",
    "淵": "渕",
    "曾": "曽",
    "豐": "豊",
    "兒": "児",
    "單": "単",
    "參": "参",
    "壹": "壱",
    "獨": "独",
    "臺": "台",
    "晝": "昼",
    "氣": "気",
    "經": "経",
    "營": "営",
    "勞": "労",
    "圖": "図",
    "團": "団",
    "廳": "庁",
    "盜": "盗",
    "觀": "観",
    "聲": "声",
    "體": "体",
    "轉": "転",
    "號": "号",
    "點": "点",
    "關": "関",
    "顏": "顔",
    "驛": "駅",
    "鑛": "鉱",
    "滿": "満",
    "萬": "万",
}

_TRANSLATE_TABLE = str.maketrans(_KYUJITAI_TO_SHINJITAI)

# ひらがな文字の範囲
_HIRAGANA_RE = re.compile(r"[ぁ-ん]")

# CJK統合漢字の範囲（基本ブロック + 拡張A）
_KANJI_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# 姓の構成文字（漢字 + 姓に出現する特殊文字）
# 々: 踊り字（佐々木、野々村）
# ヶ/ケ: 竹ヶ原、一ヶ谷
# ッ/ツ: 三ッ林、三ツ矢
# ノ: 一ノ瀬
_SURNAME_CHAR_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf々ヶケッツノ]")

# 全角・半角スペース除去（各メソッドで共有）
_WHITESPACE_RE = re.compile(r"[\s\u3000]+")


class NameNormalizer:
    """名前正規化サービス."""

    @staticmethod
    def normalize(name: str) -> str:
        """名前を正規化する.

        処理順序:
        1. Unicode NFKC正規化（全角英数→半角、異体字統合）
        2. 旧字体→新字体変換
        3. 全角・半角スペース除去
        4. 敬称除去
        """
        normalized = name.strip()
        # 1. Unicode NFKC正規化
        normalized = unicodedata.normalize("NFKC", normalized)
        # 2. 旧字体→新字体変換
        normalized = normalized.translate(_TRANSLATE_TABLE)
        # 3. スペース除去
        normalized = _WHITESPACE_RE.sub("", normalized)
        # 4. 敬称除去
        for honorific in _HONORIFICS:
            if normalized.endswith(honorific):
                normalized = normalized[: -len(honorific)]
                break
        return normalized.strip()

    @staticmethod
    def extract_kanji_surname(name: str) -> str:
        """ひらがな混じり名から先頭の連続漢字部分（姓）を抽出する.

        漢字に加え、姓に出現する特殊文字（々、ヶ、ッ、ツ、ノ）も含める。

        例:
            "武村のぶひで" → "武村"
            "佐々木はじめ" → "佐々木"
            "三ッ林ひろみ" → "三ッ林"
            "岸田文雄" → "岸田文雄"（全部漢字ならそのまま）
            "たけむら" → ""（先頭が漢字でなければ空文字）
        """
        # スペース除去
        cleaned = _WHITESPACE_RE.sub("", name)
        # 先頭が漢字でなければ空文字
        if not cleaned or not _KANJI_RE.match(cleaned[0]):
            return ""
        result: list[str] = []
        for char in cleaned:
            if _SURNAME_CHAR_RE.match(char):
                result.append(char)
            else:
                break
        return "".join(result)

    @staticmethod
    def has_mixed_hiragana(name: str) -> bool:
        """名前に漢字とひらがなが混在しているか判定する."""
        cleaned = _WHITESPACE_RE.sub("", name)
        has_kanji = bool(_KANJI_RE.search(cleaned))
        has_hiragana = bool(_HIRAGANA_RE.search(cleaned))
        return has_kanji and has_hiragana

    @staticmethod
    def normalize_kana(kana: str) -> str:
        """ふりがなを正規化する（NFKC正規化、カタカナ→ひらがな変換、スペース除去）."""
        normalized = kana.strip()
        normalized = unicodedata.normalize("NFKC", normalized)
        normalized = _WHITESPACE_RE.sub("", normalized)
        # カタカナをひらがなに変換
        result: list[str] = []
        for char in normalized:
            code = ord(char)
            # カタカナ範囲(0x30A1-0x30F6)をひらがな(0x3041-0x3096)に変換
            if 0x30A1 <= code <= 0x30F6:
                result.append(chr(code - 0x60))
            else:
                result.append(char)
        return "".join(result)
