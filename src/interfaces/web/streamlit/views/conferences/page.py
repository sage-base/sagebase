"""Main page for conference management.

会議体管理のメインページとタブ構成を定義します。
"""

from typing import cast

import streamlit as st

from .tabs.edit_delete_tab import render_edit_delete_form
from .tabs.extracted_members_tab import render_extracted_members
from .tabs.list_tab import render_conferences_list
from .tabs.new_tab import render_new_conference_form
from .tabs.seed_generator_tab import render_seed_generator

from src.application.usecases.manage_conference_members_usecase import (
    ManageConferenceMembersUseCase,
)
from src.application.usecases.manage_conferences_usecase import (
    ManageConferencesUseCase,
)
from src.application.usecases.mark_entity_as_verified_usecase import (
    MarkEntityAsVerifiedUseCase,
)
from src.domain.repositories import ConferenceRepository, GoverningBodyRepository
from src.domain.services.conference_domain_service import ConferenceDomainService
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.web_scraper_service import PlaywrightScraperService
from src.infrastructure.persistence.conference_member_repository_impl import (
    ConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)


@st.cache_resource
def _create_scraper_service() -> PlaywrightScraperService:
    """PlaywrightScraperServiceのキャッシュされたインスタンスを返す."""
    return PlaywrightScraperService()


@st.cache_resource
def _create_llm_service() -> GeminiLLMService:
    """GeminiLLMServiceのキャッシュされたインスタンスを返す."""
    return GeminiLLMService()


def render_conferences_page() -> None:
    """会議体管理のメインページをレンダリングする.

    5つのタブ（会議体一覧、新規登録、編集・削除、SEED生成、抽出結果確認）を提供します。
    """
    st.title("会議体管理")

    # Initialize repositories
    conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
    governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    extracted_member_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
    conference_member_repo = RepositoryAdapter(ConferenceMemberRepositoryImpl)

    # Initialize use case and presenter
    # Type: ignore - RepositoryAdapter duck-types as repository protocol
    use_case = ManageConferencesUseCase(
        conference_repo,  # type: ignore[arg-type]
        meeting_repo,  # type: ignore[arg-type]
    )
    presenter = ConferencePresenter(use_case)

    # 会議体メンバー管理UseCase初期化
    conference_service = ConferenceDomainService()
    manage_members_usecase = ManageConferenceMembersUseCase(
        conference_repository=conference_repo,  # type: ignore[arg-type]
        politician_repository=politician_repo,  # type: ignore[arg-type]
        conference_domain_service=conference_service,
        extracted_member_repository=extracted_member_repo,  # type: ignore[arg-type]
        conference_member_repository=conference_member_repo,  # type: ignore[arg-type]
        web_scraper_service=_create_scraper_service(),
        llm_service=_create_llm_service(),
    )

    # 検証UseCase初期化
    verify_use_case = MarkEntityAsVerifiedUseCase(
        conference_member_repository=extracted_member_repo,  # type: ignore[arg-type]
    )

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["会議体一覧", "新規登録", "編集・削除", "SEED生成", "抽出結果確認"]
    )

    with tab1:
        render_conferences_list(
            presenter, cast(GoverningBodyRepository, governing_body_repo)
        )

    with tab2:
        render_new_conference_form(
            presenter, cast(GoverningBodyRepository, governing_body_repo)
        )

    with tab3:
        render_edit_delete_form(
            presenter,
            cast(ConferenceRepository, conference_repo),
            cast(GoverningBodyRepository, governing_body_repo),
        )

    with tab4:
        render_seed_generator(presenter)

    with tab5:
        render_extracted_members(
            extracted_member_repo,
            conference_repo,
            manage_members_usecase,
            verify_use_case,
            conference_member_repo,
        )
