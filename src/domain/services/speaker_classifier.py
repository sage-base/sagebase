"""発言者の政治家/非政治家分類サービス.

役職のみの発言者名や参考人・証人など、政治家ではない発言者を
名前パターンに基づいて判定する。

完全一致パターンに加え、「政府参考人（山田太郎君）」のような
「役職名（人名）」形式にも対応するプレフィックスマッチを提供する。
"""

from enum import Enum


class SkipReason(Enum):
    """発言者マッチングのスキップ理由."""

    ROLE_ONLY = "role_only"
    REFERENCE_PERSON = "reference_person"
    GOVERNMENT_OFFICIAL = "government_official"
    OTHER_NON_POLITICIAN = "other_non_politician"
    HOMONYM = "homonym"


# === 完全一致パターン ===

# 議会役職（個人を特定できない役職名のみの発言者）
_ROLE_ONLY_NAMES: frozenset[str] = frozenset(
    {
        "委員長",
        "副委員長",
        "議長",
        "副議長",
        "仮議長",
    }
)

# 参考人・証人等
_REFERENCE_PERSON_NAMES: frozenset[str] = frozenset(
    {
        "参考人",
        "証人",
        "公述人",
    }
)

# 政府側出席者（非議員）
_GOVERNMENT_OFFICIAL_NAMES: frozenset[str] = frozenset(
    {
        "説明員",
        "政府委員",
        "政府参考人",
    }
)

# その他の非政治家名パターン
_OTHER_NON_POLITICIAN_NAMES: frozenset[str] = frozenset(
    {
        # 事務局スタッフ
        "事務局長",
        "事務局次長",
        "事務総長",
        "法制局長",
        "書記官長",
        "書記",
        "速記者",
        # 議会運営
        "幹事",
        # メタ情報（発言者ではないが発言者欄に出現することがある）
        "会議録情報",
    }
)

# 全非政治家パターンの統合（完全一致用）
NON_POLITICIAN_EXACT_NAMES: frozenset[str] = (
    _ROLE_ONLY_NAMES
    | _REFERENCE_PERSON_NAMES
    | _GOVERNMENT_OFFICIAL_NAMES
    | _OTHER_NON_POLITICIAN_NAMES
)

# === プレフィックスパターン ===
# 国会会議録APIの「役職名（人名君）」形式に対応
# 注意: 議長（、委員長（ 等は含めない。これらの括弧付き形式は政治家を指すため。

# 参考人・証人等（「参考人（山田太郎君）」形式）
_REFERENCE_PERSON_PREFIXES: frozenset[str] = frozenset(
    {
        "参考人（",
        "証人（",
        "公述人（",
    }
)

# 政府側出席者（「政府参考人（山田太郎君）」形式）
_GOVERNMENT_OFFICIAL_PREFIXES: frozenset[str] = frozenset(
    {
        "説明員（",
        "政府委員（",
        "政府参考人（",
    }
)

# その他の非政治家（「事務総長（山田太郎君）」形式）
_OTHER_NON_POLITICIAN_PREFIXES: frozenset[str] = frozenset(
    {
        "事務総長（",
        "事務局長（",
        "事務局次長（",
        "法制局長（",
        "書記官長（",
    }
)

# 全プレフィックスパターンの統合
NON_POLITICIAN_PREFIX_PATTERNS: frozenset[str] = (
    _REFERENCE_PERSON_PREFIXES
    | _GOVERNMENT_OFFICIAL_PREFIXES
    | _OTHER_NON_POLITICIAN_PREFIXES
)

# カテゴリとパターンの対応テーブル
# 新カテゴリ追加時はここに1行追加するだけでよい。
# 議長・委員長はROLE_ONLYに完全一致のみ（括弧付き形式は政治家）。
_SKIP_REASON_PATTERNS: list[tuple[SkipReason, frozenset[str], frozenset[str]]] = [
    (SkipReason.ROLE_ONLY, _ROLE_ONLY_NAMES, frozenset()),
    (SkipReason.REFERENCE_PERSON, _REFERENCE_PERSON_NAMES, _REFERENCE_PERSON_PREFIXES),
    (
        SkipReason.GOVERNMENT_OFFICIAL,
        _GOVERNMENT_OFFICIAL_NAMES,
        _GOVERNMENT_OFFICIAL_PREFIXES,
    ),
    (
        SkipReason.OTHER_NON_POLITICIAN,
        _OTHER_NON_POLITICIAN_NAMES,
        _OTHER_NON_POLITICIAN_PREFIXES,
    ),
]


def is_non_politician_name(name: str) -> bool:
    """指定された名前が非政治家パターンに該当するかを判定する.

    完全一致とプレフィックスマッチの両方をチェックする。

    Args:
        name: 発言者名

    Returns:
        非政治家パターンに該当する場合True
    """
    stripped = name.strip()
    if stripped in NON_POLITICIAN_EXACT_NAMES:
        return True
    return any(stripped.startswith(prefix) for prefix in NON_POLITICIAN_PREFIX_PATTERNS)


def classify_speaker_skip_reason(name: str) -> SkipReason | None:
    """発言者名を分類し、非政治家カテゴリを返す.

    完全一致チェック後、プレフィックスマッチも行う。

    Args:
        name: 発言者名

    Returns:
        SkipReason Enum値。政治家の可能性がある場合はNone。
    """
    stripped = name.strip()
    for reason, exact_names, prefixes in _SKIP_REASON_PATTERNS:
        if stripped in exact_names:
            return reason
        if prefixes and any(stripped.startswith(p) for p in prefixes):
            return reason
    return None
