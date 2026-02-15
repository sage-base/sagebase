"""議案管理ビューの共有ヘルパー関数.

提出者表示など、複数のタブモジュールで共通使用するユーティリティ関数を提供します。
"""

from .constants import SUBMITTER_TYPE_ICONS, SUBMITTER_TYPE_LABELS

from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter


def get_submitter_type_icon(submitter_type: str) -> str:
    """提出者種別のアイコンを取得する."""
    return SUBMITTER_TYPE_ICONS.get(submitter_type, "❓")


def get_submitter_type_label(submitter_type: str) -> str:
    """提出者種別の日本語ラベルを取得する."""
    return SUBMITTER_TYPE_LABELS.get(submitter_type, "その他")


def build_submitters_text(
    proposal: Proposal,
    submitters_map: dict[int, list[ProposalSubmitter]] | None = None,
    politician_names: dict[int, str] | None = None,
    conference_names: dict[int, str] | None = None,
    pg_names: dict[int, str] | None = None,
) -> str:
    """提出者情報を文字列として構築する（Streamlit要素を生成しない）."""
    if submitters_map is not None and proposal.id is not None:
        submitters = submitters_map.get(proposal.id, [])
    else:
        return "未設定"

    if not submitters:
        return "未設定"

    parts: list[str] = []
    for s in submitters:
        icon = get_submitter_type_icon(s.submitter_type.value)
        name = s.raw_name or ""
        if s.politician_id and politician_names:
            name = politician_names.get(
                s.politician_id, name or f"ID:{s.politician_id}"
            )
        elif s.parliamentary_group_id and pg_names:
            name = pg_names.get(
                s.parliamentary_group_id,
                name or f"ID:{s.parliamentary_group_id}",
            )
        elif s.conference_id and conference_names:
            name = conference_names.get(
                s.conference_id, name or f"ID:{s.conference_id}"
            )
        elif not name:
            name = get_submitter_type_label(s.submitter_type.value)
        parts.append(f"{icon} {name}")

    return ", ".join(parts) if parts else "未設定"
