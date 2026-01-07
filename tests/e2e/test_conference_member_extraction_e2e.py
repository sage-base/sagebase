"""E2Eテスト: ConferenceMember抽出の完全なフロー (Issue #871).

会議体メンバー情報の抽出・更新・手動修正保護の完全なE2Eフローをテスト。

フロー：
1. 会議体ページからのメンバー抽出
2. ログ確認
3. 手動修正
4. 再抽出
5. 手動修正が保護されていることを確認
"""

from datetime import datetime
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


@pytest.mark.e2e
class TestConferenceMemberExtractionFullFlow:
    """ConferenceMember抽出の完全なE2Eフローテスト。"""

    @pytest.fixture
    def mock_conference_member_repo(self):
        """会議体メンバーリポジトリのモック。"""
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
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """UpdateExtractedConferenceMemberFromExtractionUseCaseのインスタンス。"""
        return UpdateExtractedConferenceMemberFromExtractionUseCase(
            extracted_conference_member_repo=mock_conference_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_conference_member_extraction_full_flow(
        self,
        use_case,
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """ConferenceMember抽出の完全なE2Eフロー。"""
        # ============================================
        # Step 1: 会議体ページからの初回抽出
        # ============================================
        member = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_at=datetime.now(),
            is_manually_verified=False,
        )

        extraction_result_1 = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_role="議長",
            extracted_party_name="自民党",
            confidence_score=0.9,
        )
        extraction_log_1 = ExtractionLog(
            id=5000,
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            pipeline_version="member-extraction-baml-v1",
            extracted_data=extraction_result_1.to_dict(),
        )

        mock_conference_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log_1

        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="member-extraction-baml-v1",
        )

        # Step 1 検証
        assert result_1.updated is True
        assert result_1.extraction_log_id == 5000
        assert member.extracted_role == "議長"
        assert member.extracted_party_name == "自民党"

        # ============================================
        # Step 2: ログ確認
        # ============================================
        mock_extraction_log_repo.get_by_entity.return_value = [extraction_log_1]
        logs = await mock_extraction_log_repo.get_by_entity(
            EntityType.CONFERENCE_MEMBER, 1
        )
        assert len(logs) == 1

        # ============================================
        # Step 3: 手動修正
        # ============================================
        member.extracted_role = "副議長"  # 役職を修正
        member.mark_as_manually_verified()

        assert member.is_manually_verified is True
        assert member.extracted_role == "副議長"

        # ============================================
        # Step 4: 再抽出
        # ============================================
        extraction_result_2 = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_role="委員長",  # AIは異なる役職を抽出
            extracted_party_name="自民党",
            confidence_score=0.85,
        )
        extraction_log_2 = ExtractionLog(
            id=5001,
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            pipeline_version="member-extraction-baml-v2",
            extracted_data=extraction_result_2.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log_2

        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="member-extraction-baml-v2",
        )

        # ============================================
        # Step 5: 手動修正が保護されていることを確認
        # ============================================
        assert result_2.updated is False
        assert result_2.reason == "manually_verified"
        assert member.extracted_role == "副議長"  # 手動修正が保持


@pytest.mark.e2e
class TestConferenceMemberBulkExtraction:
    """ConferenceMember一括抽出のE2Eテスト。"""

    @pytest.fixture
    def mock_conference_member_repo(self):
        """会議体メンバーリポジトリのモック。"""
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
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """UpdateExtractedConferenceMemberFromExtractionUseCaseのインスタンス。"""
        return UpdateExtractedConferenceMemberFromExtractionUseCase(
            extracted_conference_member_repo=mock_conference_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_bulk_conference_member_extraction(
        self,
        use_case,
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """複数会議体メンバーの一括抽出E2Eテスト。"""
        # Setup: 同一会議体の10名のメンバー
        members = {
            i: ExtractedConferenceMember(
                id=i,
                conference_id=10,
                extracted_name=f"議員{i}",
                source_url="https://example.com/members",
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

        mock_conference_member_repo.get_by_id.side_effect = get_member
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        roles = [
            "議長",
            "副議長",
            "委員長",
            "委員",
            "委員",
            "委員",
            "委員",
            "委員",
            "委員",
            "委員",
        ]
        results = []

        for i in range(1, 11):
            extraction_result = ConferenceMemberExtractionResult(
                conference_id=10,
                extracted_name=f"議員{i}",
                source_url="https://example.com/members",
                extracted_role=roles[i - 1],
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

        # 各メンバーの役職が正しく設定された
        assert members[1].extracted_role == "議長"
        assert members[2].extracted_role == "副議長"
        assert members[3].extracted_role == "委員長"


@pytest.mark.e2e
class TestConferenceMemberPoliticianMatching:
    """ConferenceMemberと政治家のマッチングE2Eテスト。"""

    @pytest.fixture
    def mock_conference_member_repo(self):
        """会議体メンバーリポジトリのモック。"""
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
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """UpdateExtractedConferenceMemberFromExtractionUseCaseのインスタンス。"""
        return UpdateExtractedConferenceMemberFromExtractionUseCase(
            extracted_conference_member_repo=mock_conference_member_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_conference_member_with_various_verification_states(
        self,
        use_case,
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """様々な検証状態のメンバーへの抽出E2Eテスト。"""
        # Setup: 検証状態が異なるメンバー
        members = {
            1: ExtractedConferenceMember(
                id=1,
                conference_id=10,
                extracted_name="議員1",
                source_url="https://example.com",
                extracted_at=datetime.now(),
                is_manually_verified=False,  # 未検証
            ),
            2: ExtractedConferenceMember(
                id=2,
                conference_id=10,
                extracted_name="議員2",
                source_url="https://example.com",
                extracted_at=datetime.now(),
                is_manually_verified=True,  # 検証済み
                extracted_role="手動設定の役職",
            ),
            3: ExtractedConferenceMember(
                id=3,
                conference_id=10,
                extracted_name="議員3",
                source_url="https://example.com",
                extracted_at=datetime.now(),
                is_manually_verified=False,  # 未検証
            ),
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_member(entity_id: int):
            return members.get(entity_id)

        mock_conference_member_repo.get_by_id.side_effect = get_member
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        results = []
        for i in range(1, 4):
            extraction_result = ConferenceMemberExtractionResult(
                conference_id=10,
                extracted_name=f"議員{i}",
                source_url="https://example.com",
                extracted_role="AIが抽出した役職",
            )
            result = await use_case.execute(
                entity_id=i,
                extraction_result=extraction_result,
                pipeline_version="v1",
            )
            results.append(result)

        # Assert
        # 1番目: 未検証なので更新される
        assert results[0].updated is True
        assert members[1].extracted_role == "AIが抽出した役職"

        # 2番目: 検証済みなので保護される
        assert results[1].updated is False
        assert results[1].reason == "manually_verified"
        assert members[2].extracted_role == "手動設定の役職"

        # 3番目: 未検証なので更新される
        assert results[2].updated is True
        assert members[3].extracted_role == "AIが抽出した役職"
