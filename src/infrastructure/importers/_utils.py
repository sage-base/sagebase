"""インポーターモジュール共通のユーティリティ関数."""

import json
import re

from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# 和暦→西暦変換
WAREKI_MAP: dict[str, int] = {
    "令和": 2018,
    "平成": 1988,
    "昭和": 1925,
    "大正": 1911,
    "明治": 1867,
}


_WIKIPEDIA_API_URL = "https://ja.wikipedia.org/w/api.php"
_WIKIPEDIA_USER_AGENT = (
    "SagebaseBot/1.0 (political-activity-tracker; contact@example.com)"
)


def extract_template_content(wikitext: str, template_prefix: str) -> str | None:
    """ブレース深度追跡でテンプレート内容を抽出する.

    {{Refnest|...}}等のネストされたテンプレートを正しくスキップする。
    """
    start = wikitext.find("{{" + template_prefix)
    if start == -1:
        return None

    # テンプレート名の後（改行またはパイプ）からコンテンツ開始
    content_start = start + len("{{" + template_prefix)

    depth = 1
    i = content_start
    while i < len(wikitext):
        if wikitext[i : i + 2] == "{{":
            depth += 1
            i += 2
        elif wikitext[i : i + 2] == "}}":
            depth -= 1
            if depth == 0:
                return wikitext[content_start:i]
            i += 2
        else:
            i += 1

    return None


def normalize_color(color: str) -> str:
    """カラーコードを正規化（大文字化、#除去）."""
    return color.lstrip("#").upper()


def normalize_prefecture(name: str) -> str:
    """都道府県名に接尾辞を補完する（「都」「道」「府」「県」の補完）."""
    if name in ("北海道",):
        return name
    if name in ("東京", "東京都"):
        return "東京都"
    if name in ("大阪", "大阪府"):
        return "大阪府"
    if name in ("京都", "京都府"):
        return "京都府"
    if name.endswith(("都", "道", "府", "県")):
        return name
    return name + "県"


def fetch_wikipedia_wikitext(page_title: str) -> str:
    """Wikipedia APIからWikitextを取得する（同期）."""
    params = urlencode(
        {
            "action": "parse",
            "page": page_title,
            "prop": "wikitext",
            "format": "json",
        }
    )
    url = f"{_WIKIPEDIA_API_URL}?{params}"

    req = Request(url, headers={"User-Agent": _WIKIPEDIA_USER_AGENT})
    with urlopen(req, timeout=30) as response:  # nosec B310 — URLはhttpsハードコード
        data = json.loads(response.read().decode("utf-8"))

    if "error" in data:
        msg = f"Wikipedia API error: {data['error'].get('info', 'unknown')}"
        raise RuntimeError(msg)

    return data["parse"]["wikitext"]["*"]


def zen_to_han(text: str) -> str:
    """全角数字・記号を半角に変換する."""
    zen = "０１２３４５６７８９．"
    han = "0123456789."
    table = str.maketrans(zen, han)
    return text.translate(table)


def parse_wareki_date(text: str) -> date | None:
    """和暦の日付文字列を西暦dateに変換する.

    例: "令和６年１０月２７日執行" → date(2024, 10, 27)
    「元年」は1年として扱う。元号と数字の間のスペースも許容する。
    """
    if not text:
        return None
    text = zen_to_han(str(text))
    pattern = r"(令和|平成|昭和|大正|明治)\s*(元|\d+)年\s*(\d+)月\s*(\d+)日"
    match = re.search(pattern, text)
    if not match:
        return None
    era, year_str, month_str, day_str = match.groups()
    base_year = WAREKI_MAP.get(era)
    if base_year is None:
        return None
    year = base_year + (1 if year_str == "元" else int(year_str))
    try:
        return date(year, int(month_str), int(day_str))
    except ValueError:
        return None
