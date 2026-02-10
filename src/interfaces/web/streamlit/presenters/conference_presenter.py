"""Presenter for conference management."""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.application.dtos.election_dto import (
    ElectionOutputItem,
    ListElectionsInputDto,
)
from src.application.usecases.manage_conferences_usecase import (
    ConferenceListInputDto,
    CreateConferenceInputDto,
    DeleteConferenceInputDto,
    ManageConferencesUseCase,
    UpdateConferenceInputDto,
)
from src.application.usecases.manage_elections_usecase import ManageElectionsUseCase
from src.common.logging import get_logger
from src.domain.entities import Conference
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


logger = get_logger(__name__)


@dataclass
class ConferenceFormData:
    """Form data for conference."""

    name: str = ""
    governing_body_id: int | None = None
    term: str | None = None
    election_id: int | None = None


class ConferencePresenter:
    """Presenter for conference management."""

    def __init__(
        self,
        use_case: ManageConferencesUseCase,
        elections_use_case: ManageElectionsUseCase | None = None,
    ):
        """Initialize the presenter."""
        self.use_case = use_case
        self.elections_use_case = elections_use_case
        self.session = SessionManager()

    async def load_conferences(
        self,
        governing_body_id: int | None = None,
    ) -> pd.DataFrame:
        """Load conferences list."""
        input_dto = ConferenceListInputDto(
            governing_body_id=governing_body_id,
        )
        output_dto = await self.use_case.list_conferences(input_dto)

        # Convert to DataFrame
        if output_dto.conferences:
            df = self._conferences_to_dataframe(output_dto.conferences)
        else:
            df = pd.DataFrame()

        return df

    def _conferences_to_dataframe(self, conferences: list[Conference]) -> pd.DataFrame:
        """Convert conferences to DataFrame."""
        data = []
        for conf in conferences:
            data.append(
                {
                    "ID": conf.id,
                    "会議体名": conf.name,
                    "期/会期/年度": conf.term or "",
                    "開催主体ID": conf.governing_body_id or "",
                }
            )
        return pd.DataFrame(data)

    def get_form_data(self, prefix: str = "new") -> ConferenceFormData:
        """Get form data from session."""
        key = f"{prefix}_conference_form"
        if key not in st.session_state:
            st.session_state[key] = ConferenceFormData()
        return st.session_state[key]

    def update_form_data(
        self, form_data: ConferenceFormData, prefix: str = "new"
    ) -> None:
        """Update form data in session."""
        key = f"{prefix}_conference_form"
        st.session_state[key] = form_data

    def clear_form_data(self, prefix: str = "new") -> None:
        """Clear form data from session."""
        key = f"{prefix}_conference_form"
        if key in st.session_state:
            del st.session_state[key]

    async def create_conference(
        self, form_data: ConferenceFormData
    ) -> tuple[bool, str | None]:
        """Create new conference."""
        input_dto = CreateConferenceInputDto(
            name=form_data.name,
            governing_body_id=form_data.governing_body_id,
            term=form_data.term,
            election_id=form_data.election_id,
        )
        output_dto = await self.use_case.create_conference(input_dto)
        return output_dto.success, output_dto.error_message

    async def update_conference(
        self, conference_id: int, form_data: ConferenceFormData
    ) -> tuple[bool, str | None]:
        """Update conference."""
        input_dto = UpdateConferenceInputDto(
            id=conference_id,
            name=form_data.name,
            governing_body_id=form_data.governing_body_id,
            term=form_data.term,
            election_id=form_data.election_id,
        )
        output_dto = await self.use_case.update_conference(input_dto)
        return output_dto.success, output_dto.error_message

    async def delete_conference(self, conference_id: int) -> tuple[bool, str | None]:
        """Delete conference."""
        input_dto = DeleteConferenceInputDto(id=conference_id)
        output_dto = await self.use_case.delete_conference(input_dto)
        return output_dto.success, output_dto.error_message

    async def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file."""
        output_dto = await self.use_case.generate_seed_file()
        return output_dto.success, output_dto.file_path, output_dto.error_message

    def get_elections_for_governing_body(
        self, governing_body_id: int
    ) -> list[ElectionOutputItem]:
        """開催主体に紐づく選挙一覧を取得する."""
        if self.elections_use_case is None:
            return []
        try:
            import asyncio

            import nest_asyncio

            nest_asyncio.apply()

            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            input_dto = ListElectionsInputDto(governing_body_id=governing_body_id)
            coro = self.elections_use_case.list_elections(input_dto)
            output_dto = loop.run_until_complete(coro)
            return output_dto.elections
        except Exception as e:
            logger.error(
                f"Failed to load elections for governing body {governing_body_id}: {e}"
            )
            return []

    def load_conference_for_edit(self, conference: Conference) -> ConferenceFormData:
        """Load conference data for editing."""
        return ConferenceFormData(
            name=conference.name,
            governing_body_id=conference.governing_body_id,
            term=conference.term,
            election_id=conference.election_id,
        )
