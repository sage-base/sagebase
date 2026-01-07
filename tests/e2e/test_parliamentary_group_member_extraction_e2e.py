"""E2Eテスト: ParliamentaryGroupMember抽出の完全なフロー (Issue #871).

議員団メンバー情報の抽出・更新・手動修正保護の完全なE2Eフローをテスト。

フロー：
1. 議員団ページからのメンバー抽出
2. ログ確認
3. 手動修正
4. 再抽出
5. 手動修正が保護されていることを確認
"""

from datetime import datetime
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


@pytest.mark.e2e
class TestParliamentaryGroupMemberExtractionFullFlow:
    """ParliamentaryGroupMember抽出の完全なE2Eフローテスト。"""

    @pytest.fixture
    def mock_parliamentary_group_member_repo(self):
        """議員団メンバーリポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """UpdateExtractedParliamentaryGroupMemberFromExtractionUseCaseのインスタンス。"""
        return UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase(
            extracted_parliamentary_group_member_repo=mock_parliamentary_group_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_parliamentary_group_member_extraction_full_flow(
        self,
        use_case,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """ParliamentaryGroupMember抽出の完全なE2Eフロー。"""
        # ============================================
        # Step 1: 議員団ページからの初回抽出
        # ============================================
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_at=datetime.now(),
            is_manually_verified=False,
        )

        extraction_result_1 = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_district="大阪1区",
            extracted_party_name="自民党",
            confidence_score=0.85,
        )
        extraction_log_1 = ExtractionLog(
            id=6000,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="group-member-extraction-baml-v1",
            extracted_data=extraction_result_1.to_dict(),
        )

        mock_parliamentary_group_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log_1

        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="group-member-extraction-baml-v1",
        )

        # Step 1 検証
        assert result_1.updated is True
        assert result_1.extraction_log_id == 6000
        assert member.extracted_role == "団長"
        assert member.extracted_district == "大阪1区"
        assert member.extracted_party_name == "自民党"

        # ============================================
        # Step 2: ログ確認
        # ============================================
        mock_extraction_log_repo.get_by_entity.return_value = [extraction_log_1]
        logs = await mock_extraction_log_repo.get_by_entity(
            EntityType.PARLIAMENTARY_GROUP_MEMBER, 1
        )
        assert len(logs) == 1

        # ============================================
        # Step 3: 手動修正
        # ============================================
        member.extracted_district = "大阪2区"  # 選挙区を修正
        member.mark_as_manually_verified()

        assert member.is_manually_verified is True
        assert member.extracted_district == "大阪2区"

        # ============================================
        # Step 4: 再抽出
        # ============================================
        extraction_result_2 = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_district="大阪3区",  # AIは異なる選挙区を抽出
            confidence_score=0.80,
        )
        extraction_log_2 = ExtractionLog(
            id=6001,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="group-member-extraction-baml-v2",
            extracted_data=extraction_result_2.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log_2

        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="group-member-extraction-baml-v2",
        )

        # ============================================
        # Step 5: 手動修正が保護されていることを確認
        # ============================================
        assert result_2.updated is False
        assert result_2.reason == "manually_verified"
        assert member.extracted_district == "大阪2区"  # 手動修正が保持


@pytest.mark.e2e
class TestParliamentaryGroupMemberBulkExtraction:
    """ParliamentaryGroupMember一括抽出のE2Eテスト。"""

    @pytest.fixture
    def mock_parliamentary_group_member_repo(self):
        """議員団メンバーリポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """UpdateExtractedParliamentaryGroupMemberFromExtractionUseCaseのインスタンス。"""
        return UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase(
            extracted_parliamentary_group_member_repo=mock_parliamentary_group_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_bulk_parliamentary_group_member_extraction(
        self,
        use_case,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """複数議員団メンバーの一括抽出E2Eテスト。"""
        # Setup: 同一議員団の10名のメンバー
        members = {
            i: ExtractedParliamentaryGroupMember(
                id=i,
                parliamentary_group_id=10,
                extracted_name=f"議員{i}",
                source_url="https://example.com/group-members",
                extracted_at=datetime.now(),
                is_manually_verified=False,
            )
            for i in range(1, 11)
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_member(entity_id: int):
            return members.get(entity_id)

        mock_parliamentary_group_member_repo.get_by_id.side_effect = get_member
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        roles = [
            "団長",
            "副団長",
            "幹事長",
            "政調会長",
            "国対委員長",
            "会員",
            "会員",
            "会員",
            "会員",
            "会員",
        ]
        results = []

        for i in range(1, 11):
            extraction_result = ParliamentaryGroupMemberExtractionResult(
                parliamentary_group_id=10,
                extracted_name=f"議員{i}",
                source_url="https://example.com/group-members",
                extracted_role=roles[i - 1],
                extracted_district=f"選挙区{i}",
                confidence_score=0.9,
            )
            result = await use_case.execute(
                entity_id=i,
                extraction_result=extraction_result,
                pipeline_version="bulk-extraction-v1",
            )
            results.append(result)

        # Assert
        assert all(r.updated is True for r in results)
        assert mock_extraction_log_repo.create.call_count == 10

        # 各メンバーが正しく設定された
        assert members[1].extracted_role == "団長"
        assert members[2].extracted_role == "副団長"
        assert members[3].extracted_role == "幹事長"


@pytest.mark.e2e
class TestParliamentaryGroupMemberCrossGroupExtraction:
    """複数議員団にまたがる抽出のE2Eテスト。"""

    @pytest.fixture
    def mock_parliamentary_group_member_repo(self):
        """議員団メンバーリポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """UpdateExtractedParliamentaryGroupMemberFromExtractionUseCaseのインスタンス。"""
        return UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase(
            extracted_parliamentary_group_member_repo=mock_parliamentary_group_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_cross_parliamentary_group_extraction(
        self,
        use_case,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """複数議員団からの抽出E2Eテスト。"""
        # Setup: 3つの議員団からのメンバー
        members = {
            # 議員団A (ID: 10)
            1: ExtractedParliamentaryGroupMember(
                id=1,
                parliamentary_group_id=10,
                extracted_name="議員A-1",
                source_url="https://example.com/group-a",
                extracted_at=datetime.now(),
                is_manually_verified=False,
            ),
            2: ExtractedParliamentaryGroupMember(
                id=2,
                parliamentary_group_id=10,
                extracted_name="議員A-2",
                source_url="https://example.com/group-a",
                extracted_at=datetime.now(),
                is_manually_verified=False,
            ),
            # 議員団B (ID: 20)
            3: ExtractedParliamentaryGroupMember(
                id=3,
                parliamentary_group_id=20,
                extracted_name="議員B-1",
                source_url="https://example.com/group-b",
                extracted_at=datetime.now(),
                is_manually_verified=False,
            ),
            # 議員団C (ID: 30)
            4: ExtractedParliamentaryGroupMember(
                id=4,
                parliamentary_group_id=30,
                extracted_name="議員C-1",
                source_url="https://example.com/group-c",
                extracted_at=datetime.now(),
                is_manually_verified=True,  # 検証済み
                extracted_role="手動設定の役職",
            ),
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_member(entity_id: int):
            return members.get(entity_id)

        mock_parliamentary_group_member_repo.get_by_id.side_effect = get_member
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        extraction_data = [
            (1, 10, "https://example.com/group-a", "団長"),
            (2, 10, "https://example.com/group-a", "会員"),
            (3, 20, "https://example.com/group-b", "代表"),
            (4, 30, "https://example.com/group-c", "AIが抽出した役職"),
        ]

        results = []
        for entity_id, group_id, url, role in extraction_data:
            extraction_result = ParliamentaryGroupMemberExtractionResult(
                parliamentary_group_id=group_id,
                extracted_name="議員",
                source_url=url,
                extracted_role=role,
            )
            result = await use_case.execute(
                entity_id=entity_id,
                extraction_result=extraction_result,
                pipeline_version="cross-group-v1",
            )
            results.append(result)

        # Assert
        # 未検証のメンバー（1, 2, 3）は更新される
        assert results[0].updated is True
        assert results[1].updated is True
        assert results[2].updated is True

        # 検証済みのメンバー（4）は保護される
        assert results[3].updated is False
        assert results[3].reason == "manually_verified"

        # 各議員団のメンバーが正しく設定された
        assert members[1].extracted_role == "団長"
        assert members[2].extracted_role == "会員"
        assert members[3].extracted_role == "代表"
        assert members[4].extracted_role == "手動設定の役職"  # 手動修正が保持

        # 全てのログが作成された
        assert mock_extraction_log_repo.create.call_count == 4
