"""Tests for UpdateExtractedConferenceMemberFromExtractionUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.conference_member_extraction_result import (
    ConferenceMemberExtractionResult,
)
from src.application.usecases.update_extracted_conference_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedConferenceMemberFromExtractionUseCase,
)
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.entities.extraction_log import EntityType, ExtractionLog


class TestUpdateExtractedConferenceMemberFromExtractionUseCase:
    """Test cases for UpdateExtractedConferenceMemberFromExtractionUseCase."""

    @pytest.fixture
    def mock_extracted_conference_member_repo(self):
        """Create mock extracted conference member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """Create mock extraction log repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """Create mock session adapter."""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self,
        mock_extracted_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """Create UseCase instance."""
        return UpdateExtractedConferenceMemberFromExtractionUseCase(
            extracted_conference_member_repo=mock_extracted_conference_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_conference_member_success(
        self,
        use_case,
        mock_extracted_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """会議体メンバーの更新が成功する。"""
        # Setup
        member = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="委員長",
            extracted_party_name="自由民主党",
            is_manually_verified=False,
        )
        extraction_result = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="副委員長",
            extracted_party_name="自由民主党",
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            pipeline_version="conference-member-extractor-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_extracted_conference_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="conference-member-extractor-v1",
        )

        # Assert
        assert result.updated is True
        assert result.extraction_log_id == 100

        # 各フィールドが更新されたことを確認
        assert member.extracted_name == "山田太郎"
        assert member.extracted_role == "副委員長"
        assert member.extracted_party_name == "自由民主党"
        assert member.latest_extraction_log_id == 100

        mock_extracted_conference_member_repo.update.assert_called_once_with(member)
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_update_when_manually_verified(
        self,
        use_case,
        mock_extracted_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みの会議体メンバーは更新がスキップされる。"""
        # Setup
        member = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            is_manually_verified=True,
        )
        extraction_result = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="山田次郎",
            source_url="https://example.com/members",
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            pipeline_version="conference-member-extractor-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_extracted_conference_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="conference-member-extractor-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"
        assert result.extraction_log_id == 100

        # 名前が更新されていないことを確認
        assert member.extracted_name == "山田太郎"

        # updateは呼ばれない（手動検証済みのためスキップ）
        mock_extracted_conference_member_repo.update.assert_not_called()
        # commitも呼ばれない（エンティティの更新がないため）
        mock_session_adapter.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_entity_not_found(
        self,
        use_case,
        mock_extracted_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """エンティティが見つからない場合はエラーを返す。"""
        # Setup
        extraction_result = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
        )
        # 抽出ログは必ず作成される（Bronze Layer）
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=999,
            pipeline_version="conference-member-extractor-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log
        mock_extracted_conference_member_repo.get_by_id.return_value = None

        # Execute
        result = await use_case.execute(
            entity_id=999,
            extraction_result=extraction_result,
            pipeline_version="conference-member-extractor-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "entity_not_found"
        assert result.extraction_log_id == 100  # ログは作成される

        # 抽出ログは作成される
        mock_extraction_log_repo.create.assert_called_once()
        # エンティティの更新はないのでcommitは呼ばれない
        mock_session_adapter.commit.assert_not_called()
