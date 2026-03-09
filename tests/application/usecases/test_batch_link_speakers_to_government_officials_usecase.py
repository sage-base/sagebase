"""BatchLinkSpeakersToGovernmentOfficialsUseCaseのテスト."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.batch_link_speakers_to_government_officials_usecase import (  # noqa: E501
    BatchLinkSpeakersToGovernmentOfficialsUseCase,
)
from src.domain.entities.government_official import GovernmentOfficial
from src.domain.entities.speaker import Speaker


def _make_speaker(
    id: int,
    name: str,
    government_official_id: int | None = None,
) -> Speaker:
    """テスト用Speakerを作成する."""
    speaker = Speaker(name=name, id=id)
    speaker.government_official_id = government_official_id
    speaker.is_politician = False
    return speaker


def _make_official(id: int, name: str) -> GovernmentOfficial:
    """テスト用GovernmentOfficialを作成する."""
    return GovernmentOfficial(id=id, name=name)


@pytest.fixture
def speaker_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def official_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def usecase(
    speaker_repo: AsyncMock, official_repo: AsyncMock
) -> BatchLinkSpeakersToGovernmentOfficialsUseCase:
    return BatchLinkSpeakersToGovernmentOfficialsUseCase(
        speaker_repository=speaker_repo,
        government_official_repository=official_repo,
    )


@pytest.mark.asyncio
async def test_basic_match(
    usecase: BatchLinkSpeakersToGovernmentOfficialsUseCase,
    speaker_repo: AsyncMock,
    official_repo: AsyncMock,
) -> None:
    """正規化後の完全一致で紐付けされること."""
    official_repo.get_all.return_value = [_make_official(1, "田中太郎")]
    speaker_repo.get_speakers_not_linked_to_politicians.return_value = [
        _make_speaker(10, "田中太郎"),
    ]

    result = await usecase.execute(dry_run=False)

    assert result.linked_count == 1
    assert result.skipped_count == 0
    assert len(result.details) == 1
    assert result.details[0].government_official_id == 1
    assert result.details[0].speaker_id == 10
    speaker_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_old_kanji_match(
    usecase: BatchLinkSpeakersToGovernmentOfficialsUseCase,
    speaker_repo: AsyncMock,
    official_repo: AsyncMock,
) -> None:
    """旧漢字→新漢字変換後にマッチすること."""
    official_repo.get_all.return_value = [_make_official(1, "斎藤一郎")]
    speaker_repo.get_speakers_not_linked_to_politicians.return_value = [
        _make_speaker(10, "齋藤一郎"),
    ]

    result = await usecase.execute(dry_run=False)

    assert result.linked_count == 1
    assert result.details[0].normalized_name == "斎藤一郎"


@pytest.mark.asyncio
async def test_already_linked_skipped(
    usecase: BatchLinkSpeakersToGovernmentOfficialsUseCase,
    speaker_repo: AsyncMock,
    official_repo: AsyncMock,
) -> None:
    """government_official_id設定済みのSpeakerはスキップされること."""
    official_repo.get_all.return_value = [_make_official(1, "田中太郎")]
    speaker_repo.get_speakers_not_linked_to_politicians.return_value = [
        _make_speaker(10, "田中太郎", government_official_id=2),
    ]

    result = await usecase.execute(dry_run=False)

    assert result.linked_count == 0
    assert result.skipped_count == 0  # フィルタで除外されるため
    speaker_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_no_write(
    usecase: BatchLinkSpeakersToGovernmentOfficialsUseCase,
    speaker_repo: AsyncMock,
    official_repo: AsyncMock,
) -> None:
    """dry_run=TrueでDBに書き込まないこと."""
    official_repo.get_all.return_value = [_make_official(1, "田中太郎")]
    speaker_repo.get_speakers_not_linked_to_politicians.return_value = [
        _make_speaker(10, "田中太郎"),
    ]

    result = await usecase.execute(dry_run=True)

    assert result.linked_count == 1
    assert len(result.details) == 1
    speaker_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_no_match_skipped(
    usecase: BatchLinkSpeakersToGovernmentOfficialsUseCase,
    speaker_repo: AsyncMock,
    official_repo: AsyncMock,
) -> None:
    """マッチしない場合はskipped_countが正しいこと."""
    official_repo.get_all.return_value = [_make_official(1, "田中太郎")]
    speaker_repo.get_speakers_not_linked_to_politicians.return_value = [
        _make_speaker(10, "佐藤花子"),
        _make_speaker(11, "鈴木次郎"),
    ]

    result = await usecase.execute(dry_run=False)

    assert result.linked_count == 0
    assert result.skipped_count == 2


@pytest.mark.asyncio
async def test_whitespace_normalization(
    usecase: BatchLinkSpeakersToGovernmentOfficialsUseCase,
    speaker_repo: AsyncMock,
    official_repo: AsyncMock,
) -> None:
    """スペースが含まれる名前でも正規化後にマッチすること."""
    official_repo.get_all.return_value = [_make_official(1, "田中太郎")]
    speaker_repo.get_speakers_not_linked_to_politicians.return_value = [
        _make_speaker(10, "田中　太郎"),  # 全角スペース
    ]

    result = await usecase.execute(dry_run=False)

    assert result.linked_count == 1
