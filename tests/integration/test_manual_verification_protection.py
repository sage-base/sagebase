"""統合テスト: 人間修正保護テスト (Issue #871).

全エンティティタイプで人間修正保護（is_manually_verified）が
正しく動作することを検証する統合テスト。

処理フロー：
1. エンティティを手動検証済みにする
2. AI再抽出を実行
3. エンティティが変更されていないことを確認
4. ログは保存されていることを確認
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.conference_member_extraction_result import (
    ConferenceMemberExtractionResult,
)
from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.dtos.extraction_result.parliamentary_group_member_extraction_result import (  # noqa: E501
    ParliamentaryGroupMemberExtractionResult,
)
from src.application.dtos.extraction_result.politician_extraction_result import (
    PoliticianExtractionResult,
)
from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)
from src.application.usecases.update_conversation_from_extraction_usecase import (
    UpdateConversationFromExtractionUseCase,
)
from src.application.usecases.update_extracted_conference_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedConferenceMemberFromExtractionUseCase,
)
from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
)
from src.application.usecases.update_politician_from_extraction_usecase import (
    UpdatePoliticianFromExtractionUseCase,
)
from src.application.usecases.update_speaker_from_extraction_usecase import (
    UpdateSpeakerFromExtractionUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


@pytest.mark.integration
class TestManualVerificationProtectionForStatement:
    """STATEMENT（Conversation）の手動検証保護テスト。"""

    @pytest.fixture
    def mock_conversation_repo(self):
        """会話リポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self, mock_conversation_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateConversationFromExtractionUseCaseのインスタンス。"""
        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_manual_verification_protection_for_statement(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みのSTATEMENTはAI更新から保護される。"""
        # Setup: 手動検証済みのエンティティ
        original_content = "人間が修正した発言内容"
        conversation = Conversation(
            id=1,
            comment=original_content,
            sequence_number=1,
            speaker_name="山田太郎",
            is_manually_verified=True,  # 手動検証済み
            latest_extraction_log_id=100,  # 初回の抽出ログ
        )
        extraction_result = ConversationExtractionResult(
            comment="AIが抽出した新しい内容",  # 異なる内容
            sequence_number=1,
            speaker_name="山田太郎",
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="gemini-2.0-flash-v1",
        )

        # Assert:
        # 1. 更新がスキップされた
        assert result.updated is False
        assert result.reason == "manually_verified"

        # 2. エンティティの内容が変更されていない
        assert conversation.comment == original_content
        assert conversation.latest_extraction_log_id == 100  # 変更なし

        # 3. ログは保存されている（分析用）
        mock_extraction_log_repo.create.assert_called_once()
        assert result.extraction_log_id == 200

        # 4. リポジトリのupdateは呼ばれていない
        mock_conversation_repo.update.assert_not_called()
        mock_session_adapter.commit.assert_not_called()


