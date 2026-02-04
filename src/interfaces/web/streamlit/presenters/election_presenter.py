"""Presenter for election management."""

from datetime import date
from typing import Any

import pandas as pd

from src.common.logging import get_logger
from src.domain.entities.election import Election
from src.domain.entities.governing_body import GoverningBody
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.election_repository_impl import (
    ElectionRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ElectionPresenter(BasePresenter[list[Election]]):
    """Presenter for election management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        self.election_repo = RepositoryAdapter(ElectionRepositoryImpl)
        self.governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
        self.session = SessionManager()
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(__name__)

    def _get_or_create_form_state(self) -> dict[str, Any]:
        """Get or create form state in session."""
        default_state = {
            "editing_mode": None,
            "editing_id": None,
            "selected_governing_body_id": None,
        }
        return self.session.get_or_create("election_form_state", default_state)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("election_form_state", self.form_state)

    def load_data(self) -> list[Election]:
        """Load all elections."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[Election]:
        """Load all elections (async implementation)."""
        try:
            return await self.election_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to load elections: {e}")
            return []

    def load_elections_by_governing_body(
        self, governing_body_id: int
    ) -> list[Election]:
        """Load elections for a specific governing body."""
        return self._run_async(
            self._load_elections_by_governing_body_async(governing_body_id)
        )

    async def _load_elections_by_governing_body_async(
        self, governing_body_id: int
    ) -> list[Election]:
        """Load elections for a specific governing body (async implementation)."""
        try:
            return await self.election_repo.get_by_governing_body(governing_body_id)
        except Exception as e:
            self.logger.error(
                f"Failed to load elections for governing body {governing_body_id}: {e}"
            )
            return []

    def load_governing_bodies(self) -> list[GoverningBody]:
        """Load all governing bodies."""
        return self._run_async(self._load_governing_bodies_async())

    async def _load_governing_bodies_async(self) -> list[GoverningBody]:
        """Load all governing bodies (async implementation)."""
        try:
            return await self.governing_body_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to load governing bodies: {e}")
            return []

    def get_election_type_options(self) -> list[str]:
        """Get available election type options."""
        return ["統一地方選挙", "通常選挙", "補欠選挙", "再選挙", "その他"]

    def create(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """Create a new election."""
        return self._run_async(
            self._create_async(
                governing_body_id, term_number, election_date, election_type
            )
        )

    async def _create_async(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """Create a new election (async implementation)."""
        try:
            election = Election(
                governing_body_id=governing_body_id,
                term_number=term_number,
                election_date=election_date,
                election_type=election_type,
            )
            created = await self.election_repo.create(election)
            return True, str(created.id)
        except Exception as e:
            error_msg = f"Failed to create election: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def update(
        self,
        id: int,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing election."""
        return self._run_async(
            self._update_async(
                id, governing_body_id, term_number, election_date, election_type
            )
        )

    async def _update_async(
        self,
        id: int,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing election (async implementation)."""
        try:
            election = Election(
                id=id,
                governing_body_id=governing_body_id,
                term_number=term_number,
                election_date=election_date,
                election_type=election_type,
            )
            await self.election_repo.update(election)
            return True, None
        except Exception as e:
            error_msg = f"Failed to update election: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """Delete an election."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        """Delete an election (async implementation)."""
        try:
            result = await self.election_repo.delete(id)
            if result:
                return True, None
            else:
                return (
                    False,
                    "削除できませんでした（関連する会議体が存在する可能性があります）",
                )
        except Exception as e:
            error_msg = f"Failed to delete election: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def to_dataframe(self, elections: list[Election]) -> pd.DataFrame | None:
        """Convert elections to DataFrame."""
        if not elections:
            return None

        df_data = []
        for election in elections:
            df_data.append(
                {
                    "ID": election.id,
                    "期番号": f"第{election.term_number}期",
                    "選挙日": election.election_date,
                    "選挙種別": election.election_type or "",
                }
            )
        return pd.DataFrame(df_data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "list":
            return self.load_data()
        elif action == "list_by_governing_body":
            return self.load_elections_by_governing_body(
                kwargs.get("governing_body_id", 0)
            )
        elif action == "create":
            return self.create(
                kwargs.get("governing_body_id", 0),
                kwargs.get("term_number", 0),
                kwargs.get("election_date", date.today()),
                kwargs.get("election_type"),
            )
        elif action == "update":
            return self.update(
                kwargs.get("id", 0),
                kwargs.get("governing_body_id", 0),
                kwargs.get("term_number", 0),
                kwargs.get("election_date", date.today()),
                kwargs.get("election_type"),
            )
        elif action == "delete":
            return self.delete(kwargs.get("id", 0))
        else:
            raise ValueError(f"Unknown action: {action}")

    def set_selected_governing_body(self, governing_body_id: int | None) -> None:
        """Set selected governing body."""
        self.form_state["selected_governing_body_id"] = governing_body_id
        self._save_form_state()

    def get_selected_governing_body(self) -> int | None:
        """Get selected governing body."""
        return self.form_state.get("selected_governing_body_id")
