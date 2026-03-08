"""Wikipedia参議院選挙当選者Wikitextのパーサー.

Wikitextテンプレート/wikitableから当選者データを抽出し、CandidateRecordリストに変換する。

選挙区（地方区）パターン:
  - テンプレート形式: {{参院選挙区当選者}} — 都道府県=色:[[名前]]
  - wikitable形式: style="background-color:#色" | [[名前]] + ヘッダ
  - 定数別テーブル形式: N人区ヘッダ + rowspan選挙区 + 背景色セル
比例代表（全国区）パターン:
  - テンプレート形式: {{参院比例当選者}} — 色:[[名前]][:特定枠]
  - wikitable形式: 順位行(!1-10) + 背景色セル（width属性付き対応）
補欠当選パターン:
  - wikitable形式: 年/月日/選挙区/当選者/所属党派/欠員/欠員事由
"""

import re

from src.domain.value_objects.election_candidate import CandidateRecord
from src.infrastructure.importers._constants import (
    WIKIPEDIA_COLOR_PARTY_FALLBACK,
    WIKIPEDIA_SANGIIN_COLOR_PARTY_FALLBACK,
)
from src.infrastructure.importers._utils import (
    extract_template_content,
    normalize_color,
    normalize_prefecture,
)
from src.infrastructure.importers.wikipedia_election_wikitext_parser import (
    extract_color_party_mapping,
    extract_name_from_wikilink,
)


# 比例代表制度開始回次（第13回以降は「比例区」、以前は「全国区」）
_PROPORTIONAL_START_ELECTION = 13

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

# 都道府県ヘッダ: |北海道= or |青森=色:[[名前]]
_PREF_HEADER_RE = re.compile(r"^\|(.+?)=(.*)")

# 補欠マーカー
_HOKETSU_RE = re.compile(r":補欠\s*$")

# 特定枠マーカー
_TOKUTEI_WAKU_RE = re.compile(r":特定枠\s*$")

# wikitable抽出パターン
_WIKITABLE_EXTRACT_RE = re.compile(r"\{\|.*?\n(.*?)\|\}", re.DOTALL)

# rowspan属性
_ROWSPAN_RE = re.compile(r'rowspan="?\d+"?\s*\|\s*(.*)')

# 定数行（!8人区 等）
_TEISU_HEADER_RE = re.compile(r"^!\s*(?:colspan[^|]*\|)?\s*\d+人区")

# 改選定数ヘッダ（テーブルタイトル行としてスキップ）
_KAISEN_TEISU_RE = re.compile(r"^!\s*(?:colspan[^|]*\|)?\s*改選定数")

# 繰上当選セクション見出し
_KURIAGE_SECTION_RE = re.compile(r"={3,4}\s*繰上当選\s*={3,4}")

# 補欠当選セクション見出し
_HOKETSU_SECTION_RE = re.compile(r"={3,4}\s*補欠当選\s*={3,4}")

# 次のサブセクション見出し（レベル2〜4）
_NEXT_SUBSECTION_RE = re.compile(r"\n={2,4}[^=]")

# colspan値
_COLSPAN_RE = re.compile(r'colspan[= ]"?(\d+)"?\s*\|\s*(.*)')

# 順位範囲ヘッダ: !1-10, !11-20 etc.
_RANK_RANGE_RE = re.compile(r"^!(\d+)\s*[-–〜~]\s*(\d+)")

# 単独順位ヘッダ: !1
_SINGLE_RANK_RE = re.compile(r"^!(\d+)\s*$")

# 次のセクション見出し
_NEXT_SECTION_RE = re.compile(r"\n==(?!=)")