@pytest.mark.integration
class TestManualVerificationProtectionForPolitician:
    """POLITICIANの手動検証保護テスト。"""

    @pytest.fixture
    def mock_politician_repo(self):
        """政治家リポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdatePoliticianFromExtractionUseCaseのインスタンス。"""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_manual_verification_protection_for_politician(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みのPOLITICIANはAI更新から保護される。"""
        # Setup
        original_district = "人間が修正した選挙区"
        politician = Politician(
            id=1,
            name="山田太郎",
            district=original_district,
            is_manually_verified=True,
            latest_extraction_log_id=100,
        )
        extraction_result = PoliticianExtractionResult(
            name="山田太郎",
            district="AIが抽出した選挙区",
            confidence_score=0.95,
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_politician_repo.get_by_id.return_value = politician
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="gemini-2.0-flash-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"
        assert politician.district == original_district
        mock_extraction_log_repo.create.assert_called_once()
        mock_politician_repo.update.assert_not_called()


@pytest.mark.integration
class TestManualVerificationProtectionForSpeaker:
    """SPEAKERの手動検証保護テスト。"""

    @pytest.fixture
    def mock_speaker_repo(self):
        """発言者リポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self, mock_speaker_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateSpeakerFromExtractionUseCaseのインスタンス。"""
        return UpdateSpeakerFromExtractionUseCase(
            speaker_repo=mock_speaker_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_manual_verification_protection_for_speaker(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みのSPEAKERはAI更新から保護される。"""
        # Setup
        original_politician_id = 999  # 人間が手動で紐付けた政治家ID
        speaker = Speaker(
            id=1,
            name="山田太郎",
            is_politician=True,
            politician_id=original_politician_id,
            is_manually_verified=True,
            latest_extraction_log_id=100,
        )
        extraction_result = SpeakerExtractionResult(
            name="山田太郎",
            is_politician=True,
            politician_id=888,  # AIが推定した異なる政治家ID
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.SPEAKER,
            entity_id=1,
            pipeline_version="speaker-matching-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_speaker_repo.get_by_id.return_value = speaker
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="speaker-matching-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"
        assert speaker.politician_id == original_politician_id
        mock_extraction_log_repo.create.assert_called_once()
        mock_speaker_repo.update.assert_not_called()


@pytest.mark.integration
class TestManualVerificationProtectionForConferenceMember:
    """CONFERENCE_MEMBERの手動検証保護テスト。"""

    @pytest.fixture
    def mock_conference_member_repo(self):
        """会議体メンバーリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        adapter = AsyncMock()
        return adapter

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
    async def test_manual_verification_protection_for_conference_member(
        self,
        use_case,
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みのCONFERENCE_MEMBERはAI更新から保護される。"""
        # Setup
        original_role = "人間が修正した役職"
        member = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_role=original_role,
            extracted_at=datetime.now(),
            is_manually_verified=True,
            latest_extraction_log_id=100,
        )
        extraction_result = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_role="AIが抽出した役職",
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            pipeline_version="member-extraction-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conference_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="member-extraction-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"
        assert member.extracted_role == original_role
        mock_extraction_log_repo.create.assert_called_once()
        mock_conference_member_repo.update.assert_not_called()


@pytest.mark.integration
class TestManualVerificationProtectionForParliamentaryGroupMember:
    """PARLIAMENTARY_GROUP_MEMBERの手動検証保護テスト。"""

    @pytest.fixture
    def mock_parliamentary_group_member_repo(self):
        """議員団メンバーリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        adapter = AsyncMock()
        return adapter

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
    async def test_manual_verification_protection_for_parliamentary_group_member(
        self,
        use_case,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みのPARLIAMENTARY_GROUP_MEMBERはAI更新から保護される。"""
        # Setup
        original_district = "人間が修正した選挙区"
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_district=original_district,
            extracted_at=datetime.now(),
            is_manually_verified=True,
            latest_extraction_log_id=100,
        )
        extraction_result = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_district="AIが抽出した選挙区",
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="group-member-extraction-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_parliamentary_group_member_repo.get_by_id.return_value = member
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="group-member-extraction-v1",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"
        assert member.extracted_district == original_district
        mock_extraction_log_repo.create.assert_called_once()
        mock_parliamentary_group_member_repo.update.assert_not_called()


@pytest.mark.integration
class TestManualVerificationLifecycle:
    """手動検証ライフサイクルテスト。"""

    @pytest.fixture
    def mock_conversation_repo(self):
        """会話リポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self, mock_conversation_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateConversationFromExtractionUseCaseのインスタンス。"""
        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_allowed_before_manual_verification(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証前はAI更新が許可される。"""
        # Setup: 未検証のエンティティ
        conversation = Conversation(
            id=1,
            comment="元の内容",
            sequence_number=1,
            is_manually_verified=False,
        )
        extraction_result = ConversationExtractionResult(
            comment="AI抽出内容",
            sequence_number=1,
        )
        extraction_log = ExtractionLog(
            id=300,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1",
        )

        # Assert: 更新が行われた
        assert result.updated is True
        assert conversation.comment == "AI抽出内容"
        mock_conversation_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_logs_accumulated_during_protection(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """保護中も複数の抽出ログが蓄積される。"""
        # Setup: 手動検証済みエンティティ
        conversation = Conversation(
            id=1,
            comment="人間が修正した内容",
            sequence_number=1,
            is_manually_verified=True,
        )

        mock_conversation_repo.get_by_id.return_value = conversation

        log_ids = []
        # 3回の抽出を実行
        for i in range(3):
            extraction_result = ConversationExtractionResult(
                comment=f"AI抽出内容{i}",
                sequence_number=1,
            )
            extraction_log = ExtractionLog(
                id=400 + i,
                entity_type=EntityType.STATEMENT,
                entity_id=1,
                pipeline_version=f"v{i}",
                extracted_data=extraction_result.to_dict(),
            )
            mock_extraction_log_repo.create.return_value = extraction_log

            result = await use_case.execute(
                entity_id=1,
                extraction_result=extraction_result,
                pipeline_version=f"v{i}",
            )

            log_ids.append(result.extraction_log_id)
            assert result.updated is False
            assert result.reason == "manually_verified"

        # Assert: 3つのログが作成された
        assert mock_extraction_log_repo.create.call_count == 3
        assert log_ids == [400, 401, 402]

        # エンティティは一度も更新されていない
        mock_conversation_repo.update.assert_not_called()
