"""Use case for managing conferences."""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities import Conference
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.meeting_repository import MeetingRepository


logger = get_logger(__name__)


@dataclass
class ConferenceListInputDto:
    """Input DTO for listing conferences."""

    governing_body_id: int | None = None


@dataclass
class ConferenceListOutputDto:
    """Output DTO for listing conferences."""

    conferences: list[Conference]


@dataclass
class CreateConferenceInputDto:
    """Input DTO for creating a conference."""

    name: str
    governing_body_id: int | None = None
    term: str | None = None
    election_id: int | None = None


@dataclass
class CreateConferenceOutputDto:
    """Output DTO for creating a conference."""

    success: bool
    conference_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdateConferenceInputDto:
    """Input DTO for updating a conference."""

    id: int
    name: str
    governing_body_id: int | None = None
    term: str | None = None
    election_id: int | None = None


@dataclass
class UpdateConferenceOutputDto:
    """Output DTO for updating a conference."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteConferenceInputDto:
    """Input DTO for deleting a conference."""

    id: int


@dataclass
class DeleteConferenceOutputDto:
    """Output DTO for deleting a conference."""

    success: bool
    error_message: str | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """Output DTO for generating seed file."""

    success: bool
    seed_content: str | None = None
    file_path: str | None = None
    error_message: str | None = None


class ManageConferencesUseCase:
    """Use case for managing conferences."""

    def __init__(
        self,
        conference_repository: ConferenceRepository,
        meeting_repository: MeetingRepository | None = None,
    ):
        """Initialize the use case.

        Args:
            conference_repository: Repository instance (can be sync or async)
            meeting_repository: Meeting repository for deletion checks (optional)
        """
        self.conference_repository = conference_repository
        self.meeting_repository = meeting_repository

    async def list_conferences(
        self, input_dto: ConferenceListInputDto
    ) -> ConferenceListOutputDto:
        """List conferences with optional filters."""
        try:
            if input_dto.governing_body_id:
                conferences = await self.conference_repository.get_by_governing_body(
                    input_dto.governing_body_id
                )
            else:
                conferences = await self.conference_repository.get_all()

            return ConferenceListOutputDto(
                conferences=conferences,
            )
        except Exception as e:
            logger.error(f"Failed to list conferences: {e}")
            raise

    async def create_conference(
        self, input_dto: CreateConferenceInputDto
    ) -> CreateConferenceOutputDto:
        """Create a new conference."""
        try:
            # Check for duplicates
            if input_dto.governing_body_id is not None:
                existing = (
                    await self.conference_repository.get_by_name_and_governing_body(
                        input_dto.name, input_dto.governing_body_id, input_dto.term
                    )
                )
            else:
                existing = None

            if existing:
                return CreateConferenceOutputDto(
                    success=False,
                    error_message="同じ名前・期の会議体が既に存在します。",
                )

            # Create new conference
            conference = Conference(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                governing_body_id=(
                    input_dto.governing_body_id if input_dto.governing_body_id else 0
                ),
                term=input_dto.term,
                election_id=input_dto.election_id,
            )

            created = await self.conference_repository.create(conference)
            return CreateConferenceOutputDto(success=True, conference_id=created.id)
        except Exception as e:
            logger.error(f"Failed to create conference: {e}")
            return CreateConferenceOutputDto(success=False, error_message=str(e))

    async def update_conference(
        self, input_dto: UpdateConferenceInputDto
    ) -> UpdateConferenceOutputDto:
        """Update an existing conference."""
        try:
            # Get existing conference
            existing = await self.conference_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateConferenceOutputDto(
                    success=False, error_message="会議体が見つかりません。"
                )

            # Update fields
            existing.name = input_dto.name
            if input_dto.governing_body_id is not None:
                existing.governing_body_id = input_dto.governing_body_id
            existing.term = input_dto.term
            existing.election_id = input_dto.election_id
            await self.conference_repository.update(existing)
            return UpdateConferenceOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update conference: {e}")
            return UpdateConferenceOutputDto(success=False, error_message=str(e))

    async def delete_conference(
        self, input_dto: DeleteConferenceInputDto
    ) -> DeleteConferenceOutputDto:
        """Delete a conference."""
        try:
            # Check if conference exists
            existing = await self.conference_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteConferenceOutputDto(
                    success=False, error_message="会議体が見つかりません。"
                )

            # 関連会議の存在チェック
            if self.meeting_repository:
                meetings = await self.meeting_repository.get_by_conference(
                    input_dto.id, limit=1
                )
                if meetings:
                    return DeleteConferenceOutputDto(
                        success=False,
                        error_message="関連する会議が存在するため削除できません。先に会議を削除してください。",
                    )

            await self.conference_repository.delete(input_dto.id)
            return DeleteConferenceOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete conference: {e}")
            return DeleteConferenceOutputDto(success=False, error_message=str(e))

    async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for conferences."""
        try:
            # Get all conferences
            all_conferences = await self.conference_repository.get_all()
            # Generate SQL content
            seed_content = "-- Conferences Seed Data\n"
            seed_content += "-- Generated from current database\n\n"
            seed_content += (
                "INSERT INTO conferences (id, name, governing_body_id, term) VALUES\n"
            )

            values: list[str] = []
            for conf in all_conferences:
                gb_id = conf.governing_body_id if conf.governing_body_id else "NULL"
                term = f"'{conf.term}'" if conf.term else "NULL"
                values.append(f"    ({conf.id}, '{conf.name}', {gb_id}, {term})")

            seed_content += ",\n".join(values) + "\n"
            seed_content += "ON CONFLICT (id) DO UPDATE SET\n"
            seed_content += "    name = EXCLUDED.name,\n"
            seed_content += "    governing_body_id = EXCLUDED.governing_body_id,\n"
            seed_content += "    term = EXCLUDED.term;\n"

            # Save to file
            file_path = "database/seed_conferences_generated.sql"
            with open(file_path, "w") as f:
                f.write(seed_content)

            return GenerateSeedFileOutputDto(
                success=True, seed_content=seed_content, file_path=file_path
            )
        except Exception as e:
            logger.error(f"Failed to generate seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
