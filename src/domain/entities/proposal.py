"""Proposal entity module."""

from datetime import date

from src.domain.entities.base import BaseEntity


PROPOSAL_CATEGORY_MAP: dict[str, str] = {
    "衆法": "legislation",
    "閣法": "legislation",
    "参法": "legislation",
    "予算": "budget",
    "条約": "treaty",
    "承認": "approval",
    "承諾": "approval",
    "決算": "audit",
    "国有財産": "audit",
    "ＮＨＫ決算": "audit",
    "決議": "other",
    "規程": "other",
    "規則": "other",
    "議決": "other",
    "国庫債務": "other",
    "憲法八条議決案": "other",
}

DELIBERATION_RESULT_MAP: dict[str, str] = {
    "成立": "passed",
    "本院議了": "passed",
    "両院承認": "passed",
    "両院承諾": "passed",
    "本院可決": "passed",
    "参議院回付案（同意）": "passed",
    "衆議院議決案（可決）": "passed",
    "参議院議了": "passed",
    "両院議決": "passed",
    # 元データに半角括弧の表記揺れが存在する
    "衆議院回付案(同意)": "passed",
    "衆議院回付案（同意）": "passed",
    "本院修正議決": "passed",
    "承認": "passed",
    "修正承諾": "passed",
    "撤回承諾": "passed",
    "議決不要": "passed",
    "未了": "expired",
    "撤回": "withdrawn",
    "衆議院で閉会中審査": "pending",
    "参議院で閉会中審査": "pending",
    "中間報告": "pending",
    "両院の意見が一致しない旨報告": "rejected",
    "参議院回付案（不同意）": "rejected",
    "承諾なし": "rejected",
    "衆議院で併合修正": "other",
}


class Proposal(BaseEntity):
    """議案を表すエンティティ."""

    def __init__(
        self,
        title: str,
        detail_url: str | None = None,
        status_url: str | None = None,
        votes_url: str | None = None,
        meeting_id: int | None = None,
        conference_id: int | None = None,
        proposal_category: str | None = None,
        proposal_type: str | None = None,
        governing_body_id: int | None = None,
        session_number: int | None = None,
        proposal_number: int | None = None,
        external_id: str | None = None,
        deliberation_status: str | None = None,
        deliberation_result: str | None = None,
        submitted_date: date | None = None,
        voted_date: date | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.title = title
        self.detail_url = detail_url
        self.status_url = status_url
        self.votes_url = votes_url
        self.meeting_id = meeting_id
        self.conference_id = conference_id
        self.proposal_category = proposal_category
        self.proposal_type = proposal_type
        self.governing_body_id = governing_body_id
        self.session_number = session_number
        self.proposal_number = proposal_number
        self.external_id = external_id
        self.deliberation_status = deliberation_status
        self.deliberation_result = deliberation_result
        self.submitted_date = submitted_date
        self.voted_date = voted_date

    def __str__(self) -> str:
        identifier = f"ID:{self.id}"
        return f"Proposal {identifier}: {self.title[:50]}..."

    @property
    def has_business_key(self) -> bool:
        """ビジネスキー（自然キー）が完全に設定されているか判定する."""
        return all(
            [
                self.governing_body_id is not None,
                self.session_number is not None,
                self.proposal_number is not None,
                self.proposal_type is not None,
            ]
        )

    @staticmethod
    def normalize_category(raw_type: str) -> str:
        """議案種別を正規化カテゴリに変換する."""
        return PROPOSAL_CATEGORY_MAP.get(raw_type, "other")

    @staticmethod
    def normalize_result(raw_result: str) -> str | None:
        """審議結果を正規化する."""
        if not raw_result:
            return None
        return DELIBERATION_RESULT_MAP.get(raw_result.strip(), "other")