def parse_sangiin_wikitext(
    wikitext: str,
    election_number: int,
) -> list[CandidateRecord]:
    """参議院選挙のWikitextから選挙区+比例/全国区+繰上当選+補欠当選の全当選者を抽出する."""
    color_to_party = _build_color_to_party(wikitext, election_number)

    district = _parse_district_winners(wikitext, color_to_party)
    proportional = _parse_proportional_winners(
        wikitext, election_number, color_to_party
    )
    kuriage = _parse_kuriage_winners(wikitext, color_to_party)
    hoketsu = _parse_hoketsu_winners(wikitext, color_to_party)
    return district + proportional + kuriage + hoketsu


def _build_color_to_party(wikitext: str, election_number: int) -> dict[str, str]:
    """凡例+フォールバック+時代別オーバーライドでカラー→政党マッピングを構築する.

    優先順位: 記事内抽出 > 時代別オーバーライド > 静的フォールバック
    """
    # 1. 静的フォールバックをベースに
    mapping: dict[str, str] = dict(WIKIPEDIA_SANGIIN_COLOR_PARTY_FALLBACK)

    # 2. 時代別オーバーライド（同じ色コードが時代により異なる政党を指す）
    # 社会民主党: 1996年（第17回）〜。0FFは旧: 日本社会党
    if election_number >= 17:
        mapping["0FF"] = "社会民主党"
    # れいわ新選組: 2019年（第25回）〜。F8Dは旧: 民社党
    if election_number >= 25:
        mapping["F8D"] = "れいわ新選組"
    # 日本保守党: 2025年（第27回）〜。0CFは旧: 第二院クラブ
    if election_number >= 27:
        mapping["0CF"] = "日本保守党"
        mapping["3FB"] = "チームみらい"

    # 3. 記事内の {{colorbox}} / {{政党箱|#hex|name}} 抽出が最優先
    article_mapping = extract_color_party_mapping(wikitext)
    mapping.update(article_mapping)

    return mapping


def _resolve_party(color: str, color_to_party: dict[str, str]) -> str:
    """カラーコードから政党名を解決する."""
    if color in color_to_party:
        return color_to_party[color]
    return WIKIPEDIA_COLOR_PARTY_FALLBACK.get(color, f"不明({color})")


# --- 選挙区パーサー ---


