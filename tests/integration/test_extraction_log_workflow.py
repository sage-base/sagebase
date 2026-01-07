"""統合テスト: 全エンティティタイプの抽出ログワークフロー (Issue #871).

全エンティティタイプ（STATEMENT, POLITICIAN, SPEAKER,
CONFERENCE_MEMBER, PARLIAMENTARY_GROUP_MEMBER）
で抽出ログワークフローが正しく動作することを検証する統合テスト。

処理フロー：
1. 抽出実行
2. ログが保存されていることを確認
3. エンティティが更新されていることを確認
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
class TestExtractionLogWorkflowForStatement:
    """STATEMENT（Conversation）エンティティの抽出ログワークフローテスト。"""

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
    async def test_extraction_log_workflow_for_statement(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """STATEMENT抽出ログワークフローが正しく動作する。"""
        # Setup: エンティティと抽出ログを準備
        conversation = Conversation(
            id=1,
            comment="元の発言内容",
            sequence_number=1,
            speaker_name="山田太郎",
            is_manually_verified=False,
        )
        extraction_result = ConversationExtractionResult(
            comment="新しい発言内容",
            sequence_number=1,
            speaker_name="山田太郎",
            speaker_id=100,
        )
        extraction_log = ExtractionLog(
            id=300,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute: 抽出実行
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="gemini-2.0-flash-v1",
        )

        # Assert:
        # 1. ログが保存されている
        mock_extraction_log_repo.create.assert_called_once()
        created_log = mock_extraction_log_repo.create.call_args[0][0]
        assert created_log.entity_type == EntityType.STATEMENT
        assert created_log.entity_id == 1
        assert created_log.pipeline_version == "gemini-2.0-flash-v1"

        # 2. エンティティが更新されている
        assert result.updated is True
        assert result.extraction_log_id == 300
        assert conversation.comment == "新しい発言内容"
        assert conversation.latest_extraction_log_id == 300

        # 3. コミットが呼ばれている
        mock_session_adapter.commit.assert_called_once()


@pytest.mark.integration
class TestExtractionLogWorkflowForPolitician:
    """POLITICIANエンティティの抽出ログワークフローテスト。"""

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
    async def test_extraction_log_workflow_for_politician(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """POLITICIAN抽出ログワークフローが正しく動作する。"""
        # Setup
        politician = Politician(
            id=1,
            name="山田太郎",
            is_manually_verified=False,
        )
        extraction_result = PoliticianExtractionResult(
            name="山田太郎",
            furigana="やまだたろう",
            district="東京1区",
            confidence_score=0.95,
        )
        extraction_log = ExtractionLog(
            id=400,
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
        # 1. ログが保存されている
        mock_extraction_log_repo.create.assert_called_once()
        created_log = mock_extraction_log_repo.create.call_args[0][0]
        assert created_log.entity_type == EntityType.POLITICIAN
        assert created_log.entity_id == 1

        # 2. エンティティが更新されている
        assert result.updated is True
        assert result.extraction_log_id == 400
        assert politician.furigana == "やまだたろう"
        assert politician.district == "東京1区"
        assert politician.latest_extraction_log_id == 400


@pytest.mark.integration
class TestExtractionLogWorkflowForSpeaker:
    """SPEAKERエンティティの抽出ログワークフローテスト。"""

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
    async def test_extraction_log_workflow_for_speaker(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """SPEAKER抽出ログワークフローが正しく動作する。"""
        # Setup
        speaker = Speaker(
            id=1,
            name="山田太郎",
            is_politician=False,
            is_manually_verified=False,
        )
        extraction_result = SpeakerExtractionResult(
            name="山田太郎",
            type="議員",
            political_party_name="自民党",
            is_politician=True,
            politician_id=100,
        )
        extraction_log = ExtractionLog(
            id=500,
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
        mock_extraction_log_repo.create.assert_called_once()
        created_log = mock_extraction_log_repo.create.call_args[0][0]
        assert created_log.entity_type == EntityType.SPEAKER
        assert created_log.entity_id == 1

        assert result.updated is True
        assert result.extraction_log_id == 500
        assert speaker.is_politician is True
        assert speaker.politician_id == 100
        assert speaker.latest_extraction_log_id == 500


@pytest.mark.integration
class TestExtractionLogWorkflowForConferenceMember:
    """CONFERENCE_MEMBERエンティティの抽出ログワークフローテスト。"""

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
    async def test_extraction_log_workflow_for_conference_member(
        self,
        use_case,
        mock_conference_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """CONFERENCE_MEMBER抽出ログワークフローが正しく動作する。"""
        # Setup
        member = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_at=datetime.now(),
            is_manually_verified=False,
        )
        extraction_result = ConferenceMemberExtractionResult(
            conference_id=10,
            extracted_name="鈴木一郎",
            source_url="https://example.com/members",
            extracted_role="議長",
            extracted_party_name="自民党",
            confidence_score=0.9,
        )
        extraction_log = ExtractionLog(
            id=600,
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
        mock_extraction_log_repo.create.assert_called_once()
        created_log = mock_extraction_log_repo.create.call_args[0][0]
        assert created_log.entity_type == EntityType.CONFERENCE_MEMBER
        assert created_log.entity_id == 1

        assert result.updated is True
        assert result.extraction_log_id == 600
        assert member.extracted_role == "議長"
        assert member.extracted_party_name == "自民党"
        assert member.latest_extraction_log_id == 600


@pytest.mark.integration
class TestExtractionLogWorkflowForParliamentaryGroupMember:
    """PARLIAMENTARY_GROUP_MEMBERエンティティの抽出ログワークフローテスト。"""

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
    async def test_extraction_log_workflow_for_parliamentary_group_member(
        self,
        use_case,
        mock_parliamentary_group_member_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """PARLIAMENTARY_GROUP_MEMBER抽出ログワークフローが正しく動作する。"""
        # Setup
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_at=datetime.now(),
            is_manually_verified=False,
        )
        extraction_result = ParliamentaryGroupMemberExtractionResult(
            parliamentary_group_id=10,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_district="大阪1区",
            confidence_score=0.85,
        )
        extraction_log = ExtractionLog(
            id=700,
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
        mock_extraction_log_repo.create.assert_called_once()
        created_log = mock_extraction_log_repo.create.call_args[0][0]
        assert created_log.entity_type == EntityType.PARLIAMENTARY_GROUP_MEMBER
        assert created_log.entity_id == 1

        assert result.updated is True
        assert result.extraction_log_id == 700
        assert member.extracted_role == "団長"
        assert member.extracted_district == "大阪1区"
        assert member.latest_extraction_log_id == 700


@pytest.mark.integration
class TestExtractionLogWorkflowEdgeCases:
    """抽出ログワークフローのエッジケーステスト。"""

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
    async def test_extraction_log_saved_even_when_entity_not_found(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """エンティティが存在しない場合でも抽出ログは保存される。"""
        # Setup
        extraction_result = ConversationExtractionResult(
            comment="テスト発言",
            sequence_number=1,
        )
        extraction_log = ExtractionLog(
            id=800,
            entity_type=EntityType.STATEMENT,
            entity_id=999,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = None  # エンティティが存在しない
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=999,
            extraction_result=extraction_result,
            pipeline_version="gemini-2.0-flash-v1",
        )

        # Assert: ログは保存されるが、更新は行われない
        mock_extraction_log_repo.create.assert_called_once()
        assert result.updated is False
        assert result.reason == "entity_not_found"
        assert result.extraction_log_id == 800

    @pytest.mark.asyncio
    async def test_multiple_extraction_logs_for_same_entity(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """同一エンティティに対して複数回の抽出ログが保存できる。"""
        # Setup
        conversation = Conversation(
            id=1,
            comment="元の発言内容",
            sequence_number=1,
            is_manually_verified=False,
        )

        # 1回目の抽出
        extraction_result_1 = ConversationExtractionResult(
            comment="1回目の抽出結果",
            sequence_number=1,
        )
        extraction_log_1 = ExtractionLog(
            id=900,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="v1",
            extracted_data=extraction_result_1.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log_1

        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="v1",
        )

        assert result_1.updated is True
        assert result_1.extraction_log_id == 900

        # 2回目の抽出
        extraction_result_2 = ConversationExtractionResult(
            comment="2回目の抽出結果",
            sequence_number=1,
        )
        extraction_log_2 = ExtractionLog(
            id=901,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="v2",
            extracted_data=extraction_result_2.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log_2

        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="v2",
        )

        assert result_2.updated is True
        assert result_2.extraction_log_id == 901

        # 2回の抽出ログが作成されたことを確認
        assert mock_extraction_log_repo.create.call_count == 2
