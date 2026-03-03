"""SQLAlchemy ORM models for database tables.

This module contains proper SQLAlchemy declarative models for tables that
previously used Pydantic models or dummy dynamic models. This allows the
repository pattern to use ORM features instead of raw SQL.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class ParliamentaryGroupMembershipModel(Base):
    """SQLAlchemy model for parliamentary_group_memberships table."""

    __tablename__ = "parliamentary_group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("politicians.id", use_alter=True, name="fk_pgm_politician")
    )
    parliamentary_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parliamentary_groups.id", use_alter=True, name="fk_pgm_group"),
    )
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    role: Mapped[str | None] = mapped_column(String(100))
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", use_alter=True, name="fk_pgm_user")
    )
    is_manually_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    latest_extraction_log_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("extraction_logs.id", use_alter=True, name="fk_pgm_extraction_log"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="chk_membership_end_date_after_start",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ParliamentaryGroupMembershipModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"parliamentary_group_id={self.parliamentary_group_id}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}"
            f")>"
        )


class UserModel(Base):
    """SQLAlchemy model for users table (minimal definition for FK support)."""

    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"<UserModel(user_id={self.user_id}, email={self.email})>"


class PoliticianModel(Base):
    """SQLAlchemy model for politicians table."""

    __tablename__ = "politicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    prefecture: Mapped[str | None] = mapped_column(String(10))
    furigana: Mapped[str | None] = mapped_column(String)
    district: Mapped[str | None] = mapped_column(String)
    profile_page_url: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<PoliticianModel(id={self.id}, name={self.name})>"


class ParliamentaryGroupModel(Base):
    """SQLAlchemy model for parliamentary_groups table."""

    __tablename__ = "parliamentary_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    governing_body_id: Mapped[int] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    chamber: Mapped[str] = mapped_column(String(10), default="", server_default="")
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ParliamentaryGroupModel("
            f"id={self.id}, "
            f"name={self.name}, "
            f"governing_body_id={self.governing_body_id}"
            f")>"
        )


class ParliamentaryGroupPartyModel(Base):
    """SQLAlchemy model for parliamentary_group_parties table."""

    __tablename__ = "parliamentary_group_parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    parliamentary_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "parliamentary_groups.id",
            ondelete="CASCADE",
            use_alter=True,
            name="fk_pgp_group",
        ),
    )
    political_party_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "political_parties.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_pgp_party",
        ),
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ParliamentaryGroupPartyModel("
            f"id={self.id}, "
            f"parliamentary_group_id={self.parliamentary_group_id}, "
            f"political_party_id={self.political_party_id}, "
            f"is_primary={self.is_primary}"
            f")>"
        )


class ExtractedParliamentaryGroupMemberModel(Base):
    """SQLAlchemy model for extracted_parliamentary_group_members table."""

    __tablename__ = "extracted_parliamentary_group_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    parliamentary_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parliamentary_groups.id", use_alter=True, name="fk_epgm_group"),
    )
    extracted_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(500))
    extracted_role: Mapped[str | None] = mapped_column(String(100))
    extracted_party_name: Mapped[str | None] = mapped_column(String(200))
    extracted_district: Mapped[str | None] = mapped_column(String(200))
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    matched_politician_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_epgm_politician"),
    )
    matching_confidence: Mapped[float | None] = mapped_column()  # 0.0-1.0
    matching_status: Mapped[str] = mapped_column(String(20), default="pending")
    matched_at: Mapped[datetime | None] = mapped_column(DateTime)
    additional_info: Mapped[str | None] = mapped_column(String(1000))

    def __repr__(self) -> str:
        return (
            f"<ExtractedParliamentaryGroupMemberModel("
            f"id={self.id}, "
            f"extracted_name={self.extracted_name}, "
            f"matching_status={self.matching_status}"
            f")>"
        )


class PoliticianOperationLogModel(Base):
    """SQLAlchemy model for politician_operation_logs table."""

    __tablename__ = "politician_operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(Integer, nullable=False)
    politician_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.user_id", use_alter=True, name="fk_pol_log_user")
    )
    operation_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    operated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('create', 'update', 'delete')",
            name="check_operation_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PoliticianOperationLogModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"politician_name={self.politician_name}, "
            f"operation_type={self.operation_type}"
            f")>"
        )


class ElectionModel(Base):
    """SQLAlchemy model for elections table."""

    __tablename__ = "elections"
    __table_args__ = (
        Index(
            "idx_elections_governing_body_term_type",
            "governing_body_id",
            "term_number",
            "election_type",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    governing_body_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("governing_bodies.id", use_alter=True, name="fk_election_gb"),
    )
    term_number: Mapped[int] = mapped_column(Integer)
    election_date: Mapped[date] = mapped_column()
    election_type: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ElectionMemberModel(Base):
    """SQLAlchemy model for election_members table."""

    __tablename__ = "election_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("elections.id", use_alter=True, name="fk_em_election"),
    )
    politician_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_em_politician"),
    )
    result: Mapped[str] = mapped_column(String(50))
    votes: Mapped[int | None] = mapped_column(Integer)
    rank: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ElectionMemberModel("
            f"id={self.id}, "
            f"election_id={self.election_id}, "
            f"politician_id={self.politician_id}, "
            f"result={self.result}"
            f")>"
        )


class PartyMembershipHistoryModel(Base):
    """SQLAlchemy model for party_membership_history table."""

    __tablename__ = "party_membership_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_pmh_politician"),
    )
    political_party_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("political_parties.id", use_alter=True, name="fk_pmh_party"),
    )
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="chk_party_membership_end_date_after_start",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PartyMembershipHistoryModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"political_party_id={self.political_party_id}, "
            f"start_date={self.start_date}, "
            f"end_date={self.end_date}"
            f")>"
        )


class PoliticalPartyModel(Base):
    """SQLAlchemy model for political_parties table."""

    __tablename__ = "political_parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    members_list_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<PoliticalPartyModel(id={self.id}, name={self.name})>"


class GoverningBodyModel(Base):
    """SQLAlchemy model for governing_bodies table."""

    __tablename__ = "governing_bodies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str | None] = mapped_column(String)
    organization_code: Mapped[str | None] = mapped_column(String(6), unique=True)
    organization_type: Mapped[str | None] = mapped_column(String(20))
    prefecture: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<GoverningBodyModel(id={self.id}, name={self.name})>"


class ConferenceMemberModel(Base):
    """SQLAlchemy model for conference_members table."""

    __tablename__ = "conference_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    politician_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_cm_politician"),
        nullable=False,
    )
    conference_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conferences.id", use_alter=True, name="fk_cm_conference"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    role: Mapped[str | None] = mapped_column(String(100))
    is_manually_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_extraction_log_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("extraction_logs.id", use_alter=True, name="fk_cm_extraction_log"),
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="chk_cm_end_date_after_start",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConferenceMemberModel("
            f"id={self.id}, "
            f"politician_id={self.politician_id}, "
            f"conference_id={self.conference_id}"
            f")>"
        )


class SpeakerModel(Base):
    """SQLAlchemy model for speakers table."""

    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str | None] = mapped_column(String)
    political_party_name: Mapped[str | None] = mapped_column(String)
    position: Mapped[str | None] = mapped_column(String)
    is_politician: Mapped[bool] = mapped_column(Boolean, default=False)
    politician_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_speaker_politician"),
    )
    matching_process_id: Mapped[int | None] = mapped_column(Integer)
    matching_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    matching_reason: Mapped[str | None] = mapped_column(Text)
    matched_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.user_id", use_alter=True, name="fk_speaker_user"),
    )
    is_manually_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_extraction_log_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "extraction_logs.id",
            use_alter=True,
            name="fk_speaker_extraction_log",
        ),
    )
    name_yomi: Mapped[str | None] = mapped_column(String)
    skip_reason: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<SpeakerModel(id={self.id}, name={self.name})>"


class MeetingModel(Base):
    """SQLAlchemy model for meetings table."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    conference_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conferences.id", use_alter=True, name="fk_meeting_conference"),
        nullable=False,
    )
    date: Mapped["date | None"] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    gcs_pdf_uri: Mapped[str | None] = mapped_column(String(512))
    gcs_text_uri: Mapped[str | None] = mapped_column(String(512))
    attendees_mapping: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<MeetingModel(id={self.id}, conference_id={self.conference_id})>"
