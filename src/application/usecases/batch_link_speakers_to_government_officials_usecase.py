"""一括自動紐付けユースケース.

未紐付きSpeakerとGovernmentOfficialをNameNormalizerによる正規化名の完全一致で自動紐付けする。
"""

from dataclasses import dataclass, field

from src.domain.entities.government_official import GovernmentOfficial
from src.domain.repositories.government_official_repository import (
    GovernmentOfficialRepository,
)
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.name_normalizer import NameNormalizer


@dataclass
class BatchLinkDetail:
    """一括紐付けの個別結果."""

    government_official_id: int
    government_official_name: str
    speaker_id: int
    speaker_name: str
    normalized_name: str


@dataclass
class BatchLinkOutputDto:
    """一括紐付けの出力DTO."""

    linked_count: int
    skipped_count: int
    details: list[BatchLinkDetail] = field(default_factory=list)


class BatchLinkSpeakersToGovernmentOfficialsUseCase:
    """未紐付きSpeakerとGovernmentOfficialを名前正規化で一括紐付けするユースケース."""

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        government_official_repository: GovernmentOfficialRepository,
    ):
        self.speaker_repository = speaker_repository
        self.government_official_repository = government_official_repository

    async def execute(self, dry_run: bool = False) -> BatchLinkOutputDto:
        """一括紐付けを実行する.

        Args:
            dry_run: Trueの場合はDBに書き込まず、紐付け候補のみ返す

        Returns:
            BatchLinkOutputDto: 紐付け結果
        """
        # 1. 全GovernmentOfficialを取得
        officials = await self.government_official_repository.get_all()

        # 2. 未紐付きSpeaker取得（politician_id IS NULL）
        all_non_politician_speakers = (
            await self.speaker_repository.get_speakers_not_linked_to_politicians()
        )
        # さらにgovernment_official_idが未設定のものだけ対象
        unlinked = [
            s for s in all_non_politician_speakers if s.government_official_id is None
        ]

        # 3. GovernmentOfficialの正規化名マップを構築
        official_map: dict[str, GovernmentOfficial] = {}
        for o in officials:
            normalized = NameNormalizer.normalize(o.name)
            if normalized:
                official_map[normalized] = o

        # 4. Speakerを正規化名で照合
        details: list[BatchLinkDetail] = []
        for speaker in unlinked:
            normalized_speaker = NameNormalizer.normalize(speaker.name)
            if normalized_speaker in official_map:
                official = official_map[normalized_speaker]
                if not dry_run:
                    speaker.link_to_government_official(official.id)  # type: ignore[arg-type]
                    await self.speaker_repository.update(speaker)
                details.append(
                    BatchLinkDetail(
                        government_official_id=official.id,  # type: ignore[arg-type]
                        government_official_name=official.name,
                        speaker_id=speaker.id,  # type: ignore[arg-type]
                        speaker_name=speaker.name,
                        normalized_name=normalized_speaker,
                    )
                )

        return BatchLinkOutputDto(
            linked_count=len(details),
            skipped_count=len(unlinked) - len(details),
            details=details,
        )
