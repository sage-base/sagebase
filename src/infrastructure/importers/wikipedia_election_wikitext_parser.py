"""Wikipedia衆議院選挙当選者Wikitextのパーサー.

Wikitextテンプレートから当選者データを抽出し、CandidateRecordリストに変換する。
中選挙区: 第1-40回（形式C: wikitable）
小選挙区: 第41回（形式A）と第42-44回（形式B）
比例代表: 第41回（形式A-PR）、第42回（形式B-PR）、第43-44回（wikitable）
"""

import re

from src.domain.value_objects.election_candidate import CandidateRecord
from src.infrastructure.importers._constants import WIKIPEDIA_COLOR_PARTY_FALLBACK
from src.infrastructure.importers._utils import (
    extract_template_content,
    normalize_color,
    normalize_prefecture,
)


# colorboxパターン: {{colorbox|#9E9|自由民主党}}
_COLORBOX_RE = re.compile(
    r"\{\{colorbox\|#?([0-9A-Fa-f]{3,6})\|([^}]+)\}\}",
)

# 政党箱パターン: {{自由民主党}}（色を含まないが政党名テンプレート）
_PARTY_BOX_RE = re.compile(
    r"\{\{政党箱\|#?([0-9A-Fa-f]{3,6})\|([^}]+)\}\}",
)

# wikilink: [[名前]] or [[リンク先|表示名]]
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# 脚注パターン: <ref...>...</ref> or <ref.../>
_REF_TAG_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^/]*/\s*>", re.DOTALL)

# 形式Aの色付きエントリ: "f9b:[[横路孝弘]]"
_FORMAT_A_ENTRY_RE = re.compile(r"([0-9A-Fa-f]{3,6}):(.+)")


def parse_wikitext(wikitext: str, election_number: int) -> list[CandidateRecord]:
    """Wikitextから当選者データを抽出する.

    Args:
        wikitext: Wikipediaから取得したWikitext
        election_number: 選挙回次（1-44）

    Returns:
        CandidateRecordのリスト
    """
    color_to_party = extract_color_party_mapping(wikitext)

    if election_number <= 40:
        return _parse_format_c(wikitext, color_to_party)
    if election_number == 41:
        return _parse_format_a(wikitext, color_to_party)
    return _parse_format_b(wikitext, color_to_party)


def parse_proportional_wikitext(
    wikitext: str,
    election_number: int,
) -> list[CandidateRecord]:
    """Wikitextから比例代表当選者データを抽出する.

    Args:
        wikitext: Wikipediaから取得したWikitext
        election_number: 選挙回次（41-44）

    Returns:
        CandidateRecordのリスト（第40回以前は空リスト）
    """
    # 第40回以前は比例代表なし（中選挙区制）
    if election_number <= 40:
        return []

    color_to_party = extract_color_party_mapping(wikitext)

    if election_number == 41:
        return _parse_proportional_format_a(wikitext, color_to_party)
    if election_number == 42:
        return _parse_proportional_format_b(wikitext, color_to_party)
    # 第43-44回: wikitable形式
    return _parse_proportional_wikitable(wikitext, color_to_party)


def parse_all_wikitext(
    wikitext: str,
    election_number: int,
) -> list[CandidateRecord]:
    """Wikitextから小選挙区+比例代表の全当選者データを抽出する."""
    smd = parse_wikitext(wikitext, election_number)
    pr = parse_proportional_wikitext(wikitext, election_number)
    return smd + pr


def extract_color_party_mapping(wikitext: str) -> dict[str, str]:
    """凡例セクションからカラーコード→政党名マッピングを抽出する."""
    mapping: dict[str, str] = {}

    for match in _COLORBOX_RE.finditer(wikitext):
        color = normalize_color(match.group(1))
        party = match.group(2).strip()
        mapping[color] = party

    for match in _PARTY_BOX_RE.finditer(wikitext):
        color = normalize_color(match.group(1))
        party = match.group(2).strip()
        mapping[color] = party

    return mapping


def extract_name_from_wikilink(text: str) -> str:
    """Wikilinkから名前を抽出する.

    [[名前]] → 名前
    [[リンク先|表示名]] → 表示名
    脚注は除去する。
    """
    text = _remove_ref_tags(text)
    text = _remove_refnest(text)

    match = _WIKILINK_RE.search(text)
    if not match:
        return text.strip()

    content = match.group(1)
    if "|" in content:
        return content.split("|", 1)[1].strip()
    return content.strip()


