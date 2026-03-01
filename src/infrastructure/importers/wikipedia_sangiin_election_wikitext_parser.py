"""Wikipedia参議院選挙当選者Wikitextのパーサー.

Wikitextテンプレート/wikitableから当選者データを抽出し、CandidateRecordリストに変換する。

選挙区（地方区）パターン:
  - テンプレート形式: {{参院選挙区当選者}} — 都道府県=色:[[名前]]
  - wikitable形式: style="background-color:#色" | [[名前]] + ヘッダ
比例代表（全国区）パターン:
  - テンプレート形式: {{参院比例当選者}} — 色:[[名前]][:特定枠]
  - wikitable形式: 順位行(!1-10) + 背景色セル
"""

import re

from src.domain.value_objects.election_candidate import CandidateRecord
from src.infrastructure.importers._constants import (
    WIKIPEDIA_COLOR_PARTY_FALLBACK,
    WIKIPEDIA_SANGIIN_COLOR_PARTY_FALLBACK,
)
from src.infrastructure.importers.wikipedia_election_wikitext_parser import (
    extract_color_party_mapping,
    extract_name_from_wikilink,
)


def _extract_template_content(wikitext: str, template_prefix: str) -> str | None:
    """ブレース深度追跡でテンプレート内容を抽出する."""
    start = wikitext.find("{{" + template_prefix)
    if start == -1:
        return None

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


def _normalize_color(color: str) -> str:
    """カラーコードを正規化（大文字化、#除去）."""
    return color.lstrip("#").upper()


# 色:[[名前]] エントリ（テンプレート内で使用）
_ENTRY_RE = re.compile(r"([0-9A-Fa-f]{3,6}):(.+)")

# wikitableセル: background-color + [[名前]]（セミコロン有無両対応）
_WIKITABLE_CELL_RE = re.compile(
    r'style="background-color:#([0-9A-Fa-f]{3,6});?(?:[^"]*)?"\s*\|\s*(.+)'
)

# 選挙区名抽出: [[北海道選挙区|北海道]] 等
_DISTRICT_WIKILINK_RE = re.compile(r"\[\[(.+?)(?:\|(.+?))?\]\]")

# セクション見出しパターン（選挙区）
_DISTRICT_SECTION_RE = re.compile(
    r"===?\s*(?:地方区当選者|選挙区当選者|この選挙で(?:選挙区|地方区)当選)\s*===?",
)

# セクション見出しパターン（全国区/比例区）
_PROPORTIONAL_SECTION_RE = re.compile(
    r"===?\s*(?:全国区当選者|比例区当選者|比例代表選出議員|"
    r"この選挙で(?:全国区|比例区|比例代表)当選|"
    r"比例代表当選者)\s*===?",
)


def parse_sangiin_wikitext(
    wikitext: str,
    election_number: int,
) -> list[CandidateRecord]:
    """参議院選挙のWikitextから選挙区+比例/全国区の全当選者を抽出する."""
    color_to_party = _build_color_to_party(wikitext)

    district = _parse_district_winners(wikitext, election_number, color_to_party)
    proportional = _parse_proportional_winners(
        wikitext, election_number, color_to_party
    )
    return district + proportional


def _build_color_to_party(wikitext: str) -> dict[str, str]:
    """凡例からカラーコード→政党名マッピングを構築する."""
    mapping = extract_color_party_mapping(wikitext)
    # {{政党箱|政党名}} 形式（色コードなし）からは取得できないため
    # フォールバックは _resolve_party で対応
    return mapping


def _resolve_party(color: str, color_to_party: dict[str, str]) -> str:
    """カラーコードから政党名を解決する."""
    if color in color_to_party:
        return color_to_party[color]
    # 参議院専用フォールバック → 衆議院共通フォールバック
    if color in WIKIPEDIA_SANGIIN_COLOR_PARTY_FALLBACK:
        return WIKIPEDIA_SANGIIN_COLOR_PARTY_FALLBACK[color]
    return WIKIPEDIA_COLOR_PARTY_FALLBACK.get(color, f"不明({color})")


# --- 選挙区パーサー ---


