"""SQLAlchemy implementation of Unit of Work pattern.

This implementation provides transaction management for multiple repositories
using SQLAlchemy's session, ensuring all operations share the same transaction.
"""

from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.unit_of_work import IUnitOfWork
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.minutes_repository_impl import MinutesRepositoryImpl
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl


class UnitOfWorkImpl(IUnitOfWork):
    """SQLAlchemy implementation of Unit of Work.

    This class manages a single database session and provides repositories
    that all share this session, ensuring transactional consistency.
    """

    def __init__(self, session: ISessionAdapter):
        """Initialize Unit of Work with a database session.

        Args:
            session: The database session adapter to use for all repository operations
        """
        self._session = session

        # Create repositories that share the same session
        self._meeting_repository = MeetingRepositoryImpl(session)
        self._minutes_repository = MinutesRepositoryImpl(session)
        self._conversation_repository = ConversationRepositoryImpl(session)
        self._speaker_repository = SpeakerRepositoryImpl(session)

    @property
    def meeting_repository(self) -> MeetingRepository:
        """Get the meeting repository for this unit of work."""
        return self._meeting_repository

    @property
    def minutes_repository(self) -> MinutesRepository:
        """Get the minutes repository for this unit of work."""
        return self._minutes_repository

    @property
    def conversation_repository(self) -> ConversationRepository:
        """Get the conversation repository for this unit of work."""
        return self._conversation_repository

    @property
    def speaker_repository(self) -> SpeakerRepository:
        """Get the speaker repository for this unit of work."""
        return self._speaker_repository

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush changes to database without committing.

        This makes the changes visible within the current transaction,
        allowing foreign key references to work correctly.
        """
        await self._session.flush()
