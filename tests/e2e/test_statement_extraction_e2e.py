"""E2Eテスト: Statement（Conversation）抽出の完全なフロー (Issue #871).

議事録からの発言抽出・更新・手動修正保護の完全なE2Eフローをテスト。

フロー：
1. 議事録処理実行
2. ログ確認
3. 手動修正
4. 再処理
5. 手動修正が保護されていることを確認
"""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.usecases.update_conversation_from_extraction_usecase import (
    UpdateConversationFromExtractionUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.extraction_log import EntityType, ExtractionLog


@pytest.mark.e2e
class TestStatementExtractionFullFlow:
    """Statement抽出の完全なE2Eフローテスト。"""

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
    async def test_statement_extraction_full_flow(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """Statement抽出の完全なE2Eフロー。

        1. 議事録処理実行
        2. ログ確認
        3. 手動修正
        4. 再処理
        5. 手動修正が保護されていることを確認
        """
        # ============================================
        # Step 1: 初回の議事録処理実行
        # ============================================
        conversation = Conversation(
            id=1,
            comment="AI抽出された発言内容",
            sequence_number=1,
            speaker_name="山田太郎",
            minutes_id=100,
            is_manually_verified=False,
        )

        extraction_result_1 = ConversationExtractionResult(
            comment="AI抽出された発言内容",
            sequence_number=1,
            speaker_name="山田太郎",
            minutes_id=100,
        )
        extraction_log_1 = ExtractionLog(
            id=1000,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data=extraction_result_1.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log_1

        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="gemini-2.0-flash-v1",
        )

        # Step 1 検証
        assert result_1.updated is True
        assert result_1.extraction_log_id == 1000
        assert conversation.comment == "AI抽出された発言内容"
        assert conversation.latest_extraction_log_id == 1000

        # ============================================
        # Step 2: ログ確認
        # ============================================
        mock_extraction_log_repo.get_by_entity.return_value = [extraction_log_1]

        # ログが存在することを確認（モックの呼び出し確認）
        logs = await mock_extraction_log_repo.get_by_entity(EntityType.STATEMENT, 1)
        assert len(logs) == 1
        assert logs[0].id == 1000

        # ============================================
        # Step 3: 手動修正
        # ============================================
        # ユーザーが手動で発言内容を修正し、検証済みにマーク
        conversation.comment = "手動で修正した発言内容"
        conversation.mark_as_manually_verified()

        assert conversation.is_manually_verified is True
        assert conversation.comment == "手動で修正した発言内容"

        # ============================================
        # Step 4: 再処理
        # ============================================
        extraction_result_2 = ConversationExtractionResult(
            comment="再抽出された発言内容（異なる内容）",
            sequence_number=1,
            speaker_name="山田太郎",
            minutes_id=100,
        )
        extraction_log_2 = ExtractionLog(
            id=1001,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="gemini-2.0-flash-v2",
            extracted_data=extraction_result_2.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log_2

        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="gemini-2.0-flash-v2",
        )

        # ============================================
        # Step 5: 手動修正が保護されていることを確認
        # ============================================
        assert result_2.updated is False
        assert result_2.reason == "manually_verified"
        assert result_2.extraction_log_id == 1001  # ログは保存されている

        # 手動修正した内容が保持されている
        assert conversation.comment == "手動で修正した発言内容"
        assert conversation.is_manually_verified is True

        # 抽出ログは2つ作成されている
        assert mock_extraction_log_repo.create.call_count == 2


@pytest.mark.e2e
class TestStatementExtractionEdgeCases:
    """Statement抽出のエッジケースE2Eテスト。"""

    @pytest.fixture
    def mock_conversation_repo(self):
        """会話リポジトリのモック。"""
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
        self, mock_conversation_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateConversationFromExtractionUseCaseのインスタンス。"""
        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_multiple_statements_in_same_minutes(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """同一議事録内の複数発言の抽出・更新フロー。"""
        # Setup: 同一議事録の3つの発言
        conversations = {
            1: Conversation(
                id=1,
                comment="発言1",
                sequence_number=1,
                minutes_id=100,
                is_manually_verified=False,
            ),
            2: Conversation(
                id=2,
                comment="発言2",
                sequence_number=2,
                minutes_id=100,
                is_manually_verified=False,
            ),
            3: Conversation(
                id=3,
                comment="発言3",
                sequence_number=3,
                minutes_id=100,
                is_manually_verified=False,
            ),
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_conversation(entity_id: int):
            return conversations.get(entity_id)

        mock_conversation_repo.get_by_id.side_effect = get_conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 3つの発言を順番に更新
        results = []
        for i in range(1, 4):
            extraction_result = ConversationExtractionResult(
                comment=f"更新された発言{i}",
                sequence_number=i,
                minutes_id=100,
            )
            result = await use_case.execute(
                entity_id=i,
                extraction_result=extraction_result,
                pipeline_version="v1",
            )
            results.append(result)

        # Assert: 全て更新された
        assert all(r.updated is True for r in results)
        assert mock_extraction_log_repo.create.call_count == 3

        # 各発言が正しく更新された
        assert conversations[1].comment == "更新された発言1"
        assert conversations[2].comment == "更新された発言2"
        assert conversations[3].comment == "更新された発言3"

    @pytest.mark.asyncio
    async def test_speaker_linkage_preservation(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """発言者紐付けが保持されるE2Eフロー。"""
        # Setup: 発言者IDが既に設定されている発言
        conversation = Conversation(
            id=1,
            comment="元の発言",
            sequence_number=1,
            speaker_id=999,  # 既存の発言者紐付け
            speaker_name="山田太郎",
            is_manually_verified=False,
        )

        extraction_result = ConversationExtractionResult(
            comment="更新された発言",
            sequence_number=1,
            speaker_name="山田太郎",
            speaker_id=999,  # 同じ発言者ID
        )
        extraction_log = ExtractionLog(
            id=100,
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

        # Assert: 発言者紐付けが保持されている
        assert result.updated is True
        assert conversation.speaker_id == 999
        assert conversation.comment == "更新された発言"


@pytest.mark.e2e
class TestStatementExtractionWithHistory:
    """抽出履歴を伴うStatement抽出テスト。"""

    @pytest.fixture
    def mock_conversation_repo(self):
        """会話リポジトリのモック。"""
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
        self, mock_conversation_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateConversationFromExtractionUseCaseのインスタンス。"""
        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_extraction_history_accumulation(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """抽出履歴が正しく蓄積されるE2Eテスト。"""
        # Setup
        conversation = Conversation(
            id=1,
            comment="元の発言",
            sequence_number=1,
            is_manually_verified=False,
        )

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 5回の抽出処理を実行
        versions = ["v1", "v1.1", "v2", "v2.1", "v3"]
        results = []

        for version in versions:
            extraction_result = ConversationExtractionResult(
                comment=f"発言_{version}",
                sequence_number=1,
            )
            result = await use_case.execute(
                entity_id=1,
                extraction_result=extraction_result,
                pipeline_version=version,
            )
            results.append(result)

        # Assert: 5回の抽出ログが蓄積された
        assert mock_extraction_log_repo.create.call_count == 5
        assert all(r.updated is True for r in results)

        # ログIDは連番で割り当てられた
        log_ids = [r.extraction_log_id for r in results]
        assert log_ids == [1, 2, 3, 4, 5]

        # 最後のログIDがエンティティに設定されている
        assert conversation.latest_extraction_log_id == 5

    @pytest.mark.asyncio
    async def test_pipeline_version_tracking(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """パイプラインバージョンが正しく追跡されるE2Eテスト。"""
        # Setup
        conversation = Conversation(
            id=1,
            comment="発言",
            sequence_number=1,
            is_manually_verified=False,
        )

        created_logs = []

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log.id = len(created_logs) + 1
            created_logs.append(log)
            return log

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 異なるパイプラインバージョンで抽出
        pipeline_versions = [
            "gemini-1.5-flash-v1",
            "gemini-2.0-flash-v1",
            "gemini-2.0-flash-v2",
        ]

        for version in pipeline_versions:
            extraction_result = ConversationExtractionResult(
                comment=f"発言_{version}",
                sequence_number=1,
            )
            await use_case.execute(
                entity_id=1,
                extraction_result=extraction_result,
                pipeline_version=version,
            )

        # Assert: 各ログに正しいバージョンが記録されている
        assert len(created_logs) == 3
        recorded_versions = [log.pipeline_version for log in created_logs]
        assert recorded_versions == pipeline_versions
