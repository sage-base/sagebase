"""統合テスト: 並行更新テスト (Issue #871).

並行した抽出更新でもデータ整合性が保たれることを検証する統合テスト。

処理フロー：
1. 複数の並行抽出を実行
2. 全てのログが保存されていることを確認
3. データ整合性が保たれていることを確認
"""

import asyncio

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
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
from src.application.usecases.update_politician_from_extraction_usecase import (
    UpdatePoliticianFromExtractionUseCase,
)
from src.application.usecases.update_speaker_from_extraction_usecase import (
    UpdateSpeakerFromExtractionUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


@pytest.mark.integration
class TestConcurrentExtractionUpdates:
    """並行抽出更新テスト。"""

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
    async def test_concurrent_extraction_updates(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """並行した抽出更新でもデータ整合性が保たれる。"""
        # Setup: 同一エンティティに対する並行抽出
        conversation = Conversation(
            id=1,
            comment="元の発言内容",
            sequence_number=1,
            is_manually_verified=False,
        )

        # 各呼び出しで異なるログIDを返すようにモック
        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 10並列で抽出を実行
        num_concurrent = 10

        async def execute_extraction(index: int):
            extraction_result = ConversationExtractionResult(
                comment=f"抽出内容_{index}",
                sequence_number=1,
            )
            return await use_case.execute(
                entity_id=1,
                extraction_result=extraction_result,
                pipeline_version=f"v{index}",
            )

        results = await asyncio.gather(
            *[execute_extraction(i) for i in range(num_concurrent)]
        )

        # Assert:
        # 1. 全ての抽出結果が取得された
        assert len(results) == num_concurrent

        # 2. ログが全て保存された
        assert mock_extraction_log_repo.create.call_count == num_concurrent

        # 3. 全ての結果がログIDを持つ
        log_ids = [r.extraction_log_id for r in results]
        assert all(log_id is not None for log_id in log_ids)

        # 4. ログIDはユニーク（重複なし）
        assert len(set(log_ids)) == num_concurrent

    @pytest.mark.asyncio
    async def test_concurrent_updates_with_different_entities(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """異なるエンティティへの並行更新が正しく動作する。"""
        # Setup: 異なるエンティティに対する並行抽出
        conversations = {
            i: Conversation(
                id=i,
                comment=f"発言_{i}",
                sequence_number=i,
                is_manually_verified=False,
            )
            for i in range(1, 6)  # 5つのエンティティ
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

        # Execute: 各エンティティに対して並行で抽出
        async def execute_extraction(entity_id: int):
            extraction_result = ConversationExtractionResult(
                comment=f"新しい発言_{entity_id}",
                sequence_number=entity_id,
            )
            return await use_case.execute(
                entity_id=entity_id,
                extraction_result=extraction_result,
                pipeline_version="v1",
            )

        results = await asyncio.gather(*[execute_extraction(i) for i in range(1, 6)])

        # Assert:
        assert len(results) == 5
        assert all(r.updated is True for r in results)
        assert mock_extraction_log_repo.create.call_count == 5

        # 各エンティティが正しく更新された
        for i in range(1, 6):
            assert conversations[i].comment == f"新しい発言_{i}"


@pytest.mark.integration
class TestConcurrentUpdatesWithDifferentEntityTypes:
    """異なるエンティティタイプへの並行更新テスト。"""

    @pytest.fixture
    def mock_conversation_repo(self):
        """会話リポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_politician_repo(self):
        """政治家リポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_speaker_repo(self):
        """発言者リポジトリのモック。"""
        return AsyncMock()

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック（共有）。"""
        return AsyncMock()

    @pytest.fixture
    def mock_session_adapter(self):
        """セッションアダプターのモック。"""
        return AsyncMock()

    @pytest.fixture
    def conversation_use_case(
        self, mock_conversation_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """会話更新UseCaseのインスタンス。"""
        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.fixture
    def politician_use_case(
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """政治家更新UseCaseのインスタンス。"""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.fixture
    def speaker_use_case(
        self, mock_speaker_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """発言者更新UseCaseのインスタンス。"""
        return UpdateSpeakerFromExtractionUseCase(
            speaker_repo=mock_speaker_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_concurrent_updates_across_entity_types(
        self,
        conversation_use_case,
        politician_use_case,
        speaker_use_case,
        mock_conversation_repo,
        mock_politician_repo,
        mock_speaker_repo,
        mock_extraction_log_repo,
    ):
        """異なるエンティティタイプへの並行更新が正しく動作する。"""
        # Setup
        conversation = Conversation(
            id=1,
            comment="発言",
            sequence_number=1,
            is_manually_verified=False,
        )
        politician = Politician(
            id=1,
            name="山田太郎",
            is_manually_verified=False,
        )
        speaker = Speaker(
            id=1,
            name="山田太郎",
            is_politician=False,
            is_manually_verified=False,
        )

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_politician_repo.get_by_id.return_value = politician
        mock_speaker_repo.get_by_id.return_value = speaker
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 3種類のエンティティタイプに対して並行で更新
        async def update_conversation():
            return await conversation_use_case.execute(
                entity_id=1,
                extraction_result=ConversationExtractionResult(
                    comment="新しい発言",
                    sequence_number=1,
                ),
                pipeline_version="v1",
            )

        async def update_politician():
            return await politician_use_case.execute(
                entity_id=1,
                extraction_result=PoliticianExtractionResult(
                    name="山田太郎",
                    district="東京1区",
                ),
                pipeline_version="v1",
            )

        async def update_speaker():
            return await speaker_use_case.execute(
                entity_id=1,
                extraction_result=SpeakerExtractionResult(
                    name="山田太郎",
                    is_politician=True,
                    politician_id=100,
                ),
                pipeline_version="v1",
            )

        results = await asyncio.gather(
            update_conversation(),
            update_politician(),
            update_speaker(),
        )

        # Assert:
        assert len(results) == 3
        assert all(r.updated is True for r in results)

        # 各エンティティタイプのログが作成された
        assert mock_extraction_log_repo.create.call_count == 3

        # ログのエンティティタイプを確認
        created_logs = [
            call[0][0] for call in mock_extraction_log_repo.create.call_args_list
        ]
        entity_types = {log.entity_type for log in created_logs}
        assert EntityType.STATEMENT in entity_types
        assert EntityType.POLITICIAN in entity_types
        assert EntityType.SPEAKER in entity_types


@pytest.mark.integration
class TestConcurrentUpdatesRaceCondition:
    """レース条件テスト。"""

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
    async def test_race_condition_with_manual_verification(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証フラグ変更時のレース条件テスト。

        シナリオ：
        1. 最初は未検証状態
        2. 並行してAI更新と手動検証が発生
        3. 手動検証後のAI更新は保護される
        """
        # Setup: 状態が途中で変わるエンティティをシミュレート
        call_count = [0]

        def get_conversation(entity_id: int):
            call_count[0] += 1
            # 3回目以降の呼び出しでは手動検証済みになっている
            is_verified = call_count[0] > 2
            return Conversation(
                id=1,
                comment="発言内容",
                sequence_number=1,
                is_manually_verified=is_verified,
            )

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        mock_conversation_repo.get_by_id.side_effect = get_conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 5回の並行抽出（途中で手動検証が入る）
        async def execute_extraction(index: int):
            # 実際のシステムでは、これらは時間差で実行される
            extraction_result = ConversationExtractionResult(
                comment=f"抽出_{index}",
                sequence_number=1,
            )
            return await use_case.execute(
                entity_id=1,
                extraction_result=extraction_result,
                pipeline_version=f"v{index}",
            )

        results = await asyncio.gather(*[execute_extraction(i) for i in range(5)])

        # Assert:
        # 全てのログが保存されている
        assert mock_extraction_log_repo.create.call_count == 5

        # 一部は更新され、一部は保護された
        updated_count = sum(1 for r in results if r.updated)
        protected_count = sum(1 for r in results if r.reason == "manually_verified")

        # 少なくとも一部は更新され、一部は保護されている
        assert updated_count > 0
        assert protected_count > 0
        assert updated_count + protected_count == 5


@pytest.mark.integration
class TestBulkExtraction:
    """一括抽出テスト。"""

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
    async def test_bulk_extraction_with_mixed_verification_status(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """一括抽出時に検証状態が混在するケース。"""
        # Setup: 検証状態が混在するエンティティ
        conversations = {
            1: Conversation(
                id=1, comment="発言1", sequence_number=1, is_manually_verified=False
            ),
            2: Conversation(
                id=2, comment="発言2", sequence_number=2, is_manually_verified=True
            ),  # 検証済み
            3: Conversation(
                id=3, comment="発言3", sequence_number=3, is_manually_verified=False
            ),
            4: Conversation(
                id=4, comment="発言4", sequence_number=4, is_manually_verified=True
            ),  # 検証済み
            5: Conversation(
                id=5, comment="発言5", sequence_number=5, is_manually_verified=False
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

        # Execute: 全エンティティに対して並行で抽出
        async def execute_extraction(entity_id: int):
            extraction_result = ConversationExtractionResult(
                comment=f"新しい発言_{entity_id}",
                sequence_number=entity_id,
            )
            return await use_case.execute(
                entity_id=entity_id,
                extraction_result=extraction_result,
                pipeline_version="v1",
            )

        results = await asyncio.gather(*[execute_extraction(i) for i in range(1, 6)])

        # Assert:
        # 全てのログが保存された
        assert mock_extraction_log_repo.create.call_count == 5

        # 検証結果の確認
        result_dict = {i + 1: results[i] for i in range(5)}

        # 未検証のエンティティ（1, 3, 5）は更新された
        assert result_dict[1].updated is True
        assert result_dict[3].updated is True
        assert result_dict[5].updated is True

        # 検証済みのエンティティ（2, 4）は保護された
        assert result_dict[2].updated is False
        assert result_dict[2].reason == "manually_verified"
        assert result_dict[4].updated is False
        assert result_dict[4].reason == "manually_verified"

        # 更新されたエンティティの内容を確認
        assert conversations[1].comment == "新しい発言_1"
        assert conversations[3].comment == "新しい発言_3"
        assert conversations[5].comment == "新しい発言_5"

        # 保護されたエンティティの内容は変更なし
        assert conversations[2].comment == "発言2"
        assert conversations[4].comment == "発言4"
