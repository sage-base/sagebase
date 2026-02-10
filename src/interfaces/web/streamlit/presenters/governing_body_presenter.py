"""Presenter for governing body management."""

from typing import Any

import pandas as pd

from src.application.usecases.manage_governing_bodies_usecase import (
    CreateGoverningBodyInputDto,
    DeleteGoverningBodyInputDto,
    GoverningBodyListInputDto,
    UpdateGoverningBodyInputDto,
)
from src.common.logging import get_logger
from src.domain.entities import GoverningBody
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class GoverningBodyPresenter(BasePresenter[list[GoverningBody]]):
    """Presenter for governing body management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        # DIコンテナ経由でユースケースを取得
        self.use_case = self.container.use_cases.manage_governing_bodies_usecase()
        self.session = SessionManager()
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(__name__)

    def _get_or_create_form_state(self) -> dict[str, Any]:
        """Get or create form state in session."""
        default_state = {
            "editing_mode": None,
            "editing_id": None,
            "type_filter": "すべて",
            "conference_filter": "すべて",
        }
        return self.session.get_or_create("governing_body_form_state", default_state)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("governing_body_form_state", self.form_state)

    def load_data(self) -> list[GoverningBody]:
        """Load all governing bodies."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[GoverningBody]:
        """Load all governing bodies (async implementation)."""
        try:
            result = await self.use_case.list_governing_bodies(
                GoverningBodyListInputDto()
            )
            return result.governing_bodies
        except Exception as e:
            self.logger.error(f"Failed to load governing bodies: {e}")
            return []

    def load_governing_bodies_with_filters(
        self, type_filter: str | None = None, conference_filter: str | None = None
    ) -> tuple[list[GoverningBody], Any]:
        """Load governing bodies with filters and statistics."""
        return self._run_async(
            self._load_governing_bodies_with_filters_async(
                type_filter, conference_filter
            )
        )

    async def _load_governing_bodies_with_filters_async(
        self, type_filter: str | None = None, conference_filter: str | None = None
    ) -> tuple[list[GoverningBody], Any]:
        """Load governing bodies with filters and statistics (async implementation)."""
        try:
            result = await self.use_case.list_governing_bodies(
                GoverningBodyListInputDto(
                    type_filter=type_filter, conference_filter=conference_filter
                )
            )
            return result.governing_bodies, result.statistics
        except Exception as e:
            self.logger.error(f"Failed to load governing bodies with filters: {e}")
            return [], None

    def get_type_options(self) -> list[str]:
        """Get available type options."""
        try:
            return self.use_case.get_type_options()
        except Exception as e:
            self.logger.error(f"Failed to get type options: {e}")
            return []

    def create(
        self,
        name: str,
        type: str,
        organization_code: str | None = None,
        organization_type: str | None = None,
        prefecture: str | None = None,
    ) -> tuple[bool, str | None]:
        """Create a new governing body."""
        return self._run_async(
            self._create_async(
                name, type, organization_code, organization_type, prefecture
            )
        )

    async def _create_async(
        self,
        name: str,
        type: str,
        organization_code: str | None = None,
        organization_type: str | None = None,
        prefecture: str | None = None,
    ) -> tuple[bool, str | None]:
        """Create a new governing body (async implementation)."""
        try:
            result = await self.use_case.create_governing_body(
                CreateGoverningBodyInputDto(
                    name=name,
                    type=type,
                    organization_code=organization_code,
                    organization_type=organization_type,
                    prefecture=prefecture,
                )
            )
            if result.success:
                return True, str(result.governing_body_id)
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to create governing body: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def update(
        self,
        id: int,
        name: str,
        type: str,
        organization_code: str | None = None,
        organization_type: str | None = None,
        prefecture: str | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing governing body."""
        return self._run_async(
            self._update_async(
                id, name, type, organization_code, organization_type, prefecture
            )
        )

    async def _update_async(
        self,
        id: int,
        name: str,
        type: str,
        organization_code: str | None = None,
        organization_type: str | None = None,
        prefecture: str | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing governing body (async implementation)."""
        try:
            result = await self.use_case.update_governing_body(
                UpdateGoverningBodyInputDto(
                    id=id,
                    name=name,
                    type=type,
                    organization_code=organization_code,
                    organization_type=organization_type,
                    prefecture=prefecture,
                )
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to update governing body: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """Delete a governing body."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        """Delete a governing body (async implementation)."""
        try:
            result = await self.use_case.delete_governing_body(
                DeleteGoverningBodyInputDto(id=id)
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to delete governing body: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for governing bodies."""
        return self._run_async(self._generate_seed_file_async())

    async def _generate_seed_file_async(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for governing bodies (async implementation)."""
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
        self, governing_bodies: list[GoverningBody]
    ) -> pd.DataFrame | None:
        """Convert governing bodies to DataFrame."""
        if not governing_bodies:
            return None

        df_data = []
        for gb in governing_bodies:
            df_data.append(
                {
                    "ID": gb.id,
                    "名称": gb.name,
                    "種別": gb.type,
                    "都道府県": gb.prefecture or "",
                    "会議体数": getattr(gb, "conference_count", 0),
                    "組織コード": gb.organization_code or "",
                    "組織タイプ": gb.organization_type or "",
                }
            )
        return pd.DataFrame(df_data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "list":
            return self.load_governing_bodies_with_filters(
                kwargs.get("type_filter"), kwargs.get("conference_filter")
            )
        elif action == "create":
            return self.create(
                kwargs.get("name", ""),
                kwargs.get("type", ""),
                kwargs.get("organization_code"),
                kwargs.get("organization_type"),
                kwargs.get("prefecture"),
            )
        elif action == "update":
            return self.update(
                kwargs.get("id", 0),
                kwargs.get("name", ""),
                kwargs.get("type", ""),
                kwargs.get("organization_code"),
                kwargs.get("organization_type"),
                kwargs.get("prefecture"),
            )
        elif action == "delete":
            return self.delete(kwargs.get("id", 0))
        elif action == "generate_seed":
            return self.generate_seed_file()
        else:
            raise ValueError(f"Unknown action: {action}")

    def set_editing_mode(self, mode: str | None, id: int | None = None) -> None:
        """Set editing mode."""
        self.form_state["editing_mode"] = mode
        self.form_state["editing_id"] = id
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.set_editing_mode(None, None)

    def is_editing(self, id: int) -> bool:
        """Check if currently editing a specific governing body."""
        return (
            self.form_state.get("editing_mode") == "edit"
            and self.form_state.get("editing_id") == id
        )
