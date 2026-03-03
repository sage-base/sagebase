"""政府関係者関連のDTO定義."""

from dataclasses import dataclass, field
from datetime import date

from src.domain.entities.government_official import GovernmentOfficial
from src.domain.entities.government_official_position import GovernmentOfficialPosition


@dataclass
class GovernmentOfficialPositionOutputItem:
    """政府関係者の役職履歴出力DTO."""

    id: int
    government_official_id: int
    organization: str
    position: str
    start_date: date | None = None
    end_date: date | None = None
    source_note: str | None = None

    @classmethod
    def from_entity(
        cls, entity: GovernmentOfficialPosition
    ) -> "GovernmentOfficialPositionOutputItem":
        return cls(
            id=entity.id or 0,
            government_official_id=entity.government_official_id,
            organization=entity.organization,
            position=entity.position,
            start_date=entity.start_date,
            end_date=entity.end_date,
            source_note=entity.source_note,
        )


@dataclass
class GovernmentOfficialOutputItem:
    """政府関係者出力DTO."""

    id: int
    name: str
    name_yomi: str | None = None
    positions: list[GovernmentOfficialPositionOutputItem] = field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        entity: GovernmentOfficial,
        positions: list[GovernmentOfficialPosition] | None = None,
    ) -> "GovernmentOfficialOutputItem":
        return cls(
            id=entity.id or 0,
            name=entity.name,
            name_yomi=entity.name_yomi,
            positions=[
                GovernmentOfficialPositionOutputItem.from_entity(p)
                for p in (positions or [])
            ],
        )


@dataclass
class LinkSpeakerToGovernmentOfficialInputDto:
    """発言者-政府関係者紐付け入力DTO."""

    speaker_id: int
    government_official_id: int


@dataclass
class LinkSpeakerToGovernmentOfficialOutputDto:
    """発言者-政府関係者紐付け出力DTO."""

    success: bool
    error_message: str | None = None


@dataclass
class GovernmentOfficialCsvRow:
    """CSVの1行を表すDTO."""

    speaker_name: str
    representative_speaker_id: int
    organization: str
    position: str
    notes: str | None = None


@dataclass
class ImportGovernmentOfficialsCsvInputDto:
    """政府関係者CSV取込入力DTO."""

    rows: list[GovernmentOfficialCsvRow]
    dry_run: bool = False


@dataclass
class ImportGovernmentOfficialsCsvOutputDto:
    """政府関係者CSV取込出力DTO."""

    created_officials_count: int = 0
    created_positions_count: int = 0
    linked_speakers_count: int = 0
    skipped_count: int = 0
    errors: list[str] = field(default_factory=list)
