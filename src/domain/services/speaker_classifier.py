"""発言者の政治家/非政治家分類サービス.

役職のみの発言者名や参考人・証人など、政治家ではない発言者を
名前パターンに基づいて判定する。
"""

from enum import Enum


class SkipReason(Enum):
    """非政治家分類の理由."""

    ROLE_ONLY = "role_only"
    REFERENCE_PERSON = "reference_person"
    GOVERNMENT_OFFICIAL = "government_official"
    OTHER_NON_POLITICIAN = "other_non_politician"


# カテゴリ別の非政治家名パターン
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
        "書記",
        "速記者",
        # 議会運営
        "幹事",
        # メタ情報（発言者ではないが発言者欄に出現することがある）
        "会議録情報",
    }
)

# 全非政治家パターンの統合（既存APIとの互換性維持）
NON_POLITICIAN_EXACT_NAMES: frozenset[str] = (
    _ROLE_ONLY_NAMES
    | _REFERENCE_PERSON_NAMES
    | _GOVERNMENT_OFFICIAL_NAMES
    | _OTHER_NON_POLITICIAN_NAMES
)


def is_non_politician_name(name: str) -> bool:
    """指定された名前が非政治家パターンに該当するかを判定する.

    Args:
        name: 発言者名

    Returns:
        非政治家パターンに該当する場合True
    """
    return name.strip() in NON_POLITICIAN_EXACT_NAMES


def classify_speaker_skip_reason(name: str) -> SkipReason | None:
    """発言者名を分類し、非政治家カテゴリを返す.

    Args:
        name: 発言者名

    Returns:
        SkipReason Enum値。政治家の可能性がある場合はNone。
    """
    stripped = name.strip()
    if stripped in _ROLE_ONLY_NAMES:
        return SkipReason.ROLE_ONLY
    if stripped in _REFERENCE_PERSON_NAMES:
        return SkipReason.REFERENCE_PERSON
    if stripped in _GOVERNMENT_OFFICIAL_NAMES:
        return SkipReason.GOVERNMENT_OFFICIAL
    if stripped in _OTHER_NON_POLITICIAN_NAMES:
        return SkipReason.OTHER_NON_POLITICIAN
    return None
