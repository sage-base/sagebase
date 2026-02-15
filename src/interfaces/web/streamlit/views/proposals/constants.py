"""議案管理ビューの共有定数.

各タブモジュールで共通使用する定数を定義します。
"""

# 議案一覧のページサイズ
PROPOSALS_PAGE_SIZE = 10

# 提出者種別のアイコンマッピング
SUBMITTER_TYPE_ICONS: dict[str, str] = {
    "mayor": "👤",
    "politician": "👥",
    "parliamentary_group": "🏛️",
    "committee": "📋",
    "conference": "🏢",
    "other": "❓",
}

# 提出者種別の日本語ラベル
SUBMITTER_TYPE_LABELS: dict[str, str] = {
    "mayor": "市長",
    "politician": "議員",
    "parliamentary_group": "会派",
    "committee": "委員会",
    "conference": "会議体",
    "other": "その他",
}

# 賛否の選択肢
JUDGMENT_OPTIONS = ["賛成", "反対", "棄権", "欠席"]
