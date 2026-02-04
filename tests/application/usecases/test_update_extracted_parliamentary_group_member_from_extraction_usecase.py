"""Tests for UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.parliamentary_group_member_extraction_result import (  # noqa: E501
    ParliamentaryGroupMemberExtractionResult,
)
from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
)
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog


class TestUpdateExtractedParliamentaryGroupMemberFromExtractionUseCase:
    """Test cases for UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase."""

    @pytest.fixture
    def mock_extracted_parliamentary_group_member_repo(self):
        """Create mock extracted parliamentary group member repository."""
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
        mock_extracted_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """Create UseCase instance."""
        return UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase(
            extracted_parliamentary_group_member_repo=(
                mock_extracted_parliamentary_group_member_repo
            ),
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_parliamentary_group_member_success(
        self,
        use_case,
        mock_extracted_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """議員団メンバーの更新が成功する。"""
        # Setup
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="幹事長",
            extracted_party_name="自由民主党",
            extracted_district="東京1区",
        )
        extraction_result = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="副幹事長",
            extracted_party_name="自由民主党",
            extracted_district="東京2区",
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="parliamentary-group-member-extractor-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_extracted_parliamentary_group_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="parliamentary-group-member-extractor-v1",
        )

        # Assert
        assert result.updated is True
        assert result.extraction_log_id == 100

        # 各フィールドが更新されたことを確認
        assert member.extracted_name == "山田太郎"
        assert member.extracted_role == "副幹事長"
        assert member.extracted_party_name == "自由民主党"
        assert member.extracted_district == "東京2区"
        assert member.latest_extraction_log_id == 100

        mock_extracted_parliamentary_group_member_repo.update.assert_called_once_with(
            member
        )
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bronze_layer_always_updatable(
        self,
        use_case,
        mock_extracted_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """Bronze Layerの議員団メンバーは常にAI更新可能。

        ExtractedParliamentaryGroupMemberはBronze Layerエンティティであり、
        検証状態はGold Layer（ParliamentaryGroupMembership）で管理されるため、
        常にAI更新可能である。
        """
        # Setup
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
        )
        # Bronze Layerのエンティティは常に更新可能
        assert member.can_be_updated_by_ai() is True
        assert member.is_manually_verified is False  # 常にFalse

        extraction_result = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="山田次郎",  # 名前を変更
            source_url="https://example.com/members",
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="parliamentary-group-member-extractor-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_extracted_parliamentary_group_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="parliamentary-group-member-extractor-v1",
        )

        # Assert - Bronze Layerでは常に更新される
        assert result.updated is True
        assert result.extraction_log_id == 100

        # 名前が更新されていることを確認
        assert member.extracted_name == "山田次郎"

        mock_extracted_parliamentary_group_member_repo.update.assert_called_once_with(
            member
        )
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_not_found(
        self,
        use_case,
        mock_extracted_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """エンティティが見つからない場合はエラーを返す。"""
        # Setup
        extraction_result = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
        )
        # 抽出ログは必ず作成される（Bronze Layer）
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=999,
            pipeline_version="parliamentary-group-member-extractor-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log
        mock_extracted_parliamentary_group_member_repo.get_by_id.return_value = None

        # Execute
        result = await use_case.execute(
            entity_id=999,
            extraction_result=extraction_result,
            pipeline_version="parliamentary-group-member-extractor-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "entity_not_found"
        assert result.extraction_log_id == 100  # ログは作成される

        # 抽出ログは作成される
        mock_extraction_log_repo.create.assert_called_once()
        # エンティティの更新はないのでcommitは呼ばれない
        mock_session_adapter.commit.assert_not_called()
