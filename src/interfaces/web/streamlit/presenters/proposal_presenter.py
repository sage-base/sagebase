"""Presenter for proposal management in Streamlit.

This module provides the presenter layer for proposal management,
handling UI state and coordinating with use cases.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
)
from src.application.usecases.extract_proposal_judges_usecase import (
    CreateProposalJudgesInputDTO,
    CreateProposalJudgesOutputDTO,
    ExtractProposalJudgesInputDTO,
    ExtractProposalJudgesOutputDTO,
    ExtractProposalJudgesUseCase,
    MatchProposalJudgesInputDTO,
    MatchProposalJudgesOutputDTO,
)
from src.application.usecases.manage_parliamentary_group_judges_usecase import (
    CreateJudgeOutputDTO,
    DeleteJudgeOutputDTO,
    ManageParliamentaryGroupJudgesUseCase,
    UpdateJudgeOutputDTO,
)
from src.application.usecases.manage_proposals_usecase import (
    CreateProposalInputDto,
    CreateProposalOutputDto,
    DeleteProposalInputDto,
    DeleteProposalOutputDto,
    ManageProposalsUseCase,
    ProposalListInputDto,
    ProposalListOutputDto,
    UpdateProposalInputDto,
    UpdateProposalOutputDto,
)
from src.application.usecases.scrape_proposal_usecase import (
    ScrapeProposalInputDTO,
    ScrapeProposalOutputDTO,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (  # noqa: E501
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.dto.base import FormStateDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ProposalPresenter(CRUDPresenter[list[Proposal]]):
    """Presenter for proposal management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.proposal_repository = RepositoryAdapter(ProposalRepositoryImpl)
        self.extracted_judge_repository = RepositoryAdapter(
            ExtractedProposalJudgeRepositoryImpl
        )
        self.judge_repository = RepositoryAdapter(ProposalJudgeRepositoryImpl)
        self.parliamentary_group_judge_repository = RepositoryAdapter(
            ProposalParliamentaryGroupJudgeRepositoryImpl
        )
        self.parliamentary_group_repository = RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl
        )
        self.meeting_repository = RepositoryAdapter(MeetingRepositoryImpl)

        # Initialize use cases
        self.manage_usecase = ManageProposalsUseCase(
            self.proposal_repository  # type: ignore[arg-type]
        )
        self.manage_parliamentary_group_judges_usecase = (
            ManageParliamentaryGroupJudgesUseCase(
                judge_repository=self.parliamentary_group_judge_repository,  # type: ignore[arg-type]
                parliamentary_group_repository=self.parliamentary_group_repository,  # type: ignore[arg-type]
            )
        )

        # Session management
        self.session = SessionManager(namespace="proposal")
        self.form_state = self._get_or_create_form_state()

    def _get_or_create_form_state(self) -> FormStateDTO:
        """Get or create form state from session."""
        state_dict = self.session.get("form_state", {})
        if not state_dict:
            state = FormStateDTO()
            self.session.set("form_state", state.__dict__)
            return state
        return FormStateDTO(**state_dict)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("form_state", self.form_state.__dict__)

    def load_data(self) -> list[Proposal]:
        """Load proposals data."""
        result = self.load_data_filtered("all")
        return result.proposals

    def load_data_filtered(
        self,
        filter_type: str = "all",
        status: str | None = None,
        meeting_id: int | None = None,
    ) -> ProposalListOutputDto:
        """Load proposals with filter."""
        return self._run_async(
            self._load_data_filtered_async(filter_type, status, meeting_id)
        )

    async def _load_data_filtered_async(
        self,
        filter_type: str = "all",
        status: str | None = None,
        meeting_id: int | None = None,
    ) -> ProposalListOutputDto:
        """Load proposals with filter (async implementation)."""
        try:
            input_dto = ProposalListInputDto(
                filter_type=filter_type, status=status, meeting_id=meeting_id
            )
            return await self.manage_usecase.list_proposals(input_dto)
        except Exception as e:
            self.logger.error(f"Error loading proposals: {e}", exc_info=True)
            raise

    def create(self, **kwargs: Any) -> CreateProposalOutputDto:
        """Create a new proposal."""
        return self._run_async(self._create_async(**kwargs))

    async def _create_async(self, **kwargs: Any) -> CreateProposalOutputDto:
        """Create a new proposal (async implementation)."""
        input_dto = CreateProposalInputDto(
            content=kwargs["content"],
            status=kwargs.get("status"),
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            submission_date=kwargs.get("submission_date"),
            submitter=kwargs.get("submitter"),
            proposal_number=kwargs.get("proposal_number"),
            meeting_id=kwargs.get("meeting_id"),
            summary=kwargs.get("summary"),
        )
        return await self.manage_usecase.create_proposal(input_dto)

    def update(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal."""
        return self._run_async(self._update_async(**kwargs))

    async def _update_async(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal (async implementation)."""
        input_dto = UpdateProposalInputDto(
            proposal_id=kwargs["proposal_id"],
            content=kwargs.get("content"),
            status=kwargs.get("status"),
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            submission_date=kwargs.get("submission_date"),
            submitter=kwargs.get("submitter"),
            proposal_number=kwargs.get("proposal_number"),
            meeting_id=kwargs.get("meeting_id"),
            summary=kwargs.get("summary"),
        )
        return await self.manage_usecase.update_proposal(input_dto)

    def delete(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal."""
        return self._run_async(self._delete_async(**kwargs))

    async def _delete_async(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal (async implementation)."""
        input_dto = DeleteProposalInputDto(proposal_id=kwargs["proposal_id"])
        return await self.manage_usecase.delete_proposal(input_dto)

    def scrape_proposal(
        self, url: str, meeting_id: int | None = None
    ) -> ScrapeProposalOutputDTO:
        """Scrape proposal from URL."""
        return self._run_async(self._scrape_proposal_async(url, meeting_id))

    async def _scrape_proposal_async(
        self, url: str, meeting_id: int | None = None
    ) -> ScrapeProposalOutputDTO:
        """Scrape proposal from URL (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        scrape_usecase = self.container.use_cases.scrape_proposal_usecase()
        input_dto = ScrapeProposalInputDTO(url=url, meeting_id=meeting_id)
        return await scrape_usecase.scrape_and_save(input_dto)

    def extract_judges(
        self, url: str, proposal_id: int | None = None, force: bool = False
    ) -> ExtractProposalJudgesOutputDTO:
        """Extract judges from proposal status URL."""
        return self._run_async(self._extract_judges_async(url, proposal_id, force))

    async def _extract_judges_async(
        self, url: str, proposal_id: int | None = None, force: bool = False
    ) -> ExtractProposalJudgesOutputDTO:
        """Extract judges from proposal status URL (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = ExtractProposalJudgesInputDTO(
            url=url, proposal_id=proposal_id, force=force
        )
        return await extract_usecase.extract_judges(input_dto)

    def match_judges(
        self, proposal_id: int | None = None
    ) -> MatchProposalJudgesOutputDTO:
        """Match extracted judges with politicians."""
        return self._run_async(self._match_judges_async(proposal_id))

    async def _match_judges_async(
        self, proposal_id: int | None = None
    ) -> MatchProposalJudgesOutputDTO:
        """Match extracted judges with politicians (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = MatchProposalJudgesInputDTO(proposal_id=proposal_id)
        return await extract_usecase.match_judges(input_dto)

    def create_judges_from_matched(
        self, proposal_id: int | None = None
    ) -> CreateProposalJudgesOutputDTO:
        """Create proposal judges from matched extracted judges."""
        return self._run_async(self._create_judges_from_matched_async(proposal_id))

    async def _create_judges_from_matched_async(
        self, proposal_id: int | None = None
    ) -> CreateProposalJudgesOutputDTO:
        """Create proposal judges from matched extracted judges (async)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = CreateProposalJudgesInputDTO(proposal_id=proposal_id)
        return await extract_usecase.create_judges(input_dto)

    def load_extracted_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Load extracted judges."""
        return self._run_async(self._load_extracted_judges_async(proposal_id))

    async def _load_extracted_judges_async(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Load extracted judges (async implementation)."""
        if proposal_id:
            return await self.extracted_judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        else:
            return await self.extracted_judge_repository.get_all()  # type: ignore[attr-defined]

    def load_proposal_judges(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Load final proposal judges."""
        return self._run_async(self._load_proposal_judges_async(proposal_id))

    async def _load_proposal_judges_async(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Load final proposal judges (async implementation)."""
        if proposal_id:
            return await self.judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        else:
            return await self.judge_repository.get_all()  # type: ignore[attr-defined]

    def to_dataframe(self, proposals: list[Proposal]) -> pd.DataFrame:
        """Convert proposals to DataFrame for display."""
        if not proposals:
            return pd.DataFrame(
                {
                    "ID": [],
                    "議案番号": [],
                    "内容": [],
                    "状態": [],
                    "提出者": [],
                    "提出日": [],
                }
            )

        data = []
        for proposal in proposals:
            data.append(
                {
                    "ID": proposal.id,
                    "議案番号": proposal.proposal_number or "未設定",
                    "内容": (
                        proposal.content[:50] + "..."
                        if len(proposal.content) > 50
                        else proposal.content
                    ),
                    "状態": proposal.status or "未設定",
                    "提出者": proposal.submitter or "未設定",
                    "提出日": proposal.submission_date or "未設定",
                }
            )

        return pd.DataFrame(data)

    def extracted_judges_to_dataframe(
        self, judges: list[ExtractedProposalJudge]
    ) -> pd.DataFrame:
        """Convert extracted judges to DataFrame for display."""
        if not judges:
            return pd.DataFrame(
                {
                    "ID": [],
                    "政治家名": [],
                    "議員団名": [],
                    "賛否": [],
                    "信頼度": [],
                    "ステータス": [],
                }
            )

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "政治家名": judge.extracted_politician_name or "未設定",
                    "議員団名": judge.extracted_parliamentary_group_name or "未設定",
                    "賛否": judge.extracted_judgment or "未設定",
                    "信頼度": (
                        f"{judge.matching_confidence:.2f}"
                        if judge.matching_confidence
                        else "未実施"
                    ),
                    "ステータス": judge.matching_status or "pending",
                }
            )

        return pd.DataFrame(data)

    def proposal_judges_to_dataframe(self, judges: list[ProposalJudge]) -> pd.DataFrame:
        """Convert proposal judges to DataFrame for display."""
        if not judges:
            return pd.DataFrame({"ID": [], "政治家ID": [], "賛否": []})

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "政治家ID": judge.politician_id or "未設定",
                    "賛否": judge.approve or "未設定",
                }
            )

        return pd.DataFrame(data)

    def set_editing_mode(self, proposal_id: int) -> None:
        """Set form to editing mode."""
        self.form_state.set_editing(proposal_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, proposal_id: int) -> bool:
        """Check if editing."""
        return self.form_state.is_editing and self.form_state.current_id == proposal_id

    def read(self, **kwargs: Any) -> Proposal | None:
        """Read a single proposal by ID.

        Args:
            **kwargs: Must include proposal_id

        Returns:
            Proposal entity or None if not found
        """
        proposal_id = kwargs.get("proposal_id")
        if not proposal_id:
            raise ValueError("proposal_id is required")

        return self._run_async(
            self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        )

    def list(self, **kwargs: Any) -> list[Proposal]:
        """List all proposals.

        Args:
            **kwargs: Can include filter_type, status, meeting_id

        Returns:
            List of proposals
        """
        filter_type = kwargs.get("filter_type", "all")
        status = kwargs.get("status")
        meeting_id = kwargs.get("meeting_id")
        result = self.load_data_filtered(filter_type, status, meeting_id)
        return result.proposals

    # ========== Parliamentary Group Judge Methods (Issue #1007) ==========

    def load_parliamentary_group_judges(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudgeDTO]:
        """会派賛否一覧を取得する.

        Args:
            proposal_id: 議案ID

        Returns:
            会派賛否DTOのリスト
        """
        return cast(
            list[ProposalParliamentaryGroupJudgeDTO],
            self._run_async(self._load_parliamentary_group_judges_async(proposal_id)),
        )

    async def _load_parliamentary_group_judges_async(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudgeDTO]:
        """会派賛否一覧を取得する（非同期実装）."""
        result = await self.manage_parliamentary_group_judges_usecase.list_by_proposal(
            proposal_id
        )
        return cast(list[ProposalParliamentaryGroupJudgeDTO], result.judges)

    def create_parliamentary_group_judge(
        self,
        proposal_id: int,
        parliamentary_group_id: int,
        judgment: str,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派賛否を新規登録する.

        Args:
            proposal_id: 議案ID
            parliamentary_group_id: 会派ID
            judgment: 賛否（賛成/反対/棄権/欠席）
            member_count: 人数
            note: 備考

        Returns:
            作成結果DTO
        """
        return self._run_async(
            self._create_parliamentary_group_judge_async(
                proposal_id, parliamentary_group_id, judgment, member_count, note
            )
        )

    async def _create_parliamentary_group_judge_async(
        self,
        proposal_id: int,
        parliamentary_group_id: int,
        judgment: str,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派賛否を新規登録する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.create(
            proposal_id=proposal_id,
            parliamentary_group_id=parliamentary_group_id,
            judgment=judgment,
            member_count=member_count,
            note=note,
        )

    def update_parliamentary_group_judge(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する.

        Args:
            judge_id: 会派賛否ID
            judgment: 賛否（賛成/反対/棄権/欠席）
            member_count: 人数
            note: 備考

        Returns:
            更新結果DTO
        """
        return self._run_async(
            self._update_parliamentary_group_judge_async(
                judge_id, judgment, member_count, note
            )
        )

    async def _update_parliamentary_group_judge_async(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.update(
            judge_id=judge_id,
            judgment=judgment,
            member_count=member_count,
            note=note,
        )

    def delete_parliamentary_group_judge(self, judge_id: int) -> DeleteJudgeOutputDTO:
        """会派賛否を削除する.

        Args:
            judge_id: 会派賛否ID

        Returns:
            削除結果DTO
        """
        return self._run_async(self._delete_parliamentary_group_judge_async(judge_id))

    async def _delete_parliamentary_group_judge_async(
        self, judge_id: int
    ) -> DeleteJudgeOutputDTO:
        """会派賛否を削除する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.delete(judge_id)

    def load_parliamentary_groups_for_proposal(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ParliamentaryGroup]:
        """議案に関連する会派一覧を取得する.

        議案 → 会議 → 会議体 → 会派の流れで取得します。

        Args:
            proposal_id: 議案ID

        Returns:
            会派エンティティのリスト
        """
        return cast(
            list[ParliamentaryGroup],
            self._run_async(
                self._load_parliamentary_groups_for_proposal_async(proposal_id)
            ),
        )

    async def _load_parliamentary_groups_for_proposal_async(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ParliamentaryGroup]:
        """議案に関連する会派一覧を取得する（非同期実装）."""
        # 議案を取得
        proposal = await self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        if not proposal or not proposal.meeting_id:
            return []

        # 会議から会議体IDを取得
        meeting = await self.meeting_repository.get_by_id(proposal.meeting_id)  # type: ignore[attr-defined]
        if not meeting:
            return []

        # 会議体IDから会派一覧を取得
        groups = await self.parliamentary_group_repository.get_by_conference_id(  # type: ignore[attr-defined]
            meeting.conference_id, active_only=True
        )
        return cast(list[ParliamentaryGroup], groups)

    def parliamentary_group_judges_to_dataframe(
        self, judges: list[ProposalParliamentaryGroupJudgeDTO]
    ) -> pd.DataFrame:
        """会派賛否DTOリストをDataFrameに変換する."""
        if not judges:
            return pd.DataFrame(
                {
                    "ID": [],
                    "会派名": [],
                    "賛否": [],
                    "人数": [],
                    "備考": [],
                    "登録日時": [],
                }
            )

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "会派名": judge.parliamentary_group_name,
                    "賛否": judge.judgment,
                    "人数": judge.member_count if judge.member_count else "-",
                    "備考": judge.note if judge.note else "-",
                    "登録日時": judge.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )

        return pd.DataFrame(data)
