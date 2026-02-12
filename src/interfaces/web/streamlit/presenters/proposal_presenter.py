"""Presenter for proposal management in Streamlit.

This module provides the presenter layer for proposal management,
handling UI state and coordinating with use cases.
"""

from __future__ import annotations

import asyncio

from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID

import pandas as pd

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesPreviewDTO,
    ExpandGroupJudgesRequestDTO,
    ExpandGroupJudgesResultDTO,
    GroupJudgePreviewItem,
    GroupJudgePreviewMember,
)
from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
)
from src.application.dtos.submitter_candidates_dto import SubmitterCandidatesDTO
from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
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
from src.application.usecases.manage_proposal_submitter_usecase import (
    ClearSubmitterOutputDTO,
    ManageProposalSubmitterUseCase,
    SetSubmitterOutputDTO,
    UpdateSubmittersOutputDTO,
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
from src.domain.entities.politician import Politician
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.conference_member_repository_impl import (
    ConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_operation_log_repository_impl import (
    ProposalOperationLogRepositoryImpl,
)
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (  # noqa: E501
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.proposal_submitter_repository_impl import (
    ProposalSubmitterRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.dto.base import FormStateDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


def _build_related_data_map_from_cache(
    proposals: list[Proposal],
    meeting_conference_map: dict[int, int | None],
    conference_detail_map: dict[int, dict[str, Any]],
    governing_body_name_map: dict[int, str],
) -> dict[int, dict[str, str | None]]:
    """キャッシュ済みマスターデータから議案の関連データマップを構築する."""
    result: dict[int, dict[str, str | None]] = {}
    for p in proposals:
        if p.id is None:
            continue

        conference_id = p.conference_id
        if not conference_id and p.meeting_id:
            conference_id = meeting_conference_map.get(p.meeting_id)

        conference_name: str | None = None
        governing_body_name: str | None = None

        if conference_id and conference_id in conference_detail_map:
            conf_data = conference_detail_map[conference_id]
            conference_name = conf_data["name"]
            gb_id = conf_data["governing_body_id"]
            if gb_id and gb_id in governing_body_name_map:
                governing_body_name = governing_body_name_map[gb_id]

        result[p.id] = {
            "conference_name": conference_name,
            "governing_body_name": governing_body_name,
        }
    return result


@dataclass
class _ProposalsMasterDataCache:
    """ページ切替間で再利用するマスターデータキャッシュ."""

    politician_names: dict[int, str]
    conference_names: dict[int, str]
    pg_names: dict[int, str]
    meeting_conference_map: dict[int, int | None]
    conference_detail_map: dict[int, dict[str, Any]]
    governing_body_name_map: dict[int, str]


@dataclass
class ProposalsPageData:
    """議案一覧ページの一括取得データ."""

    result: ProposalListOutputDto
    related_data_map: dict[int, dict[str, str | None]] = field(default_factory=dict)
    submitters_map: dict[int, list[ProposalSubmitter]] = field(default_factory=dict)
    politician_names: dict[int, str] = field(default_factory=dict)
    conference_names: dict[int, str] = field(default_factory=dict)
    pg_names: dict[int, str] = field(default_factory=dict)


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
        self.politician_repository = RepositoryAdapter(PoliticianRepositoryImpl)
        self.meeting_repository = RepositoryAdapter(MeetingRepositoryImpl)
        self.conference_repository = RepositoryAdapter(ConferenceRepositoryImpl)
        self.governing_body_repository = RepositoryAdapter(GoverningBodyRepositoryImpl)
        self.operation_log_repository = RepositoryAdapter(
            ProposalOperationLogRepositoryImpl
        )
        self.submitter_repository = RepositoryAdapter(ProposalSubmitterRepositoryImpl)
        self.conference_member_repository = RepositoryAdapter(
            ConferenceMemberRepositoryImpl
        )
        self.membership_repository = RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl
        )

        # Initialize use cases
        self.manage_usecase = ManageProposalsUseCase(
            repository=self.proposal_repository,  # type: ignore[arg-type]
            operation_log_repository=self.operation_log_repository,  # type: ignore[arg-type]
        )
        self.manage_parliamentary_group_judges_usecase = (
            ManageParliamentaryGroupJudgesUseCase(
                judge_repository=self.parliamentary_group_judge_repository,  # type: ignore[arg-type]
                parliamentary_group_repository=self.parliamentary_group_repository,  # type: ignore[arg-type]
                politician_repository=self.politician_repository,  # type: ignore[arg-type]
            )
        )
        self.manage_submitter_usecase = ManageProposalSubmitterUseCase(
            proposal_repository=self.proposal_repository,  # type: ignore[arg-type]
            proposal_submitter_repository=self.submitter_repository,  # type: ignore[arg-type]
            meeting_repository=self.meeting_repository,  # type: ignore[arg-type]
            conference_member_repository=self.conference_member_repository,  # type: ignore[arg-type]
            parliamentary_group_repository=self.parliamentary_group_repository,  # type: ignore[arg-type]
            politician_repository=self.politician_repository,  # type: ignore[arg-type]
            conference_repository=self.conference_repository,  # type: ignore[arg-type]
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

    def get_current_user_id(self) -> UUID | None:
        """現在ログインしているユーザーのIDを取得する."""
        user_info = google_sign_in.get_user_info()
        if not user_info:
            return None

        try:
            auth_usecase = AuthenticateUserUseCase(
                user_repository=self.container.repositories.user_repository()
            )
            email = user_info.get("email", "")
            name = user_info.get("name")
            user = asyncio.run(auth_usecase.execute(email=email, name=name))
            return user.user_id
        except Exception:
            return None

    def load_data(self) -> list[Proposal]:
        """Load proposals data."""
        result = self.load_data_filtered("all")
        return result.proposals

    def load_proposal_by_id(self, proposal_id: int) -> Proposal | None:
        """IDを指定して議案を1件取得する."""
        return self._run_async(self._load_proposal_by_id_async(proposal_id))

    async def _load_proposal_by_id_async(self, proposal_id: int) -> Proposal | None:
        """IDを指定して議案を1件取得する（非同期実装）."""
        try:
            return await self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        except Exception:
            self.logger.exception(f"議案ID {proposal_id} の読み込みに失敗")
            return None

    def load_data_filtered(
        self,
        filter_type: str = "all",
        meeting_id: int | None = None,
        conference_id: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> ProposalListOutputDto:
        """Load proposals with filter."""
        return self._run_async(
            self._load_data_filtered_async(
                filter_type, meeting_id, conference_id, limit, offset
            )
        )

    async def _load_data_filtered_async(
        self,
        filter_type: str = "all",
        meeting_id: int | None = None,
        conference_id: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> ProposalListOutputDto:
        """Load proposals with filter (async implementation)."""
        try:
            input_dto = ProposalListInputDto(
                filter_type=filter_type,
                meeting_id=meeting_id,
                conference_id=conference_id,
                limit=limit,
                offset=offset,
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
            title=kwargs["title"],
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            votes_url=kwargs.get("votes_url"),
            meeting_id=kwargs.get("meeting_id"),
            conference_id=kwargs.get("conference_id"),
            user_id=kwargs.get("user_id"),
        )
        return await self.manage_usecase.create_proposal(input_dto)

    def update(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal."""
        return self._run_async(self._update_async(**kwargs))

    async def _update_async(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal (async implementation)."""
        input_dto = UpdateProposalInputDto(
            proposal_id=kwargs["proposal_id"],
            title=kwargs.get("title"),
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            votes_url=kwargs.get("votes_url"),
            meeting_id=kwargs.get("meeting_id"),
            conference_id=kwargs.get("conference_id"),
            user_id=kwargs.get("user_id"),
        )
        return await self.manage_usecase.update_proposal(input_dto)

    def delete(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal."""
        return self._run_async(self._delete_async(**kwargs))

    async def _delete_async(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal (async implementation)."""
        input_dto = DeleteProposalInputDto(
            proposal_id=kwargs["proposal_id"],
            user_id=kwargs.get("user_id"),
        )
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

    def load_politicians(self) -> list[Politician]:
        """Load all politicians for selection."""
        return self._run_async(self._load_politicians_async())

    async def _load_politicians_async(self) -> list[Politician]:
        """Load all politicians (async implementation)."""
        return await self.politician_repository.get_all()  # type: ignore[attr-defined]

    def load_meetings(self) -> list[dict[str, Any]]:
        """Load all meetings for selection."""
        return self._run_async(self._load_meetings_async())

    async def _load_meetings_async(self) -> list[dict[str, Any]]:
        """Load all meetings (async implementation).

        会議の表示名は「会議体名 + 開催日」の形式で構築する。
        """
        meetings = await self.meeting_repository.get_all()  # type: ignore[attr-defined]

        # 会議体のマップを一括取得で構築（N+1問題対策）
        conference_ids = {m.conference_id for m in meetings if m.conference_id}
        all_conferences = await self.conference_repository.get_all()  # type: ignore[attr-defined]
        conference_map: dict[int, str] = {
            c.id: c.name for c in all_conferences if c.id in conference_ids
        }

        result = []
        for m in meetings:
            # 表示名を構築: 会議体名 + 開催日
            conference_name = (
                conference_map.get(m.conference_id, "") if m.conference_id else ""
            )
            date_str = m.date.strftime("%Y-%m-%d") if m.date else ""

            if conference_name and date_str:
                display_name = f"{conference_name} ({date_str})"
            elif conference_name:
                display_name = conference_name
            elif m.name:
                display_name = m.name
            else:
                display_name = f"会議ID: {m.id}"

            result.append({"id": m.id, "name": display_name, "date": m.date})

        return result

    def load_conferences(self) -> list[dict[str, Any]]:
        """Load all conferences for selection."""
        return self._run_async(self._load_conferences_async())

    async def _load_conferences_async(self) -> list[dict[str, Any]]:
        """Load all conferences (async implementation)."""
        conferences = await self.conference_repository.get_all()  # type: ignore[attr-defined]
        return [{"id": c.id, "name": c.name} for c in conferences]

    def load_conferences_by_governing_body(
        self, governing_body_id: int
    ) -> list[dict[str, Any]]:
        """指定された開催主体に属する会議体を取得する."""
        return self._run_async(
            self._load_conferences_by_governing_body_async(governing_body_id)
        )

    async def _load_conferences_by_governing_body_async(
        self, governing_body_id: int
    ) -> list[dict[str, Any]]:
        """指定された開催主体に属する会議体を取得する（非同期実装）."""
        conferences = await self.conference_repository.get_by_governing_body(  # type: ignore[attr-defined]
            governing_body_id
        )
        return [{"id": c.id, "name": c.name} for c in conferences]

    def load_governing_bodies(self) -> list[dict[str, Any]]:
        """Load all governing bodies for selection."""
        return self._run_async(self._load_governing_bodies_async())

    async def _load_governing_bodies_async(self) -> list[dict[str, Any]]:
        """Load all governing bodies (async implementation)."""
        governing_bodies = await self.governing_body_repository.get_all()  # type: ignore[attr-defined]
        return [{"id": g.id, "name": g.name} for g in governing_bodies]

    def build_proposal_related_data_map(
        self, proposals: list[Proposal]
    ) -> dict[int, dict[str, str | None]]:
        """議案一覧から、会議体名・開催主体名のマップを構築する.

        N+1問題を避けるため、一括でデータを取得してマップ化する。

        Args:
            proposals: 議案のリスト

        Returns:
            議案ID -> {"conference_name": str | None, "governing_body_name": str | None}
        """
        return self._run_async(self._build_proposal_related_data_map_async(proposals))

    async def _build_proposal_related_data_map_async(
        self, proposals: list[Proposal]
    ) -> dict[int, dict[str, str | None]]:
        """議案一覧から、会議体名・開催主体名のマップを構築する（非同期実装）."""
        result: dict[int, dict[str, str | None]] = {}

        # 議案からconference_idとmeeting_idを収集
        conference_ids: set[int] = set()
        meeting_ids: set[int] = set()
        for p in proposals:
            if p.conference_id:
                conference_ids.add(p.conference_id)
            if p.meeting_id:
                meeting_ids.add(p.meeting_id)

        # 会議情報を一括取得してconference_idを追加収集
        meeting_conference_map: dict[int, int | None] = {}
        if meeting_ids:
            all_meetings = await self.meeting_repository.get_all()  # type: ignore[attr-defined]
            for meeting in all_meetings:
                if meeting.id in meeting_ids:
                    meeting_conference_map[meeting.id] = meeting.conference_id
                    if meeting.conference_id:
                        conference_ids.add(meeting.conference_id)

        # 会議体情報を一括取得
        conference_map: dict[int, dict[str, Any]] = {}
        governing_body_ids: set[int] = set()
        all_conferences = await self.conference_repository.get_all()  # type: ignore[attr-defined]
        for conference in all_conferences:
            if conference.id in conference_ids:
                conference_map[conference.id] = {
                    "name": conference.name,
                    "governing_body_id": conference.governing_body_id,
                }
                governing_body_ids.add(conference.governing_body_id)

        # 開催主体情報を一括取得
        governing_body_map: dict[int, str] = {}
        all_governing_bodies = await self.governing_body_repository.get_all()  # type: ignore[attr-defined]
        for governing_body in all_governing_bodies:
            if governing_body.id in governing_body_ids:
                governing_body_map[governing_body.id] = governing_body.name

        # 各議案のマップを構築
        for p in proposals:
            if p.id is None:
                continue

            conference_id = p.conference_id
            if not conference_id and p.meeting_id:
                conference_id = meeting_conference_map.get(p.meeting_id)

            conference_name: str | None = None
            governing_body_name: str | None = None

            if conference_id and conference_id in conference_map:
                conf_data = conference_map[conference_id]
                conference_name = conf_data["name"]
                gb_id = conf_data["governing_body_id"]
                if gb_id and gb_id in governing_body_map:
                    governing_body_name = governing_body_map[gb_id]

            result[p.id] = {
                "conference_name": conference_name,
                "governing_body_name": governing_body_name,
            }

        return result

    def to_dataframe(self, proposals: list[Proposal]) -> pd.DataFrame:
        """Convert proposals to DataFrame for display."""
        if not proposals:
            return pd.DataFrame(
                {
                    "ID": [],
                    "タイトル": [],
                    "会議ID": [],
                    "会議体ID": [],
                }
            )

        data = []
        for proposal in proposals:
            data.append(
                {
                    "ID": proposal.id,
                    "タイトル": (
                        proposal.title[:50] + "..."
                        if len(proposal.title) > 50
                        else proposal.title
                    ),
                    "会議ID": proposal.meeting_id or "未設定",
                    "会議体ID": proposal.conference_id or "未設定",
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
            **kwargs: Can include filter_type, meeting_id, conference_id

        Returns:
            List of proposals
        """
        filter_type = kwargs.get("filter_type", "all")
        meeting_id = kwargs.get("meeting_id")
        conference_id = kwargs.get("conference_id")
        result = self.load_data_filtered(filter_type, meeting_id, conference_id)
        return result.proposals

    # ========== Submitter Methods ==========

    def load_submitters(self, proposal_id: int) -> list[ProposalSubmitter]:
        """Load submitters for a proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalSubmitter entities
        """
        return self._run_async(self._load_submitters_async(proposal_id))

    async def _load_submitters_async(self, proposal_id: int) -> list[ProposalSubmitter]:
        """Load submitters for a proposal (async implementation)."""
        return await self.submitter_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]

    def load_submitters_batch(
        self, proposal_ids: list[int]
    ) -> dict[int, list[ProposalSubmitter]]:
        """複数議案の提出者を一括取得する.

        Args:
            proposal_ids: 議案IDのリスト

        Returns:
            議案IDをキー、提出者リストを値とする辞書
        """
        return self._run_async(self._load_submitters_batch_async(proposal_ids))

    async def _load_submitters_batch_async(
        self, proposal_ids: list[int]
    ) -> dict[int, list[ProposalSubmitter]]:
        """複数議案の提出者を一括取得する（async実装）."""
        return await self.submitter_repository.get_by_proposal_ids(proposal_ids)  # type: ignore[attr-defined]

    def load_all_parliamentary_group_names(self) -> dict[int, str]:
        """全アクティブ会派のID→名前マップを取得する."""
        return self._run_async(self._load_all_parliamentary_group_names_async())

    async def _load_all_parliamentary_group_names_async(
        self,
    ) -> dict[int, str]:
        """全アクティブ会派のID→名前マップを取得する（async実装）."""
        groups = await self.parliamentary_group_repository.get_active()  # type: ignore[attr-defined]
        return {g.id: g.name for g in groups if g.id}

    def load_proposals_page_data(
        self,
        filter_type: str = "all",
        meeting_id: int | None = None,
        conference_id: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> ProposalsPageData:
        """議案一覧ページのデータを1回のasync呼び出しで一括取得する.

        _run_async呼び出しを1回に統合し、fragment内でのevent loopブロックを最小化。
        マスターデータ（政治家・会議体・会派等）はセッションキャッシュを使用し、
        ページ切替時の再取得を省略する。
        """
        import streamlit as st

        cache_key = "_proposals_master_cache"
        cache: _ProposalsMasterDataCache | None = st.session_state.get(cache_key)

        page_data, new_cache = self._run_async(
            self._load_proposals_page_data_async(
                filter_type,
                meeting_id,
                conference_id,
                limit,
                offset,
                master_cache=cache,
            )
        )

        # 初回取得後にキャッシュ保存
        if new_cache is not None:
            st.session_state[cache_key] = new_cache

        return page_data

    async def _load_proposals_page_data_async(
        self,
        filter_type: str = "all",
        meeting_id: int | None = None,
        conference_id: int | None = None,
        limit: int | None = None,
        offset: int = 0,
        master_cache: _ProposalsMasterDataCache | None = None,
    ) -> tuple[ProposalsPageData, _ProposalsMasterDataCache | None]:
        """議案一覧ページのデータを一括取得する（async実装）.

        master_cache が提供された場合、マスターデータの再取得をスキップし、
        ページ固有データ（議案・提出者）のみ取得する。
        初回取得時も get_all() ではなく get_by_ids() で必要なIDのみ取得する。
        """
        # 1. フィルタ付き議案取得
        result = await self._load_data_filtered_async(
            filter_type, meeting_id, conference_id, limit, offset
        )
        proposals = result.proposals

        if not proposals:
            return ProposalsPageData(result=result), None

        # 2. 提出者を一括取得（ページ固有データ）
        page_proposal_ids = [p.id for p in proposals if p.id is not None]
        submitters_map: dict[int, list[ProposalSubmitter]] = {}
        if page_proposal_ids:
            submitters_map = await self._load_submitters_batch_async(page_proposal_ids)

        if master_cache is not None:
            politician_names = master_cache.politician_names
            conference_names = master_cache.conference_names
            pg_names = master_cache.pg_names
            related_data_map = _build_related_data_map_from_cache(
                proposals,
                master_cache.meeting_conference_map,
                master_cache.conference_detail_map,
                master_cache.governing_body_name_map,
            )
            return ProposalsPageData(
                result=result,
                related_data_map=related_data_map,
                submitters_map=submitters_map,
                politician_names=politician_names,
                conference_names=conference_names,
                pg_names=pg_names,
            ), None

        # 3. ページ内の議案・提出者から必要なIDを収集
        needed_meeting_ids: set[int] = set()
        needed_conference_ids: set[int] = set()
        needed_politician_ids: set[int] = set()
        needed_pg_ids: set[int] = set()

        for p in proposals:
            if p.meeting_id:
                needed_meeting_ids.add(p.meeting_id)
            if p.conference_id:
                needed_conference_ids.add(p.conference_id)

        for subs in submitters_map.values():
            for s in subs:
                if s.politician_id:
                    needed_politician_ids.add(s.politician_id)
                if s.parliamentary_group_id:
                    needed_pg_ids.add(s.parliamentary_group_id)

        # 4. 第1段階: meetings・politicians・pg を並行取得
        meetings_coro = (
            self.meeting_repository.get_by_ids(list(needed_meeting_ids))  # type: ignore[attr-defined]
            if needed_meeting_ids
            else asyncio.sleep(0, result=[])
        )
        politicians_coro = (
            self.politician_repository.get_by_ids(list(needed_politician_ids))  # type: ignore[attr-defined]
            if needed_politician_ids
            else asyncio.sleep(0, result=[])
        )
        pg_groups_coro = (
            self.parliamentary_group_repository.get_by_ids(list(needed_pg_ids))  # type: ignore[attr-defined]
            if needed_pg_ids
            else asyncio.sleep(0, result=[])
        )

        fetched_meetings, fetched_politicians, fetched_pg_groups = await asyncio.gather(
            meetings_coro, politicians_coro, pg_groups_coro
        )

        # meetingから追加のconference_idを収集
        for m in fetched_meetings:
            if m.conference_id:
                needed_conference_ids.add(m.conference_id)

        # 5. 第2段階: conferences取得
        fetched_conferences = (
            await self.conference_repository.get_by_ids(list(needed_conference_ids))  # type: ignore[attr-defined]
            if needed_conference_ids
            else []
        )

        # conferenceからgoverning_body_idを収集
        needed_gb_ids: set[int] = set()
        for c in fetched_conferences:
            if c.governing_body_id:
                needed_gb_ids.add(c.governing_body_id)

        # 6. 第3段階: governing_bodies取得
        fetched_governing_bodies = (
            await self.governing_body_repository.get_by_ids(list(needed_gb_ids))  # type: ignore[attr-defined]
            if needed_gb_ids
            else []
        )

        # 7. マップ構築
        meeting_conference_map: dict[int, int | None] = {
            m.id: m.conference_id for m in fetched_meetings if m.id is not None
        }
        conference_detail_map: dict[int, dict[str, Any]] = {
            c.id: {"name": c.name, "governing_body_id": c.governing_body_id}
            for c in fetched_conferences
            if c.id is not None
        }
        governing_body_name_map: dict[int, str] = {
            g.id: g.name for g in fetched_governing_bodies if g.id is not None
        }
        politician_names: dict[int, str] = {
            p.id: p.name for p in fetched_politicians if p.id is not None
        }
        conference_names: dict[int, str] = {
            c.id: c.name for c in fetched_conferences if c.id is not None
        }
        pg_names: dict[int, str] = {g.id: g.name for g in fetched_pg_groups if g.id}

        related_data_map = _build_related_data_map_from_cache(
            proposals,
            meeting_conference_map,
            conference_detail_map,
            governing_body_name_map,
        )

        new_cache = _ProposalsMasterDataCache(
            politician_names=politician_names,
            conference_names=conference_names,
            pg_names=pg_names,
            meeting_conference_map=meeting_conference_map,
            conference_detail_map=conference_detail_map,
            governing_body_name_map=governing_body_name_map,
        )

        return ProposalsPageData(
            result=result,
            related_data_map=related_data_map,
            submitters_map=submitters_map,
            politician_names=politician_names,
            conference_names=conference_names,
            pg_names=pg_names,
        ), new_cache

    def update_submitters(
        self,
        proposal_id: int,
        politician_ids: list[int] | None = None,
        conference_ids: list[int] | None = None,
        parliamentary_group_id: int | None = None,
        other_submitter: tuple[SubmitterType, str] | None = None,
    ) -> UpdateSubmittersOutputDTO:
        """Update submitters for a proposal.

        This method deletes existing submitters and creates new ones.
        Uses ManageProposalSubmitterUseCase for business logic.

        Args:
            proposal_id: ID of the proposal
            politician_ids: List of politician IDs to set as submitters
            conference_ids: List of conference IDs to set as submitters
            parliamentary_group_id: Parliamentary group ID (single)
            other_submitter: Tuple of (SubmitterType, raw_name) for other types

        Returns:
            UpdateSubmittersOutputDTO with operation result
        """
        return self._run_async(
            self._update_submitters_async(
                proposal_id,
                politician_ids,
                conference_ids,
                parliamentary_group_id,
                other_submitter,
            )
        )

    async def _update_submitters_async(
        self,
        proposal_id: int,
        politician_ids: list[int] | None = None,
        conference_ids: list[int] | None = None,
        parliamentary_group_id: int | None = None,
        other_submitter: tuple[SubmitterType, str] | None = None,
    ) -> UpdateSubmittersOutputDTO:
        """Update submitters for a proposal (async implementation).

        Delegates to ManageProposalSubmitterUseCase.
        """
        return await self.manage_submitter_usecase.update_submitters(
            proposal_id=proposal_id,
            politician_ids=politician_ids,
            conference_ids=conference_ids,
            parliamentary_group_id=parliamentary_group_id,
            other_submitter=other_submitter,
        )

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
        judgment: str,
        judge_type: str = "parliamentary_group",
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派/政治家賛否を新規登録する.

        Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。

        Args:
            proposal_id: 議案ID
            judgment: 賛否（賛成/反対/棄権/欠席）
            judge_type: 賛否種別（parliamentary_group/politician）
            parliamentary_group_ids: 会派IDのリスト（会派単位の場合）
            politician_ids: 政治家IDのリスト（政治家単位の場合）
            member_count: 人数（会派単位の場合）
            note: 備考

        Returns:
            作成結果DTO
        """
        return self._run_async(
            self._create_parliamentary_group_judge_async(
                proposal_id,
                judgment,
                judge_type,
                parliamentary_group_ids,
                politician_ids,
                member_count,
                note,
            )
        )

    async def _create_parliamentary_group_judge_async(
        self,
        proposal_id: int,
        judgment: str,
        judge_type: str = "parliamentary_group",
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派/政治家賛否を新規登録する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.create(
            proposal_id=proposal_id,
            judgment=judgment,
            judge_type=judge_type,
            parliamentary_group_ids=parliamentary_group_ids,
            politician_ids=politician_ids,
            member_count=member_count,
            note=note,
        )

    def update_parliamentary_group_judge(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する.

        Args:
            judge_id: 会派賛否ID
            judgment: 賛否（賛成/反対/棄権/欠席）
            member_count: 人数
            note: 備考
            parliamentary_group_ids: 紐付ける会派IDのリスト（Noneの場合は変更しない）
            politician_ids: 紐付ける政治家IDのリスト（Noneの場合は変更しない）

        Returns:
            更新結果DTO
        """
        return self._run_async(
            self._update_parliamentary_group_judge_async(
                judge_id,
                judgment,
                member_count,
                note,
                parliamentary_group_ids,
                politician_ids,
            )
        )

    async def _update_parliamentary_group_judge_async(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.update(
            judge_id=judge_id,
            judgment=judgment,
            member_count=member_count,
            note=note,
            parliamentary_group_ids=parliamentary_group_ids,
            politician_ids=politician_ids,
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
        if not proposal:
            return []

        # conference_idを取得（直接設定されている場合はそれを使用）
        conference_id: int | None = None
        if proposal.conference_id:
            conference_id = proposal.conference_id
        elif proposal.meeting_id:
            # 会議から会議体IDを取得
            meeting = await self.meeting_repository.get_by_id(proposal.meeting_id)  # type: ignore[attr-defined]
            if meeting:
                conference_id = meeting.conference_id

        if not conference_id:
            return []

        # conference_id → governing_body_id を解決して会派一覧を取得
        conference = await self.conference_repository.get_by_id(conference_id)  # type: ignore[attr-defined]
        if not conference:
            return []

        groups = await self.parliamentary_group_repository.get_by_governing_body_id(  # type: ignore[attr-defined]
            conference.governing_body_id, active_only=True
        )
        return cast(list[ParliamentaryGroup], groups)

    def load_politicians_for_proposal(self, proposal_id: int) -> list[Politician]:
        """議案に関連する政治家一覧を取得する.

        議案 → 会議 → 会議体 → 政治家の流れで取得します。

        Args:
            proposal_id: 議案ID

        Returns:
            政治家エンティティのリスト
        """
        return cast(
            list[Politician],
            self._run_async(self._load_politicians_for_proposal_async(proposal_id)),
        )

    async def _load_politicians_for_proposal_async(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[Politician]:
        """議案に紐付け可能な政治家一覧を取得する（非同期実装）.

        Args:
            proposal_id: 議案ID（将来的な絞り込み用、現在は未使用）

        Returns:
            全政治家のリスト
        """
        _ = proposal_id  # 将来的な絞り込み用に引数は残す
        politicians = await self.politician_repository.get_all()  # type: ignore[attr-defined]
        return cast(list[Politician], politicians)

    def parliamentary_group_judges_to_dataframe(
        self, judges: list[ProposalParliamentaryGroupJudgeDTO]
    ) -> pd.DataFrame:
        """会派/政治家賛否DTOリストをDataFrameに変換する.

        Many-to-Many構造対応: 複数の会派名・政治家名をカンマ区切りで表示。
        """
        if not judges:
            return pd.DataFrame(
                {
                    "ID": [],
                    "種別": [],
                    "会派/政治家": [],
                    "賛否": [],
                    "人数": [],
                    "備考": [],
                    "登録日時": [],
                }
            )

        data = []
        for judge in judges:
            if judge.judge_type == "parliamentary_group":
                judge_type_display = "会派"
                # 複数の会派名をカンマ区切りで結合
                if judge.parliamentary_group_names:
                    name_display = ", ".join(judge.parliamentary_group_names)
                else:
                    name_display = "（不明）"
            else:
                judge_type_display = "政治家"
                # 複数の政治家名をカンマ区切りで結合
                if judge.politician_names:
                    name_display = ", ".join(judge.politician_names)
                else:
                    name_display = "（不明）"

            created_at_str = "-"
            if judge.created_at:
                created_at_str = judge.created_at.strftime("%Y-%m-%d %H:%M")

            data.append(
                {
                    "ID": judge.id,
                    "種別": judge_type_display,
                    "会派/政治家": name_display,
                    "賛否": judge.judgment,
                    "人数": judge.member_count if judge.member_count else "-",
                    "備考": judge.note if judge.note else "-",
                    "登録日時": created_at_str,
                }
            )

        return pd.DataFrame(data)

    # ========== Submitter Management Methods (Issue #1023) ==========

    def set_submitter(
        self,
        proposal_id: int,
        submitter: str,
        submitter_type: SubmitterType,
        submitter_politician_id: int | None = None,
        submitter_parliamentary_group_id: int | None = None,
    ) -> SetSubmitterOutputDTO:
        """議案の提出者情報を設定する.

        Args:
            proposal_id: 議案ID
            submitter: 生の提出者文字列
            submitter_type: 提出者種別
            submitter_politician_id: 議員提出の場合のPolitician ID
            submitter_parliamentary_group_id: 会派提出の場合のParliamentaryGroup ID

        Returns:
            設定結果DTO
        """
        return self._run_async(
            self._set_submitter_async(
                proposal_id,
                submitter,
                submitter_type,
                submitter_politician_id,
                submitter_parliamentary_group_id,
            )
        )

    async def _set_submitter_async(
        self,
        proposal_id: int,
        submitter: str,
        submitter_type: SubmitterType,
        submitter_politician_id: int | None = None,
        submitter_parliamentary_group_id: int | None = None,
    ) -> SetSubmitterOutputDTO:
        """議案の提出者情報を設定する（非同期実装）."""
        return await self.manage_submitter_usecase.set_submitter(
            proposal_id=proposal_id,
            submitter=submitter,
            submitter_type=submitter_type,
            submitter_politician_id=submitter_politician_id,
            submitter_parliamentary_group_id=submitter_parliamentary_group_id,
        )

    def clear_submitter(self, proposal_id: int) -> ClearSubmitterOutputDTO:
        """議案の提出者情報をクリアする.

        Args:
            proposal_id: 議案ID

        Returns:
            クリア結果DTO
        """
        return self._run_async(self._clear_submitter_async(proposal_id))

    async def _clear_submitter_async(self, proposal_id: int) -> ClearSubmitterOutputDTO:
        """議案の提出者情報をクリアする（非同期実装）."""
        return await self.manage_submitter_usecase.clear_submitter(proposal_id)

    def get_submitter_candidates(self, conference_id: int) -> SubmitterCandidatesDTO:
        """会議体に所属する議員/会派の候補一覧を取得する.

        Args:
            conference_id: 会議体ID

        Returns:
            提出者候補一覧DTO
        """
        return self._run_async(self._get_submitter_candidates_async(conference_id))

    async def _get_submitter_candidates_async(
        self, conference_id: int
    ) -> SubmitterCandidatesDTO:
        """会議体に所属する議員/会派の候補一覧を取得する（非同期実装）."""
        return await self.manage_submitter_usecase.get_submitter_candidates(
            conference_id
        )

    def get_conference_id_for_proposal(self, proposal_id: int) -> int | None:
        """議案に関連する会議体IDを取得する.

        Args:
            proposal_id: 議案ID

        Returns:
            会議体ID（取得できない場合はNone）
        """
        return self._run_async(self._get_conference_id_for_proposal_async(proposal_id))

    async def _get_conference_id_for_proposal_async(
        self, proposal_id: int
    ) -> int | None:
        """議案に関連する会議体IDを取得する（非同期実装）."""
        proposal = await self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        if not proposal:
            return None

        if proposal.conference_id:
            return proposal.conference_id

        if proposal.meeting_id:
            meeting = await self.meeting_repository.get_by_id(proposal.meeting_id)  # type: ignore[attr-defined]
            if meeting:
                return meeting.conference_id

        return None

    # ========== 個人投票展開メソッド (Issue #1010) ==========

    def preview_group_judges_expansion(
        self,
        proposal_id: int,
        group_judge_ids: list[int],
    ) -> ExpandGroupJudgesPreviewDTO:
        """会派賛否の個人投票展開をプレビューする.

        Args:
            proposal_id: 議案ID
            group_judge_ids: プレビュー対象の会派賛否IDリスト

        Returns:
            プレビュー結果DTO
        """
        return self._run_async(
            self._preview_group_judges_expansion_async(proposal_id, group_judge_ids)
        )

    async def _preview_group_judges_expansion_async(
        self,
        proposal_id: int,
        group_judge_ids: list[int],
    ) -> ExpandGroupJudgesPreviewDTO:
        """会派賛否の個人投票展開をプレビューする（非同期実装）."""
        result = ExpandGroupJudgesPreviewDTO(success=True)

        # 議案から投票日を特定
        proposal = await self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        if not proposal:
            result.success = False
            result.errors.append(f"議案ID {proposal_id} が見つかりません")
            return result

        meeting_date = None
        if proposal.meeting_id:
            meeting = await self.meeting_repository.get_by_id(proposal.meeting_id)  # type: ignore[attr-defined]
            if meeting and meeting.date:
                meeting_date = meeting.date

        # 会派賛否一覧を取得
        all_judges_dto = (
            await self.manage_parliamentary_group_judges_usecase.list_by_proposal(
                proposal_id
            )
        )
        all_judges = cast(
            list[ProposalParliamentaryGroupJudgeDTO], all_judges_dto.judges
        )

        # 対象の会派賛否をフィルタ
        target_judges = [j for j in all_judges if j.id in group_judge_ids]

        if not target_judges:
            result.success = False
            result.errors.append("選択された会派賛否が見つかりません")
            return result

        # 既存の個人投票データを一括取得
        existing_judges = await self.judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        existing_politician_ids = {j.politician_id for j in existing_judges}

        for judge in target_judges:
            if not judge.is_parliamentary_group_judge():
                continue

            item = GroupJudgePreviewItem(
                group_judge_id=judge.id,
                proposal_id=proposal_id,
                judgment=judge.judgment,
                parliamentary_group_names=judge.parliamentary_group_names or [],
            )

            if meeting_date is None:
                item.errors.append(
                    "投票日が特定できません（meeting_idまたはdateがnull）"
                )
                result.items.append(item)
                continue

            # 各会派のメンバーを取得
            all_politician_ids: set[int] = set()
            for group_id in judge.parliamentary_group_ids:
                members = await self.membership_repository.get_active_by_group(  # type: ignore[attr-defined]
                    group_id, as_of_date=meeting_date
                )
                for m in members:
                    all_politician_ids.add(m.politician_id)

            # 政治家名を一括取得
            politician_name_map: dict[int, str] = {}
            if all_politician_ids:
                politicians = await self.politician_repository.get_by_ids(  # type: ignore[attr-defined]
                    list(all_politician_ids)
                )
                politician_name_map = {
                    p.id: p.name for p in politicians if p.id is not None
                }

            # メンバーリストを構築
            for pid in sorted(all_politician_ids):
                has_existing = pid in existing_politician_ids
                item.members.append(
                    GroupJudgePreviewMember(
                        politician_id=pid,
                        politician_name=politician_name_map.get(pid, f"ID:{pid}"),
                        has_existing_vote=has_existing,
                    )
                )
                if has_existing:
                    item.existing_vote_count += 1

            result.items.append(item)
            result.total_members += len(item.members)
            result.total_existing_votes += item.existing_vote_count

        return result

    def expand_group_judges_to_individual(
        self,
        proposal_id: int | None = None,
        group_judge_ids: list[int] | None = None,
        force_overwrite: bool = False,
    ) -> ExpandGroupJudgesResultDTO:
        """会派賛否を個人投票データに展開する.

        Args:
            proposal_id: 議案ID（全会派賛否を展開する場合）
            group_judge_ids: 展開対象の会派賛否IDリスト（個別指定の場合）
            force_overwrite: 既存データを上書きするかどうか

        Returns:
            展開結果DTO
        """
        return self._run_async(
            self._expand_group_judges_to_individual_async(
                proposal_id, group_judge_ids, force_overwrite
            )
        )

    async def _expand_group_judges_to_individual_async(
        self,
        proposal_id: int | None = None,
        group_judge_ids: list[int] | None = None,
        force_overwrite: bool = False,
    ) -> ExpandGroupJudgesResultDTO:
        """会派賛否を個人投票データに展開する（非同期実装）."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        expand_usecase = self.container.use_cases.expand_group_judges_usecase()

        # group_judge_idsが指定されている場合、各IDについて個別に実行
        if group_judge_ids:
            combined_result = ExpandGroupJudgesResultDTO(success=True)
            for gj_id in group_judge_ids:
                request = ExpandGroupJudgesRequestDTO(
                    group_judge_id=gj_id,
                    force_overwrite=force_overwrite,
                )
                partial = await expand_usecase.execute(request)
                combined_result.total_group_judges_processed += (
                    partial.total_group_judges_processed
                )
                combined_result.total_members_found += partial.total_members_found
                combined_result.total_judges_created += partial.total_judges_created
                combined_result.total_judges_skipped += partial.total_judges_skipped
                combined_result.total_judges_overwritten += (
                    partial.total_judges_overwritten
                )
                combined_result.group_summaries.extend(partial.group_summaries)
                combined_result.errors.extend(partial.errors)
                combined_result.skipped_no_meeting_date += (
                    partial.skipped_no_meeting_date
                )
                if not partial.success:
                    combined_result.success = False
            return combined_result

        # proposal_idが指定されている場合
        request = ExpandGroupJudgesRequestDTO(
            proposal_id=proposal_id,
            force_overwrite=force_overwrite,
        )
        return await expand_usecase.execute(request)
