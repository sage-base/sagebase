"""MarkEntityAsVerifiedUseCaseの単体テスト。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.domain.entities.conversation import Conversation


class TestMarkEntityAsVerifiedUseCase:
    """MarkEntityAsVerifiedUseCaseのテスト。"""

    @pytest.fixture
    def mock_conversation_repo(self) -> MagicMock:
        """発言リポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def usecase(
        self,
        mock_conversation_repo: MagicMock,
    ) -> MarkEntityAsVerifiedUseCase:
        """UseCaseのインスタンス。"""
        return MarkEntityAsVerifiedUseCase(
            conversation_repository=mock_conversation_repo,
        )

    # ========== Conversationエンティティのテスト ==========

    @pytest.mark.asyncio
    async def test_mark_conversation_as_verified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """発言を手動検証済みにマーク成功のテスト。"""
        # Arrange
        conversation = Conversation(
            id=1,
            comment="テスト発言",
            sequence_number=1,
            minutes_id=1,
        )
        mock_conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        mock_conversation_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert conversation.is_manually_verified is True
        mock_conversation_repo.get_by_id.assert_called_once_with(1)
        mock_conversation_repo.update.assert_called_once_with(conversation)

    @pytest.mark.asyncio
    async def test_mark_conversation_as_unverified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """発言の手動検証済みを解除するテスト。"""
        # Arrange
        conversation = Conversation(
            id=1,
            comment="テスト発言",
            sequence_number=1,
            minutes_id=1,
        )
        conversation.mark_as_manually_verified()
        assert conversation.is_manually_verified is True

        mock_conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        mock_conversation_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=False,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert conversation.is_manually_verified is False

    @pytest.mark.asyncio
    async def test_mark_conversation_not_found(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """発言が見つからない場合のテスト。"""
        # Arrange
        mock_conversation_repo.get_by_id = AsyncMock(return_value=None)

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=999,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "発言が見つかりません。"

    @pytest.mark.asyncio
    async def test_conversation_repository_not_configured(self) -> None:
        """発言リポジトリが未設定の場合のテスト。"""
        # Arrange
        usecase = MarkEntityAsVerifiedUseCase()  # リポジトリなしで作成

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "not configured" in result.error_message  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_repository_error_handling(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """リポジトリエラー時のハンドリングテスト。"""
        # Arrange
        mock_conversation_repo.get_by_id = AsyncMock(
            side_effect=Exception("Database error")
        )

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message  # type: ignore[operator]