def _parse_district_winners(
    wikitext: str,
    election_number: int,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """選挙区（地方区）当選者を抽出する.

    テンプレートを優先し、なければwikitableにフォールバック。
    """
    # テンプレート形式を試行
    template_candidates = _parse_district_template(wikitext, color_to_party)
    if template_candidates:
        return template_candidates

    # wikitable形式にフォールバック
    return _parse_district_wikitable(wikitext, color_to_party)


def _parse_district_template(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """{{参院選挙区当選者}}テンプレートをパースする.

    形式:
        {{参院選挙区当選者
        |北海道=
        0ff:[[米田勲]]
        9e9:[[堀末治]]
        |青森=9AF:[[佐藤尚武]]
        }}
    """
    template_text = _extract_template_content(wikitext, "参院選挙区当選者")
    if template_text is None:
        return []

    candidates: list[CandidateRecord] = []
    current_pref: str | None = None

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 都道府県ヘッダ: |北海道= or |青森=色:[[名前]]（ヘッダと値が同一行）
        pref_match = re.match(r"^\|(.+?)=(.*)", line)
        if pref_match:
            pref_name = pref_match.group(1).strip()
            remainder = pref_match.group(2).strip()

            # 増減セクション等はスキップ
            if "増減" in pref_name or "注" in pref_name:
                current_pref = None
                continue

            # 補欠キーは独立ヘッダとして扱わない（例: |北海道補欠=...）
            if pref_name.endswith("補欠"):
                # 補欠当選者 — 対応する都道府県を推定
                base_pref: str = pref_name.replace("補欠", "")
                current_pref = base_pref
                if remainder:
                    _parse_entry_line(
                        remainder,
                        base_pref,
                        color_to_party,
                        candidates,
                    )
                continue

            current_pref = pref_name

            # 同一行にエントリがある場合（例: |青森=9AF:[[佐藤尚武]]）
            if remainder:
                _parse_entry_line(
                    remainder,
                    pref_name,
                    color_to_party,
                    candidates,
                )
            continue

        if current_pref is None:
            continue

        # 色:[[名前]] エントリ
        _parse_entry_line(line, current_pref, color_to_party, candidates)

    return candidates


def _parse_entry_line(
    line: str,
    pref_name: str,
    color_to_party: dict[str, str],
    candidates: list[CandidateRecord],
) -> None:
    """テンプレート内の色:[[名前]]行をパースしてcandidatesに追加する."""
    entry_match = _ENTRY_RE.match(line)
    if not entry_match:
        return

    color = _normalize_color(entry_match.group(1))
    name_part = entry_match.group(2)

    # 補欠マーカー ":補欠" を除去
    name_part = re.sub(r":補欠\s*$", "", name_part)
    # 特定枠マーカーを除去（比例で使われるが念のため）
    name_part = re.sub(r":特定枠\s*$", "", name_part)

    name = extract_name_from_wikilink(name_part)
    if not name:
        return

    party = _resolve_party(color, color_to_party)
    district = _normalize_sangiin_district(pref_name)
    prefecture = _extract_prefecture_from_sangiin_district(pref_name)

    candidates.append(
        CandidateRecord(
            name=name,
            party_name=party,
            district_name=district,
            prefecture=prefecture,
            total_votes=0,
            rank=1,
            is_elected=True,
        )
    )


def _parse_district_wikitable(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """wikitable形式の選挙区当選者をパースする.

    セクション見出し配下のwikitableを探し、ヘッダ行から選挙区名を抽出する。

    構造例:
        === 選挙区当選者 ===
        {| class="wikitable"
        |-
        !colspan=4|[[北海道選挙区|北海道]]!![[青森県選挙区|青森県]]
        |-
        |style="background-color:#9e9"|[[名前]]||style="background-color:#0ff"|[[名前]]
        |}
    """
    # セクションを探す
    section_text = _extract_section(wikitext, _DISTRICT_SECTION_RE)
    if not section_text:
        return []

    # wikitableを抽出
    table_match = re.search(r"\{\|.*?\n(.*?)\|\}", section_text, re.DOTALL)
    if not table_match:
        return []

    table_text = table_match.group(1)
    candidates: list[CandidateRecord] = []

    # ヘッダ行から選挙区名の列マッピングを構築
    districts = _extract_district_columns(table_text)

    # データ行を処理
    col_index = 0
    for line in table_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line == "|-":
            col_index = 0
            continue

        # ヘッダ行はスキップ（既に処理済み）
        if line.startswith("!"):
            col_index = 0
            continue

        if not line.startswith("|"):
            continue

        # セル行を処理
        content = line[1:] if line.startswith("|") else line
        cells = content.split("||")

        for cell_text in cells:
            cell_text = cell_text.strip()

            # rowspan属性の処理
            rowspan_match = re.match(r'rowspan="?\d+"?\s*\|\s*(.*)', cell_text)
            if rowspan_match:
                cell_text = rowspan_match.group(1).strip()

            cell_match = _WIKITABLE_CELL_RE.match(cell_text)
            if cell_match:
                color = _normalize_color(cell_match.group(1))
                name_part = cell_match.group(2)
                name = extract_name_from_wikilink(name_part)

                if name and col_index < len(districts) and districts[col_index]:
                    party = _resolve_party(color, color_to_party)
                    district = districts[col_index]
                    prefecture = _extract_prefecture_from_sangiin_district(district)

                    candidates.append(
                        CandidateRecord(
                            name=name,
                            party_name=party,
                            district_name=_normalize_sangiin_district(district),
                            prefecture=prefecture,
                            total_votes=0,
                            rank=1,
                            is_elected=True,
                        )
                    )
            col_index += 1

    return candidates


def _extract_district_columns(table_text: str) -> list[str]:
    """wikitableのヘッダ行から選挙区名の列マッピングを構築する.

    ヘッダの構造例:
        !colspan=4|[[北海道選挙区|北海道]]!![[青森県選挙区|青森県]]!!colspan=2|[[東京都選挙区|東京都]]
    colspanの値に応じて同じ選挙区名を複数列に展開する。
    """
    districts: list[str] = []

    for line in table_text.split("\n"):
        line = line.strip()
        if not line.startswith("!"):
            continue

        # 選挙区名のヘッダ行を検出（wikilinkを含む行）
        if "選挙区" not in line and "[[" not in line:
            continue

        # 定数行（数字のみ）はスキップ
        # 例: !8人区 や !colspan=10|8人区
        if re.match(r"^!\s*(?:colspan[^|]*\|)?\s*\d+人区", line):
            # 定数行 — これは選挙区名ではない
            continue

        parts = re.split(r"!!", line)
        for i, part in enumerate(parts):
            part = part.strip()
            if i == 0:
                # 最初のパートは先頭の ! を除去
                part = part.lstrip("!").strip()

            if not part:
                continue

            # colspan値を取得
            colspan = 1
            colspan_match = re.match(r'colspan[= ]"?(\d+)"?\s*\|\s*(.*)', part)
            if colspan_match:
                colspan = int(colspan_match.group(1))
                part = colspan_match.group(2).strip()

            # wikilinkから選挙区名を取得
            wl_match = _DISTRICT_WIKILINK_RE.search(part)
            if wl_match:
                display = wl_match.group(2) or wl_match.group(1)
                # [[北海道選挙区|北海道]] → "北海道"
                district_name = display.strip()
            else:
                district_name = part.strip()

            # colspan分だけ繰り返す
            for _ in range(colspan):
                districts.append(district_name)

        if districts:
            break  # 最初のヘッダ行のみ使用

    return districts


# --- 比例代表/全国区パーサー ---


def _parse_proportional_winners(
    wikitext: str,
    election_number: int,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """比例代表（全国区）当選者を抽出する.

    テンプレートを優先し、なければwikitableにフォールバック。
    """
    # テンプレート形式を試行
    template_candidates = _parse_proportional_template(
        wikitext, election_number, color_to_party
    )
    if template_candidates:
        return template_candidates

    # wikitable形式にフォールバック
    return _parse_proportional_wikitable(wikitext, election_number, color_to_party)


def _parse_proportional_template(
    wikitext: str,
    election_number: int,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """{{参院比例当選者}}テンプレートをパースする.

    形式:
        {{参院比例当選者|
        9e9:[[藤井一博]]:特定枠
        0c9:[[石井章]]
        ccf:[[辻元清美]]
        ...
        }}
    """
    template_text = _extract_template_content(wikitext, "参院比例当選者")
    if template_text is None:
        return []

    candidates: list[CandidateRecord] = []
    district_label = "比例区" if election_number >= 13 else "全国区"
    rank_counter = 0

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        entry_match = _ENTRY_RE.match(line)
        if not entry_match:
            continue

        rank_counter += 1
        color = _normalize_color(entry_match.group(1))
        name_part = entry_match.group(2)

        # 特定枠マーカーを除去
        name_part = re.sub(r":特定枠\s*$", "", name_part)

        name = extract_name_from_wikilink(name_part)
        if not name:
            continue

        party = _resolve_party(color, color_to_party)

        candidates.append(
            CandidateRecord(
                name=name,
                party_name=party,
                district_name=district_label,
                prefecture=district_label,
                total_votes=0,
                rank=rank_counter,
                is_elected=True,
            )
        )

    return candidates


def _parse_proportional_wikitable(
    wikitext: str,
    election_number: int,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """wikitable形式の全国区/比例区当選者をパースする.

    構造例:
        === 全国区当選者 ===
        {| class="wikitable"
        |-
        !1-10
        |style="background-color:#9e9"|[[名前]]||style="background-color:#0ff"|[[名前]]
        |-
        !11-20
        ...
        |}

    順位は行ヘッダ（!1-10等）から算出する。
    """
    section_text = _extract_section(wikitext, _PROPORTIONAL_SECTION_RE)
    if not section_text:
        return []

    # wikitableを抽出
    table_match = re.search(r"\{\|.*?\n(.*?)\|\}", section_text, re.DOTALL)
    if not table_match:
        return []

    table_text = table_match.group(1)
    candidates: list[CandidateRecord] = []
    district_label = "比例区" if election_number >= 13 else "全国区"

    # 順位追跡用
    rank_base = 0  # 行ヘッダの開始順位
    rank_offset = 0  # 行内のオフセット

    for line in table_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line == "|-":
            rank_offset = 0
            continue

        # ヘッダ行: !1-10 or !11-20 etc.
        rank_header_match = re.match(r"^!(\d+)\s*[-–〜~]\s*(\d+)", line)
        if rank_header_match:
            rank_base = int(rank_header_match.group(1))
            rank_offset = 0
            continue

        # 単独数字ヘッダ: !1
        single_rank_match = re.match(r"^!(\d+)\s*$", line)
        if single_rank_match:
            rank_base = int(single_rank_match.group(1))
            rank_offset = 0
            continue

        # ヘッダ行（その他）はスキップ
        if line.startswith("!"):
            continue

        if not line.startswith("|"):
            continue

        # セル行を処理
        content = line[1:]
        cells = content.split("||")

        for cell_text in cells:
            cell_text = cell_text.strip()

            # rowspan属性の処理
            rowspan_match = re.match(r'rowspan="?\d+"?\s*\|\s*(.*)', cell_text)
            if rowspan_match:
                cell_text = rowspan_match.group(1).strip()

            cell_match = _WIKITABLE_CELL_RE.match(cell_text)
            if cell_match:
                color = _normalize_color(cell_match.group(1))
                name_part = cell_match.group(2)
                name = extract_name_from_wikilink(name_part)

                if name:
                    rank_offset += 1
                    rank = rank_base + rank_offset - 1 if rank_base > 0 else rank_offset
                    party = _resolve_party(color, color_to_party)

                    candidates.append(
                        CandidateRecord(
                            name=name,
                            party_name=party,
                            district_name=district_label,
                            prefecture=district_label,
                            total_votes=0,
                            rank=rank,
                            is_elected=True,
                        )
                    )
            else:
                rank_offset += 1  # 空セルもカラムカウントに含める

    return candidates


# --- ユーティリティ ---


def _extract_section(wikitext: str, pattern: re.Pattern[str]) -> str | None:
    """正規表現にマッチするセクション見出し以降のテキストを抽出する."""
    match = pattern.search(wikitext)
    if not match:
        return None

    start = match.end()
    # 次の同レベル以上のセクション見出しまで
    next_section = re.search(r"\n==(?!=)", wikitext[start:])
    if next_section:
        return wikitext[start : start + next_section.start()]
    return wikitext[start:]


def _normalize_sangiin_district(name: str) -> str:
    """参議院選挙区名を正規化する.

    例:
        "北海道" → "北海道選挙区"
        "東京都" → "東京都選挙区"
        "青森" → "青森県選挙区"
        "鳥取・島根" → "鳥取県・島根県選挙区"
    """
    # 既に「選挙区」が含まれている場合はそのまま
    if "選挙区" in name:
        return name

    # 合区対応: "鳥取・島根" → "鳥取県・島根県選挙区"
    if "・" in name:
        parts = name.split("・")
        normalized_parts = [_add_prefecture_suffix(p.strip()) for p in parts]
        return "・".join(normalized_parts) + "選挙区"

    return _add_prefecture_suffix(name) + "選挙区"


def _add_prefecture_suffix(name: str) -> str:
    """都道府県名に接尾辞を補完する."""
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


def _extract_prefecture_from_sangiin_district(name: str) -> str:
    """参議院選挙区名から都道府県名を抽出する.

    合区の場合は最初の都道府県名を返す。
    """
    # 「選挙区」を除去
    name = name.replace("選挙区", "")

    # 合区の場合は最初の都道府県
    if "・" in name:
        name = name.split("・")[0]

    return _add_prefecture_suffix(name.strip())