def _parse_format_a(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """形式Aをパースする（第41回: 都道府県ヘッダ + 位置順リスト）."""
    template_text = extract_template_content(wikitext, "衆院小選挙区当選者")
    if template_text is None:
        return []
    candidates: list[CandidateRecord] = []

    current_pref: str | None = None
    district_counter = 0

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 都道府県ヘッダ: "|北海道=" or "|東京都="
        pref_match = re.match(r"^\|(.+?)=$", line)
        if pref_match:
            pref_name = pref_match.group(1)
            # 「増減」セクションはスキップ
            if "増減" in pref_name:
                current_pref = None
                continue
            current_pref = pref_name
            district_counter = 0
            continue

        if current_pref is None:
            continue

        # 色:[[名前]] エントリ
        entry_match = _FORMAT_A_ENTRY_RE.match(line)
        if entry_match:
            district_counter += 1
            color = normalize_color(entry_match.group(1))
            name_part = entry_match.group(2)
            name = extract_name_from_wikilink(name_part)
            party = _resolve_party(color, color_to_party)
            pref_for_district = normalize_prefecture(current_pref)
            district_name = f"{pref_for_district}{district_counter}区"

            candidates.append(
                CandidateRecord(
                    name=name,
                    party_name=party,
                    district_name=district_name,
                    prefecture=pref_for_district,
                    total_votes=0,
                    rank=1,
                    is_elected=True,
                )
            )

    return candidates


def _parse_format_b(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """形式Bをパースする（第42-44回: 明示的な選挙区名）."""
    template_text = extract_template_content(wikitext, "衆議院小選挙区当選者")
    if template_text is None:
        return []
    candidates: list[CandidateRecord] = []

    # 各行を処理
    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # |{district}色={color}|{district}=[[{name}]] パターンを探す
        # Wikilink内の|を区切りと誤認しないよう、\[\[...\]\]を明示的にマッチ
        entries = re.findall(
            r"\|(.+?)色=([0-9A-Fa-f]{3,6})\|(.+?)=(\[\[.+?\]\][^\|]*)",
            line,
        )

        for _district_color, color, district, name_part in entries:
            color = normalize_color(color)
            name = extract_name_from_wikilink(name_part)
            party = _resolve_party(color, color_to_party)
            pref = _extract_prefecture_from_district(district)

            candidates.append(
                CandidateRecord(
                    name=name,
                    party_name=party,
                    district_name=district,
                    prefecture=pref,
                    total_votes=0,
                    rank=1,
                    is_elected=True,
                )
            )

    return candidates


def _resolve_party(color: str, color_to_party: dict[str, str]) -> str:
    """カラーコードから政党名を解決する."""
    if color in color_to_party:
        return color_to_party[color]
    return WIKIPEDIA_COLOR_PARTY_FALLBACK.get(color, f"不明({color})")


def _extract_prefecture_from_district(district: str) -> str:
    """選挙区名から都道府県名を抽出する.

    例: "北海道1区" → "北海道", "東京都1区" → "東京都"
    """
    match = re.match(r"^(.+?[都道府県])", district)
    if match:
        return match.group(1)
    # 「区」の前の数字を除去して都道府県名を推定
    match = re.match(r"^(.+?)\d+区", district)
    if match:
        return normalize_prefecture(match.group(1))
    return district


def _remove_ref_tags(text: str) -> str:
    """<ref>タグを除去する."""
    return _REF_TAG_RE.sub("", text)


def _remove_refnest(text: str) -> str:
    """{{Refnest|...}} をブレース深度追跡で除去する."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i:].startswith("{{Refnest|") or text[i:].startswith("{{refnest|"):
            # ブレース深度で対応する }}を探す
            depth = 0
            j = i
            while j < len(text):
                if text[j : j + 2] == "{{":
                    depth += 1
                    j += 2
                elif text[j : j + 2] == "}}":
                    depth -= 1
                    j += 2
                    if depth == 0:
                        break
                else:
                    j += 1
            i = j
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


# --- 中選挙区制パーサー（第1-40回） ---

# wikitableセル: background-color + [[名前]]（セミコロン有無両対応）
_WIKITABLE_MEMBER_CELL_RE = re.compile(
    r'style="background-color:#([0-9A-Fa-f]{3,6});?"\s*\|\s*(.+)'
)

# 選挙区ヘッダ: ! [[県名第N区 (中選挙区)|N区]] or !N区 or !札幌 etc.
_DISTRICT_HEADER_WIKILINK_RE = re.compile(
    r"^\!(?:\s*rowspan=\"\d+\"\s*\|)?\s*\[\[(.+?)(?:\|(.+?))?\]\]\s*$"
)
_DISTRICT_HEADER_PLAIN_RE = re.compile(r"^\!(?:\s*rowspan=\"\d+\"\s*\|)?\s*(.+?)\s*$")


def _parse_format_c(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """形式C: 中選挙区制wikitableをパースする（第1-40回）.

    === 当選者 === or == この選挙で当選 == セクション内のwikitable。
    行構造:
    - ! [[都道府県]] — 都道府県ヘッダ
    - ! [[選挙区名|N区]] or !N区 — 選挙区ヘッダ
    - | style="background-color:#色" | [[名前]] — 当選者セル
    """
    # 「当選者」or「この選挙で当選」セクションを探す
    section_match = re.search(
        r"(?:===\s*当選者\s*===|==\s*この選挙で当選\s*==)\s*\n(.*?)(?=\n====|\n===|\n==(?!=)|\Z)",
        wikitext,
        re.DOTALL,
    )
    if not section_match:
        return []

    section_text = section_match.group(1)

    # wikitableを抽出
    table_match = re.search(
        r"\{\|.*?\n(.*?)\|\}",
        section_text,
        re.DOTALL,
    )
    if not table_match:
        return []

    table_text = table_match.group(1)
    candidates: list[CandidateRecord] = []

    current_pref: str | None = None
    current_district: str | None = None

    for line in table_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 行区切り
        if line == "|-":
            continue

        # colspan（空セル）はスキップ
        if line.startswith("| colspan"):
            continue

        # 空セル: | のみ
        if line == "|":
            continue

        # ヘッダ行: !で始まる
        if line.startswith("!"):
            _process_format_c_header(
                line,
                current_pref,
                current_district,
                result := {},
            )
            current_pref = result.get("pref", current_pref)
            current_district = result.get("district", current_district)
            # 同一行にセルが続く場合もある
            # !ヘッダ の後に |cell が続く行がある
            # 例: !1区\n|style=... は改行されるが
            #     !2区 のみの場合もある
            continue

        # 当選者セル
        if line.startswith("|"):
            _process_format_c_cells(
                line,
                current_pref,
                current_district,
                color_to_party,
                candidates,
            )

    return candidates


def _process_format_c_header(
    line: str,
    current_pref: str | None,
    current_district: str | None,
    result: dict[str, str | None],
) -> None:
    """wikitableヘッダ行を処理して都道府県/選挙区を更新する.

    1行に複数のヘッダとセルが混在する場合がある:
    ! [[北海道]] ! [[1区]] |cell |cell ! [[2区]] |cell
    """
    # !で分割して各ヘッダ部分を処理
    parts = re.split(r"(?<!\|)\!", line)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # rowspanなどの属性を除去
        attr_match = re.match(r'(?:rowspan="?\d+"?\s*\|)?\s*(.*)', part)
        if attr_match:
            part = attr_match.group(1).strip()

        if not part:
            continue

        # wikilink付きヘッダ
        wl_match = re.match(r"\[\[(.+?)(?:\|(.+?))?\]\]", part)
        if wl_match:
            full_link = wl_match.group(1)
            display = wl_match.group(2) or full_link

            # 都道府県ヘッダ判定: リンク先が都道府県名のみ
            if _is_prefecture(full_link):
                result["pref"] = full_link
                result["district"] = None
            else:
                # 選挙区ヘッダ: [[県名第N区 (中選挙区)|N区]]
                district_name = _extract_district_from_header(
                    full_link, display, result.get("pref", current_pref)
                )
                result["district"] = district_name
            continue

        # プレーンテキストヘッダ（第1回などのN区形式）
        if re.match(r"\d+区$", part):
            pref = result.get("pref", current_pref)
            if pref:
                result["district"] = f"{pref}{part}"
            continue

        # 地名ヘッダ（第1-9回の「札幌」「函館」等）
        if not part.startswith("|") and _is_prefecture(part):
            result["pref"] = part
            result["district"] = None
        elif not part.startswith("|") and len(part) < 20:
            # 地名ベースの選挙区（第1-9回）
            pref = result.get("pref", current_pref)
            if pref:
                result["district"] = f"{pref}{part}"


def _process_format_c_cells(
    line: str,
    current_pref: str | None,
    current_district: str | None,
    color_to_party: dict[str, str],
    candidates: list[CandidateRecord],
) -> None:
    """wikitableのセル行から当選者を抽出する."""
    # 先頭の|を除去し、セル区切り||で分割
    content = line[1:] if line.startswith("|") else line
    cells = content.split("||")

    for cell_text in cells:
        cell_text = cell_text.strip()
        cell_match = _WIKITABLE_MEMBER_CELL_RE.match(cell_text)
        if cell_match:
            color = normalize_color(cell_match.group(1))
            name_part = cell_match.group(2)
            name = extract_name_from_wikilink(name_part)
            party = _resolve_party(color, color_to_party)

            pref = current_pref or ""
            district = current_district or pref

            candidates.append(
                CandidateRecord(
                    name=name,
                    party_name=party,
                    district_name=district,
                    prefecture=pref,
                    total_votes=0,
                    rank=1,
                    is_elected=True,
                )
            )


_PREFECTURES: frozenset[str] = frozenset(
    {
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
    }
)


def _is_prefecture(name: str) -> bool:
    """文字列が都道府県名かどうかを判定する."""
    return name in _PREFECTURES


def _extract_district_from_header(
    full_link: str,
    display: str,
    current_pref: str | None,
) -> str:
    """選挙区ヘッダのリンクから選挙区名を抽出する.

    例:
    - [[北海道第1区 (中選挙区)|1区]] → "北海道1区"
    - [[東京都第1区 (中選挙区)|1区]] → "東京都1区"
    """
    # リンク先から選挙区名を抽出: "県名第N区 (中選挙区)" → "県名N区"
    m = re.match(r"(.+?)第?(\d+区)", full_link)
    if m:
        pref_part = m.group(1)
        district_num = m.group(2)
        return f"{pref_part}{district_num}"

    # フォールバック: 表示名 + 都道府県
    if current_pref and display:
        return f"{current_pref}{display}"
    return display or full_link


# --- 比例代表パーサー ---

# 比例ブロック略称→正式名マッピング（第42回形式B-PRで使用）
_BLOCK_SHORT_TO_FULL: dict[str, str] = {
    "北海": "比例北海道ブロック",
    "東北": "比例東北ブロック",
    "北関": "比例北関東ブロック",
    "南関": "比例南関東ブロック",
    "東京": "比例東京ブロック",
    "北信": "比例北陸信越ブロック",
    "東海": "比例東海ブロック",
    "近畿": "比例近畿ブロック",
    "中国": "比例中国ブロック",
    "四国": "比例四国ブロック",
    "九州": "比例九州ブロック",
}

# wikitableヘッダからブロック名抽出: [[比例北海道ブロック|北海道]]
_WIKITABLE_BLOCK_HEADER_RE = re.compile(r"\[\[比例(.+?)ブロック\|(.+?)\]\]")

# wikitableセル: |style="background-color:#f9b"|[[名前]]
_WIKITABLE_CELL_RE = re.compile(r'style="background-color:#([0-9A-Fa-f]{3,6})"\|(.+)')


def _parse_proportional_format_a(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """第41回比例代表テンプレートをパースする.

    形式: {{衆院比例当選者 ... }}
    ブロック別セクション（|北海道定数=N |北海道= ...）に色:[[名前]]リスト。
    """
    template_text = extract_template_content(wikitext, "衆院比例当選者")
    if template_text is None:
        return []

    candidates: list[CandidateRecord] = []

    current_block: str | None = None
    rank_counter = 0

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # ブロック定数ヘッダ: |北海道定数=9
        if re.match(r"^\|.+?定数=\d+", line):
            continue

        # ブロック名ヘッダ: |北海道= or |東北=
        block_match = re.match(r"^\|(.+?)=$", line)
        if block_match:
            block_name = block_match.group(1)
            if "増減" in block_name:
                current_block = None
                continue
            current_block = f"比例{block_name}ブロック"
            rank_counter = 0
            continue

        if current_block is None:
            continue

        entry_match = _FORMAT_A_ENTRY_RE.match(line)
        if entry_match:
            rank_counter += 1
            color = normalize_color(entry_match.group(1))
            name_part = entry_match.group(2)
            name = extract_name_from_wikilink(name_part)
            party = _resolve_party(color, color_to_party)

            candidates.append(
                CandidateRecord(
                    name=name,
                    party_name=party,
                    district_name=current_block,
                    prefecture=current_block,
                    total_votes=0,
                    rank=rank_counter,
                    is_elected=True,
                )
            )

    return candidates


def _parse_proportional_format_b(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """第42回比例代表テンプレートをパースする.

    形式: {{衆議院当選者一覧(比例区) ... }}
    |{block略称}{n}色={color}|{block略称}{n}=[[名前]]
    """
    template_text = extract_template_content(wikitext, "衆議院当選者一覧(比例区)")
    if template_text is None:
        return []

    candidates: list[CandidateRecord] = []

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        entries = re.findall(
            r"\|(.+?)(\d+)色=([0-9A-Fa-f]{3,6})\|(.+?)\d+=(\[\[.+?\]\][^\|]*)",
            line,
        )

        for block_short, rank_str, color, _block2, name_part in entries:
            color = normalize_color(color)
            name = extract_name_from_wikilink(name_part)
            party = _resolve_party(color, color_to_party)
            block_full = _BLOCK_SHORT_TO_FULL.get(
                block_short, f"比例{block_short}ブロック"
            )
            rank = int(rank_str)

            candidates.append(
                CandidateRecord(
                    name=name,
                    party_name=party,
                    district_name=block_full,
                    prefecture=block_full,
                    total_votes=0,
                    rank=rank,
                    is_elected=True,
                )
            )

    return candidates


def _parse_proportional_wikitable(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """第43-44回比例代表wikitableをパースする.

    形式: === 比例区当選者 === セクション内のwikitable。
    ヘッダ行でブロック名（列）を取得。各行は1セル=1行で、行内の位置順=列番号。
    """
    section_match = re.search(
        r"===\s*比例区当選者\s*===\s*\n(.*?)(?=\n==|\Z)",
        wikitext,
        re.DOTALL,
    )
    if not section_match:
        return []

    section_text = section_match.group(1)

    table_match = re.search(
        r"\{\|.*?\n(.*?)\|\}",
        section_text,
        re.DOTALL,
    )
    if not table_match:
        return []

    table_text = table_match.group(1)

    # ヘッダ行からブロック名を抽出
    blocks: list[str] = []
    for line in table_text.split("\n"):
        if line.startswith("!"):
            for m in _WIKITABLE_BLOCK_HEADER_RE.finditer(line):
                full_name = m.group(1)
                blocks.append(f"比例{full_name}ブロック")
            if blocks:
                break

    if not blocks:
        return []

    candidates: list[CandidateRecord] = []
    current_rank = 0
    col_index = 0

    for line in table_text.split("\n"):
        line = line.strip()

        if line == "|-":
            col_index = 0
            continue

        rank_match = re.match(r"^!(\d+)$", line)
        if rank_match:
            current_rank = int(rank_match.group(1))
            col_index = 0
            continue

        if line == "!":
            current_rank = 0
            continue

        if current_rank == 0:
            continue

        if not line.startswith("|"):
            continue

        # セル行を処理: 先頭の|を除去し、||で分割
        row_content = line[1:]  # 先頭の|を除去
        cells = row_content.split("||")

        for cell_text in cells:
            cell_text = cell_text.strip()
            cell_match = re.match(
                r'style="background-color:#([0-9A-Fa-f]{3,6})"\|(.+)',
                cell_text,
            )
            if cell_match and col_index < len(blocks):
                color = normalize_color(cell_match.group(1))
                name_part = cell_match.group(2)
                name = extract_name_from_wikilink(name_part)
                party = _resolve_party(color, color_to_party)
                block = blocks[col_index]

                candidates.append(
                    CandidateRecord(
                        name=name,
                        party_name=party,
                        district_name=block,
                        prefecture=block,
                        total_votes=0,
                        rank=current_rank,
                        is_elected=True,
                    )
                )
            col_index += 1

    return candidates
