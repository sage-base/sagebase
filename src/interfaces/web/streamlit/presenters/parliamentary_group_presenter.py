"""Presenter for parliamentary group management."""

from datetime import date
from typing import Any

import pandas as pd

from src.application.usecases.manage_parliamentary_groups_usecase import (
    CreateParliamentaryGroupInputDto,
    DeleteParliamentaryGroupInputDto,
    ExtractMembersInputDto,
    ManageParliamentaryGroupsUseCase,
    ParliamentaryGroupListInputDto,
    UpdateParliamentaryGroupInputDto,
)
from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
)
from src.common.logging import get_logger
from src.domain.entities import ParliamentaryGroup
from src.domain.entities.governing_body import GoverningBody
from src.domain.entities.political_party import PoliticalParty
from src.infrastructure.di.container import Container
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.infrastructure.persistence.async_session_adapter import NoOpSessionAdapter
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ParliamentaryGroupPresenter(BasePresenter[list[ParliamentaryGroup]]):
    """Presenter for parliamentary group management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        # Initialize repositories and use case
        self.parliamentary_group_repo = RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl
        )
        self.governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
        self.political_party_repo = RepositoryAdapter(PoliticalPartyRepositoryImpl)
        self.membership_repo = RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl
        )
        self.extracted_member_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )
        self.llm_service = GeminiLLMService()

        # Initialize member extractor using Factory
        self.member_extractor = ParliamentaryGroupMemberExtractorFactory.create()

        # 抽出ログ記録用のUseCaseを作成
        # RepositoryAdapterは各操作で自動コミットするため、NoOpSessionAdapterを使用
        self.extraction_log_repo = RepositoryAdapter(ExtractionLogRepositoryImpl)
        session_adapter = NoOpSessionAdapter()

        self.update_usecase = (
            UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase(
                extracted_parliamentary_group_member_repo=self.extracted_member_repo,  # type: ignore[arg-type]
                extraction_log_repo=self.extraction_log_repo,  # type: ignore[arg-type]
                session_adapter=session_adapter,
            )
        )

        # Initialize use case with required dependencies
        # Type: ignore - RepositoryAdapter duck-types as repository protocol
        self.use_case = ManageParliamentaryGroupsUseCase(
            parliamentary_group_repository=self.parliamentary_group_repo,  # type: ignore[arg-type]
            member_extractor=self.member_extractor,  # Injected extractor
            extracted_member_repository=self.extracted_member_repo,  # type: ignore[arg-type]
            update_usecase=self.update_usecase,  # 抽出ログ記録用UseCase
            membership_repository=self.membership_repo,  # type: ignore[arg-type]
        )
        self.session = SessionManager()
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(__name__)

    def _get_or_create_form_state(self) -> dict[str, Any]:
        """Get or create form state in session."""
        default_state = {
            "editing_mode": None,
            "editing_id": None,
            "governing_body_filter": "すべて",
            "created_parliamentary_groups": [],
        }
        return self.session.get_or_create(
            "parliamentary_group_form_state", default_state
        )

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("parliamentary_group_form_state", self.form_state)

    def load_data(self) -> list[ParliamentaryGroup]:
        """Load all parliamentary groups."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[ParliamentaryGroup]:
        """Load all parliamentary groups (async implementation)."""
        try:
            result = await self.use_case.list_parliamentary_groups(
                ParliamentaryGroupListInputDto()
            )
            return result.parliamentary_groups
        except Exception as e:
            self.logger.error(f"Failed to load parliamentary groups: {e}")
            return []

    def load_parliamentary_groups_with_filters(
        self, governing_body_id: int | None = None, active_only: bool = False
    ) -> list[ParliamentaryGroup]:
        """Load parliamentary groups with filters."""
        return self._run_async(
            self._load_parliamentary_groups_with_filters_async(
                governing_body_id, active_only
            )
        )

    async def _load_parliamentary_groups_with_filters_async(
        self, governing_body_id: int | None = None, active_only: bool = False
    ) -> list[ParliamentaryGroup]:
        """Load parliamentary groups with filters (async implementation)."""
        try:
            result = await self.use_case.list_parliamentary_groups(
                ParliamentaryGroupListInputDto(
                    governing_body_id=governing_body_id, active_only=active_only
                )
            )
            return result.parliamentary_groups
        except Exception as e:
            self.logger.error(f"Failed to load parliamentary groups with filters: {e}")
            return []

    def get_all_governing_bodies(self) -> list[GoverningBody]:
        """Get all governing bodies."""
        return self._run_async(self._get_all_governing_bodies_async())

    async def _get_all_governing_bodies_async(self) -> list[GoverningBody]:
        """Get all governing bodies (async implementation)."""
        try:
            return await self.governing_body_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get governing bodies: {e}")
            return []

    def get_all_political_parties(self) -> list[PoliticalParty]:
        """Get all political parties."""
        return self._run_async(self._get_all_political_parties_async())

    async def _get_all_political_parties_async(self) -> list[PoliticalParty]:
        """Get all political parties (async implementation)."""
        try:
            return await self.political_party_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get political parties: {e}")
            return []

    def create(
        self,
        name: str,
        governing_body_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        political_party_id: int | None = None,
        chamber: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, ParliamentaryGroup | None, str | None]:
        """Create a new parliamentary group."""
        return self._run_async(
            self._create_async(
                name,
                governing_body_id,
                url,
                description,
                is_active,
                political_party_id,
                chamber,
                start_date,
                end_date,
            )
        )

    async def _create_async(
        self,
        name: str,
        governing_body_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        political_party_id: int | None = None,
        chamber: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, ParliamentaryGroup | None, str | None]:
        """Create a new parliamentary group (async implementation)."""
        try:
            result = await self.use_case.create_parliamentary_group(
                CreateParliamentaryGroupInputDto(
                    name=name,
                    governing_body_id=governing_body_id,
                    url=url,
                    description=description,
                    is_active=is_active,
                    political_party_id=political_party_id,
                    chamber=chamber,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            if result.success:
                return True, result.parliamentary_group, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to create parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def update(
        self,
        id: int,
        name: str,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        political_party_id: int | None = None,
        chamber: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing parliamentary group."""
        return self._run_async(
            self._update_async(
                id,
                name,
                url,
                description,
                is_active,
                political_party_id,
                chamber,
                start_date,
                end_date,
            )
        )

    async def _update_async(
        self,
        id: int,
        name: str,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        political_party_id: int | None = None,
        chamber: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing parliamentary group (async implementation)."""
        try:
            result = await self.use_case.update_parliamentary_group(
                UpdateParliamentaryGroupInputDto(
                    id=id,
                    name=name,
                    url=url,
                    description=description,
                    is_active=is_active,
                    political_party_id=political_party_id,
                    chamber=chamber,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to update parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """Delete a parliamentary group."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        """Delete a parliamentary group (async implementation)."""
        try:
            result = await self.use_case.delete_parliamentary_group(
                DeleteParliamentaryGroupInputDto(id=id)
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to delete parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def extract_members(
        self,
        parliamentary_group_id: int,
        url: str,
        confidence_threshold: float = 0.7,
        start_date: date | None = None,
        dry_run: bool = True,
    ) -> tuple[bool, Any, str | None]:
        """Extract members from parliamentary group URL."""
        return self._run_async(
            self._extract_members_async(
                parliamentary_group_id, url, confidence_threshold, start_date, dry_run
            )
        )

    async def _extract_members_async(
        self,
        parliamentary_group_id: int,
        url: str,
        confidence_threshold: float = 0.7,
        start_date: date | None = None,
        dry_run: bool = True,
    ) -> tuple[bool, Any, str | None]:
        """Extract members from parliamentary group URL (async implementation)."""
        try:
            result = await self.use_case.extract_members(
                ExtractMembersInputDto(
                    parliamentary_group_id=parliamentary_group_id,
                    url=url,
                    confidence_threshold=confidence_threshold,
                    start_date=start_date,
                    dry_run=dry_run,
                )
            )
            if result.success:
                return True, result, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to extract members: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def extract_members_with_agent(
        self,
        parliamentary_group_name: str,
        url: str,
    ) -> tuple[bool, Any, str | None]:
        """LangGraphエージェントを使用してメンバーを抽出 (Issue #905)

        Args:
            parliamentary_group_name: 議員団名
            url: 議員団メンバー一覧ページのURL

        Returns:
            (成功フラグ, 抽出結果DTO, エラーメッセージ)

        Note:
            DB保存は行いません。抽出のみを行います。
        """
        return self._run_async(
            self._extract_members_with_agent_async(parliamentary_group_name, url)
        )

    async def _extract_members_with_agent_async(
        self,
        parliamentary_group_name: str,
        url: str,
    ) -> tuple[bool, Any, str | None]:
        """LangGraphエージェントを使用してメンバーを抽出 (async)"""
        try:
            from src.infrastructure.external.parliamentary_group_member_extractor.extractor import (  # noqa: E501
                ParliamentaryGroupMemberExtractor,
            )

            extractor = ParliamentaryGroupMemberExtractor()
            result = await extractor.extract_members_from_url(
                url=url,
                parliamentary_group_name=parliamentary_group_name,
            )

            if not result.success:
                return False, None, result.error_message

            return True, result, None
        except Exception as e:
            error_msg = f"Failed to extract members with agent: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for parliamentary groups."""
        return self._run_async(self._generate_seed_file_async())

    async def _generate_seed_file_async(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for parliamentary groups (async implementation)."""
        try:
            result = await self.use_case.generate_seed_file()
            if result.success:
                return True, result.seed_content, result.file_path
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to generate seed file: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def to_dataframe(
        self,
        parliamentary_groups: list[ParliamentaryGroup],
        governing_bodies: list[GoverningBody],
    ) -> pd.DataFrame | None:
        """Convert parliamentary groups to DataFrame."""
        if not parliamentary_groups:
            return None

        political_parties = self.get_all_political_parties()
        party_map = {p.id: p.name for p in political_parties}

        df_data = []
        for group in parliamentary_groups:
            # Find governing body name
            gb = next(
                (g for g in governing_bodies if g.id == group.governing_body_id), None
            )
            gb_name = f"{gb.name}" if gb else "不明"

            party_name = (
                party_map.get(group.political_party_id, "未設定")
                if group.political_party_id
                else "未設定"
            )

            df_data.append(
                {
                    "ID": group.id,
                    "議員団名": group.name,
                    "院": group.chamber if group.chamber else "-",
                    "開催主体": gb_name,
                    "政党": party_name,
                    "URL": group.url or "未設定",
                    "説明": group.description or "",
                    "状態": "活動中" if group.is_active else "非活動",
                    "開始日": group.start_date,
                    "終了日": group.end_date,
                    "作成日": group.created_at,
                }
            )
        return pd.DataFrame(df_data)

    def get_member_counts(
        self, parliamentary_groups: list[ParliamentaryGroup]
    ) -> pd.DataFrame | None:
        """Get member counts for parliamentary groups."""
        if not parliamentary_groups:
            return None

        member_counts = []
        for group in parliamentary_groups:
            # Get current members for this group
            if group.id:
                try:
                    current_members = self.membership_repo.get_current_members(group.id)
                    member_count = len(current_members)
                except Exception as e:
                    self.logger.error(
                        f"Failed to get member count for group {group.id}: {e}"
                    )
                    member_count = 0
            else:
                member_count = 0

            member_counts.append(
                {
                    "議員団名": group.name,
                    "現在のメンバー数": member_count,
                }
            )
        return pd.DataFrame(member_counts)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "list":
            return self.load_parliamentary_groups_with_filters(
                kwargs.get("governing_body_id"), kwargs.get("active_only", False)
            )
        elif action == "create":
            return self.create(
                kwargs.get("name", ""),
                kwargs.get("governing_body_id", 0),
                kwargs.get("url"),
                kwargs.get("description"),
                kwargs.get("is_active", True),
                kwargs.get("political_party_id"),
                kwargs.get("chamber", ""),
                kwargs.get("start_date"),
                kwargs.get("end_date"),
            )
        elif action == "update":
            return self.update(
                kwargs.get("id", 0),
                kwargs.get("name", ""),
                kwargs.get("url"),
                kwargs.get("description"),
                kwargs.get("is_active", True),
                kwargs.get("political_party_id"),
                kwargs.get("chamber", ""),
                kwargs.get("start_date"),
                kwargs.get("end_date"),
            )
        elif action == "delete":
            return self.delete(kwargs.get("id", 0))
        elif action == "extract_members":
            return self.extract_members(
                kwargs.get("parliamentary_group_id", 0),
                kwargs.get("url", ""),
                kwargs.get("confidence_threshold", 0.7),
                kwargs.get("start_date"),
                kwargs.get("dry_run", True),
            )
        elif action == "generate_seed":
            return self.generate_seed_file()
        else:
            raise ValueError(f"Unknown action: {action}")

    def add_created_group(
        self, group: ParliamentaryGroup, governing_body_name: str
    ) -> None:
        """Add a created group to the session state."""
        created_group = {
            "id": group.id,
            "name": group.name,
            "governing_body_id": group.governing_body_id,
            "governing_body_name": governing_body_name,
            "url": group.url or "",
            "description": group.description or "",
            "is_active": group.is_active,
            "start_date": group.start_date,
            "end_date": group.end_date,
            "created_at": group.created_at,
        }
        self.form_state["created_parliamentary_groups"].append(created_group)
        self._save_form_state()

    def remove_created_group(self, index: int) -> None:
        """Remove a created group from the session state."""
        if 0 <= index < len(self.form_state["created_parliamentary_groups"]):
            self.form_state["created_parliamentary_groups"].pop(index)
            self._save_form_state()

    def get_created_groups(self) -> list[dict[str, Any]]:
        """Get created groups from the session state."""
        return self.form_state.get("created_parliamentary_groups", [])

    def get_extracted_members(self, parliamentary_group_id: int) -> list[Any]:
        """Get extracted members for a parliamentary group from database."""
        try:
            # RepositoryAdapter handles async to sync conversion
            members = self.extracted_member_repo.get_by_parliamentary_group(
                parliamentary_group_id
            )
            return members
        except Exception as e:
            self.logger.error(f"Failed to get extracted members: {e}")
            return []

    def get_extraction_summary(self, parliamentary_group_id: int) -> dict[str, int]:
        """Get extraction summary for a parliamentary group."""
        try:
            # RepositoryAdapter handles async to sync conversion
            summary = self.extracted_member_repo.get_extraction_summary(
                parliamentary_group_id
            )
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get extraction summary: {e}")
            return {
                "total": 0,
                "pending": 0,
                "matched": 0,
                "no_match": 0,
                "needs_review": 0,
            }

    def get_memberships_by_group(self, group_id: int) -> list[dict[str, Any]]:
        """議員団のメンバーシップ一覧を政治家名付きで取得する.

        Args:
            group_id: 議員団ID

        Returns:
            メンバーシップ情報のリスト。各要素は以下のキーを持つ:
            - id: メンバーシップID
            - politician_id: 政治家ID
            - politician_name: 政治家名
            - parliamentary_group_id: 議員団ID
            - role: 役職
            - start_date: 開始日
            - end_date: 終了日
            - is_active: 現在アクティブかどうか
        """
        return self._run_async(self._get_memberships_by_group_async(group_id))

    async def _get_memberships_by_group_async(
        self, group_id: int
    ) -> list[dict[str, Any]]:
        """議員団のメンバーシップ一覧を政治家名付きで取得する（async）."""
        try:
            memberships = await self.membership_repo.get_by_group(group_id)
            result = []

            for membership in memberships:
                # 政治家名を取得
                try:
                    politician = await self.politician_repo.get_by_id(
                        membership.politician_id
                    )
                    politician_name = politician.name if politician else "不明"
                except Exception as e:
                    self.logger.warning(
                        f"政治家情報取得失敗 (ID: {membership.politician_id}): {e}"
                    )
                    politician_name = "不明"

                is_active = membership.end_date is None

                result.append(
                    {
                        "id": membership.id,
                        "politician_id": membership.politician_id,
                        "politician_name": politician_name,
                        "parliamentary_group_id": membership.parliamentary_group_id,
                        "role": membership.role,
                        "start_date": membership.start_date,
                        "end_date": membership.end_date,
                        "is_active": is_active,
                    }
                )

            return result
        except Exception as e:
            self.logger.error(f"Failed to get memberships for group {group_id}: {e}")
            return []

    def get_memberships_for_groups(self, group_ids: list[int]) -> list[dict[str, Any]]:
        """複数の議員団のメンバーシップ一覧を政治家名付きで取得する.

        Args:
            group_ids: 議員団IDのリスト

        Returns:
            メンバーシップ情報のリスト
        """
        return self._run_async(self._get_memberships_for_groups_async(group_ids))

    async def _get_memberships_for_groups_async(
        self, group_ids: list[int]
    ) -> list[dict[str, Any]]:
        """複数の議員団のメンバーシップ一覧を取得する（async）."""
        all_memberships: list[dict[str, Any]] = []
        for group_id in group_ids:
            memberships = await self._get_memberships_by_group_async(group_id)
            all_memberships.extend(memberships)
        return all_memberships
