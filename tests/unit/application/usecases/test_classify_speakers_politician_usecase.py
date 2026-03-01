"""ClassifySpeakersPoliticianUseCaseのテスト."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.classify_speakers_politician_usecase import (
    ClassifySpeakersPoliticianUseCase,
)
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.speaker_classifier import (
    NON_POLITICIAN_EXACT_NAMES,
    NON_POLITICIAN_PREFIX_PATTERNS,
    SKIP_REASON_PATTERNS,
)


class TestClassifySpeakersPoliticianUseCase:
    """ClassifySpeakersPoliticianUseCaseのテスト."""

    @pytest.fixture()
    def mock_speaker_repository(self) -> AsyncMock:
        """モックSpeakerRepositoryを作成する."""
        return AsyncMock(spec=SpeakerRepository)

    @pytest.fixture()
    def usecase(
        self, mock_speaker_repository: AsyncMock
    ) -> ClassifySpeakersPoliticianUseCase:
        """テスト対象のユースケースを作成する."""
        return ClassifySpeakersPoliticianUseCase(
            speaker_repository=mock_speaker_repository,
        )

    @pytest.mark.asyncio()
    async def test_calls_repository_method(
        self,
        usecase: ClassifySpeakersPoliticianUseCase,
        mock_speaker_repository: AsyncMock,
    ) -> None:
        """execute()がリポジトリのclassify_is_politician_bulkを正しく呼び出す."""
        mock_speaker_repository.classify_is_politician_bulk.return_value = {
            "total_updated_to_politician": 100,
            "total_kept_non_politician": 20,
        }

        result = await usecase.execute()

        mock_speaker_repository.classify_is_politician_bulk.assert_called_once()
        assert result["total_updated_to_politician"] == 100
        assert result["total_kept_non_politician"] == 20

    @pytest.mark.asyncio()
    async def test_passes_non_politician_names_and_prefixes(
        self,
        usecase: ClassifySpeakersPoliticianUseCase,
        mock_speaker_repository: AsyncMock,
    ) -> None:
        """execute()が完全一致パターンとプレフィックスパターンの両方をリポジトリに渡す."""
        mock_speaker_repository.classify_is_politician_bulk.return_value = {
            "total_updated_to_politician": 0,
            "total_kept_non_politician": 0,
        }

        await usecase.execute()

        call_args = mock_speaker_repository.classify_is_politician_bulk.call_args
        passed_names = call_args[0][0]
        passed_prefixes = call_args[1]["non_politician_prefixes"]
        assert passed_names == NON_POLITICIAN_EXACT_NAMES
        assert passed_prefixes == NON_POLITICIAN_PREFIX_PATTERNS

    @pytest.mark.asyncio()
    async def test_passes_skip_reason_patterns(
        self,
        usecase: ClassifySpeakersPoliticianUseCase,
        mock_speaker_repository: AsyncMock,
    ) -> None:
        """execute()がskip_reason_patternsをリポジトリに渡す."""
        mock_speaker_repository.classify_is_politician_bulk.return_value = {
            "total_updated_to_politician": 0,
            "total_kept_non_politician": 0,
        }

        await usecase.execute()

        call_args = mock_speaker_repository.classify_is_politician_bulk.call_args
        passed_patterns = call_args[1]["skip_reason_patterns"]

        # SKIP_REASON_PATTERNSと同数のカテゴリが渡される
        assert len(passed_patterns) == len(SKIP_REASON_PATTERNS)

        # 各パターンが(str, frozenset, frozenset)の形式
        for skip_reason_value, exact_names, prefixes in passed_patterns:
            assert isinstance(skip_reason_value, str)
            assert isinstance(exact_names, frozenset)
            assert isinstance(prefixes, frozenset)

        # SkipReason.valueが文字列として渡されている
        passed_reasons = [p[0] for p in passed_patterns]
        assert "role_only" in passed_reasons
        assert "reference_person" in passed_reasons
        assert "government_official" in passed_reasons
        assert "other_non_politician" in passed_reasons

    @pytest.mark.asyncio()
    async def test_handles_zero_speakers(
        self,
        usecase: ClassifySpeakersPoliticianUseCase,
        mock_speaker_repository: AsyncMock,
    ) -> None:
        """Speakerが0件の場合もエラーなく実行される."""
        mock_speaker_repository.classify_is_politician_bulk.return_value = {
            "total_updated_to_politician": 0,
            "total_kept_non_politician": 0,
        }

        result = await usecase.execute()

        assert result["total_updated_to_politician"] == 0
        assert result["total_kept_non_politician"] == 0