def _parse_district_winners(
    wikitext: str,
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
    template_text = extract_template_content(wikitext, "参院選挙区当選者")
    if template_text is None:
        return []

    candidates: list[CandidateRecord] = []
    current_pref: str | None = None

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 都道府県ヘッダ: |北海道= or |青森=色:[[名前]]（ヘッダと値が同一行）
        pref_match = _PREF_HEADER_RE.match(line)
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

    color = normalize_color(entry_match.group(1))
    name_part = entry_match.group(2)

    # 補欠マーカー ":補欠" を除去
    name_part = _HOKETSU_RE.sub("", name_part)
    # 特定枠マーカーを除去（比例で使われるが念のため）
    name_part = _TOKUTEI_WAKU_RE.sub("", name_part)

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

    3つのフォーマットに対応:
    1. 横並びヘッダ形式: ヘッダ行に選挙区名が横並び
    2. 改選定数別テーブル形式: 定数ごとに分割されたテーブル
    3. 定数別テーブル形式: N人区ヘッダ + rowspan選挙区（初期選挙）
    """
    # セクションを探す
    section_text = _extract_section(wikitext, _DISTRICT_SECTION_RE)
    if not section_text:
        return []

    # 補欠選挙等・繰上当選・補欠当選サブセクション以降を除外
    subsection_match = re.search(
        r"\n={4}\s*(?:補欠選挙|繰上当選|補欠当選)", section_text
    )
    if subsection_match:
        section_text = section_text[: subsection_match.start()]

    # セクション内のすべてのwikitableを抽出
    tables = list(_WIKITABLE_EXTRACT_RE.finditer(section_text))
    if not tables:
        return []

    # 改選定数別テーブル or 定数別テーブル（N人区）を検出
    has_kaisen_teisu = "改選定数" in section_text
    has_teisu_betsu = bool(re.search(r"\d+人区", section_text))
    if has_kaisen_teisu or has_teisu_betsu:
        candidates: list[CandidateRecord] = []
        for table_match in tables:
            candidates.extend(
                _parse_kaisen_teisu_table(table_match.group(1), color_to_party)
            )
        return candidates

    # 横並びヘッダ形式（単一テーブル）
    first_table_text = tables[0].group(1)
    districts = _extract_district_columns(first_table_text)
    if districts:
        return _parse_horizontal_district_table(
            first_table_text, districts, color_to_party
        )

    return []


def _parse_horizontal_district_table(
    table_text: str,
    districts: list[str],
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """横並びヘッダ形式のwikitableから選挙区当選者をパースする."""
    candidates: list[CandidateRecord] = []
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
        cells = line[1:].split("||")

        for cell_text in cells:
            cell_text = cell_text.strip()

            # rowspan属性の処理
            rowspan_match = _ROWSPAN_RE.match(cell_text)
            if rowspan_match:
                cell_text = rowspan_match.group(1).strip()

            cell_match = _WIKITABLE_CELL_RE.match(cell_text)
            if cell_match:
                color = normalize_color(cell_match.group(1))
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


def _parse_kaisen_teisu_table(
    table_text: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """改選定数別/定数別テーブル形式の選挙区当選者をパースする.

    行内の ! [[選挙区名]] で現在の選挙区を切り替え、
    | style="background-color:..." | [[名前]] を当選者として抽出する。

    N人区テーブル（rowspan=2）では、下段（! ヘッダなしの行）の候補者を
    上段のdistrict順序と候補者数に基づいて位置ベースで割り当てる。
    """
    candidates: list[CandidateRecord] = []
    current_district = ""

    # N人区テーブルのrowspan下段対応用
    district_order: list[str] = []
    candidates_per_district: dict[str, int] = {}
    row_has_district_headers = False
    second_row_district_idx = 0
    second_row_cell_count = 0

    for line in table_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line == "|-":
            # 行区切り: 下段行の位置ベース割当を準備
            if row_has_district_headers and district_order:
                row_has_district_headers = False
                second_row_district_idx = 0
                second_row_cell_count = 0
                current_district = district_order[0]
            elif district_order:
                # さらに次の行区切り: district位置をリセット
                second_row_district_idx = 0
                second_row_cell_count = 0
                current_district = district_order[0]
            continue

        if line.startswith("!"):
            # 改選定数/定数別タイトルはスキップ
            if _KAISEN_TEISU_RE.match(line) or _TEISU_HEADER_RE.match(line):
                continue

            # 選挙区名を抽出
            wl_match = _DISTRICT_WIKILINK_RE.search(line)
            if wl_match:
                display = wl_match.group(2) or wl_match.group(1)
                current_district = display.strip()
                row_has_district_headers = True
                if current_district not in candidates_per_district:
                    district_order.append(current_district)
                    candidates_per_district[current_district] = 0
            continue

        if not line.startswith("|"):
            continue

        # セル行を処理
        cells = line[1:].split("||")
        for cell_text in cells:
            cell_text = cell_text.strip()

            cell_match = _WIKITABLE_CELL_RE.match(cell_text)
            if cell_match and current_district:
                color = normalize_color(cell_match.group(1))
                name_part = cell_match.group(2)
                name = extract_name_from_wikilink(name_part)

                if name:
                    if row_has_district_headers:
                        # 上段: 候補者数を追跡
                        candidates_per_district[current_district] = (
                            candidates_per_district.get(current_district, 0) + 1
                        )
                    party = _resolve_party(color, color_to_party)
                    prefecture = _extract_prefecture_from_sangiin_district(
                        current_district
                    )
                    candidates.append(
                        CandidateRecord(
                            name=name,
                            party_name=party,
                            district_name=_normalize_sangiin_district(current_district),
                            prefecture=prefecture,
                            total_votes=0,
                            rank=1,
                            is_elected=True,
                        )
                    )

                    if not row_has_district_headers and district_order:
                        second_row_cell_count += 1
                        # 現districtの候補者数に達したら次のdistrictへ
                        expected = candidates_per_district.get(
                            district_order[second_row_district_idx], 0
                        )
                        if (
                            second_row_cell_count >= expected
                            and second_row_district_idx + 1 < len(district_order)
                        ):
                            second_row_district_idx += 1
                            second_row_cell_count = 0
                            current_district = district_order[second_row_district_idx]

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
        if _TEISU_HEADER_RE.match(line):
            continue

        parts = line.split("!!")
        for i, part in enumerate(parts):
            part = part.strip()
            if i == 0:
                # 最初のパートは先頭の ! を除去
                part = part.lstrip("!").strip()

            if not part:
                continue

            # colspan値を取得
            colspan = 1
            colspan_match = _COLSPAN_RE.match(part)
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
    template_text = extract_template_content(wikitext, "参院比例当選者")
    if template_text is None:
        return []

    candidates: list[CandidateRecord] = []
    district_label = (
        "比例区" if election_number >= _PROPORTIONAL_START_ELECTION else "全国区"
    )
    rank_counter = 0

    for line in template_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        entry_match = _ENTRY_RE.match(line)
        if not entry_match:
            continue

        rank_counter += 1
        color = normalize_color(entry_match.group(1))
        name_part = entry_match.group(2)

        # 特定枠マーカーを除去
        name_part = _TOKUTEI_WAKU_RE.sub("", name_part)

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
    table_match = _WIKITABLE_EXTRACT_RE.search(section_text)
    if not table_match:
        return []

    table_text = table_match.group(1)
    candidates: list[CandidateRecord] = []
    district_label = (
        "比例区" if election_number >= _PROPORTIONAL_START_ELECTION else "全国区"
    )

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

        # ヘッダ行: !1-10 or !11-20 or ! width="70px" | 1-10 etc.
        if line.startswith("!"):
            # HTML属性付きヘッダから実コンテンツを抽出
            # 例: ! width="70px" | 1-10 → !1-10
            header_content = line
            pipe_pos = line.find("|", 1)
            bracket_pos = line.find("[[", 1)
            if pipe_pos > 0 and (bracket_pos < 0 or pipe_pos < bracket_pos):
                header_content = "!" + line[pipe_pos + 1 :].strip()

            rank_header_match = _RANK_RANGE_RE.match(header_content)
            if rank_header_match:
                rank_base = int(rank_header_match.group(1))
                rank_offset = 0
                continue

            single_rank_match = _SINGLE_RANK_RE.match(header_content)
            if single_rank_match:
                rank_base = int(single_rank_match.group(1))
                rank_offset = 0
                continue

            # ヘッダ行（その他）はスキップ
            continue

        if not line.startswith("|"):
            continue

        # セル行を処理
        content = line[1:]
        cells = content.split("||")

        for cell_text in cells:
            cell_text = cell_text.strip()

            # rowspan属性の処理
            rowspan_match = _ROWSPAN_RE.match(cell_text)
            if rowspan_match:
                cell_text = rowspan_match.group(1).strip()

            cell_match = _WIKITABLE_CELL_RE.match(cell_text)
            if cell_match:
                color = normalize_color(cell_match.group(1))
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


# --- 繰上当選パーサー ---


def _parse_kuriage_winners(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """繰上当選セクションから当選者を抽出する.

    テーブル構造:
        !年!!月日!!新旧別!!当選者!!所属党派!!欠員!!欠員事由
    当選者カラム（index 3）から名前、所属党派カラム（index 4）から政党名を抽出する。
    """
    match = _KURIAGE_SECTION_RE.search(wikitext)
    if not match:
        return []

    start = match.end()
    next_section = _NEXT_SUBSECTION_RE.search(wikitext[start:])
    if next_section:
        section_text = wikitext[start : start + next_section.start()]
    else:
        section_text = wikitext[start:]

    table_match = _WIKITABLE_EXTRACT_RE.search(section_text)
    if not table_match:
        return []

    table_text = table_match.group(1)
    candidates: list[CandidateRecord] = []

    # 各行のセルを収集してパース
    row_cells: list[str] = []
    for line in table_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line == "|-":
            candidate = _extract_kuriage_candidate(row_cells, color_to_party)
            if candidate:
                candidates.append(candidate)
            row_cells = []
            continue

        if line.startswith("!"):
            continue

        if not line.startswith("|"):
            continue

        # セル行のセルを分割して追加
        cells = line[1:].split("||")
        row_cells.extend(c.strip() for c in cells)

    # 最後の行を処理
    candidate = _extract_kuriage_candidate(row_cells, color_to_party)
    if candidate:
        candidates.append(candidate)

    return candidates


def _extract_kuriage_candidate(
    row_cells: list[str],
    color_to_party: dict[str, str],
) -> CandidateRecord | None:
    """繰上当選テーブルの1行からCandidateRecordを生成する.

    rowspanにより列数が可変のため、background-colorスタイル付きセルを動的に検出する。
    最初のbackground-colorセルが当選者、その直後のセルが所属党派。
    """
    if len(row_cells) < 3:
        return None

    # background-colorスタイル付きの最初のセルを当選者として検出
    candidate_idx = None
    for i, cell in enumerate(row_cells):
        cell_match = _WIKITABLE_CELL_RE.match(cell)
        if cell_match:
            name = extract_name_from_wikilink(cell_match.group(2))
            if name:
                candidate_idx = i
                break

    if candidate_idx is None:
        return None

    candidate_cell = row_cells[candidate_idx]
    cell_match = _WIKITABLE_CELL_RE.match(candidate_cell)
    if not cell_match:
        return None

    color = normalize_color(cell_match.group(1))
    name_part = cell_match.group(2)
    name = extract_name_from_wikilink(name_part)
    if not name:
        return None

    # 直後のセルから所属党派を取得、なければカラーマッピング
    party_idx = candidate_idx + 1
    party_text = row_cells[party_idx].strip() if len(row_cells) > party_idx else ""
    if party_text and not party_text.startswith("style="):
        party = party_text
    else:
        party = _resolve_party(color, color_to_party)

    return CandidateRecord(
        name=name,
        party_name=party,
        district_name="",
        prefecture="",
        total_votes=0,
        rank=1,
        is_elected=True,
    )


# --- 補欠当選パーサー ---


def _parse_hoketsu_winners(
    wikitext: str,
    color_to_party: dict[str, str],
) -> list[CandidateRecord]:
    """補欠当選セクションから当選者を抽出する.

    テーブル構造:
        !年!!月日!!選挙区!!当選者!!所属党派!!欠員!!所属党派!!欠員事由
    行内の ! セル（ヘッダスタイル）から選挙区名を抽出し、
    background-colorスタイル付きセルから当選者を検出する。
    """
    match = _HOKETSU_SECTION_RE.search(wikitext)
    if not match:
        return []

    start = match.end()
    next_section = _NEXT_SUBSECTION_RE.search(wikitext[start:])
    if next_section:
        section_text = wikitext[start : start + next_section.start()]
    else:
        section_text = wikitext[start:]

    table_match = _WIKITABLE_EXTRACT_RE.search(section_text)
    if not table_match:
        return []

    table_text = table_match.group(1)
    candidates: list[CandidateRecord] = []

    # 各行のセルを収集してパース
    row_cells: list[str] = []
    row_district = ""

    for line in table_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line == "|-":
            candidate = _extract_hoketsu_candidate(
                row_cells, row_district, color_to_party
            )
            if candidate:
                candidates.append(candidate)
            row_cells = []
            row_district = ""
            continue

        # テーブルヘッダ行（カラム定義）はスキップ
        # ただし ! 選挙区名（データ行内のヘッダスタイルセル）は抽出
        if line.startswith("!"):
            # カラム定義ヘッダ行の検出: !! で複数カラムが連結されている
            if "!!" in line:
                continue
            # データ行内の選挙区名 (例: ! 滋賀県)
            # rowspan等の属性を除去してテキストを取得
            district_text = line.lstrip("!").strip()
            # rowspan属性がある場合は除去
            rowspan_match = _ROWSPAN_RE.match(district_text)
            if rowspan_match:
                district_text = rowspan_match.group(1).strip()
            # wikilink形式の場合
            wl_match = _DISTRICT_WIKILINK_RE.search(district_text)
            if wl_match:
                district_text = wl_match.group(2) or wl_match.group(1)
            district_text = district_text.strip()
            if district_text:
                row_district = district_text
            continue

        if not line.startswith("|"):
            continue

        # セル行のセルを分割して追加
        cells = line[1:].split("||")
        row_cells.extend(c.strip() for c in cells)

    # 最後の行を処理
    candidate = _extract_hoketsu_candidate(row_cells, row_district, color_to_party)
    if candidate:
        candidates.append(candidate)

    return candidates


def _extract_hoketsu_candidate(
    row_cells: list[str],
    district: str,
    color_to_party: dict[str, str],
) -> CandidateRecord | None:
    """補欠当選テーブルの1行からCandidateRecordを生成する.

    繰上当選と類似だが、選挙区情報を付与する。
    """
    if len(row_cells) < 2:
        return None

    # background-colorスタイル付きの最初のセルを当選者として検出
    candidate_idx = None
    for i, cell in enumerate(row_cells):
        cell_match = _WIKITABLE_CELL_RE.match(cell)
        if cell_match:
            name = extract_name_from_wikilink(cell_match.group(2))
            if name:
                candidate_idx = i
                break

    if candidate_idx is None:
        return None

    candidate_cell = row_cells[candidate_idx]
    cell_match = _WIKITABLE_CELL_RE.match(candidate_cell)
    if not cell_match:
        return None

    color = normalize_color(cell_match.group(1))
    name_part = cell_match.group(2)
    name = extract_name_from_wikilink(name_part)
    if not name:
        return None

    # 直後のセルから所属党派を取得、なければカラーマッピング
    party_idx = candidate_idx + 1
    party_text = row_cells[party_idx].strip() if len(row_cells) > party_idx else ""
    if party_text and not party_text.startswith("style="):
        party = party_text
    else:
        party = _resolve_party(color, color_to_party)

    # 選挙区情報を付与
    district_name = _normalize_sangiin_district(district) if district else ""
    prefecture = _extract_prefecture_from_sangiin_district(district) if district else ""

    return CandidateRecord(
        name=name,
        party_name=party,
        district_name=district_name,
        prefecture=prefecture,
        total_votes=0,
        rank=1,
        is_elected=True,
    )


# --- ユーティリティ ---


def _extract_section(wikitext: str, pattern: re.Pattern[str]) -> str | None:
    """正規表現にマッチするセクション見出し以降のテキストを抽出する."""
    match = pattern.search(wikitext)
    if not match:
        return None

    start = match.end()
    # 次の同レベル以上のセクション見出しまで
    next_section = _NEXT_SECTION_RE.search(wikitext[start:])
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
        normalized_parts = [normalize_prefecture(p.strip()) for p in parts]
        return "・".join(normalized_parts) + "選挙区"

    return normalize_prefecture(name) + "選挙区"


def _extract_prefecture_from_sangiin_district(name: str) -> str:
    """参議院選挙区名から都道府県名を抽出する.

    合区の場合は最初の都道府県名を返す。
    """
    # 「選挙区」を除去
    name = name.replace("選挙区", "")

    # 合区の場合は最初の都道府県
    if "・" in name:
        name = name.split("・")[0]

    return normalize_prefecture(name.strip())
