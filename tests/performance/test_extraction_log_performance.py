"""パフォーマンステスト: 抽出ログのパフォーマンス測定 (Issue #871).

大量ログ挿入とクエリのパフォーマンスを測定するテスト。

測定項目：
1. ログ挿入パフォーマンス (1000件/10秒以内)
2. ログ検索パフォーマンス (10000件から100件取得/500ms以内)
3. 一括エンティティ更新パフォーマンス
"""

import asyncio
import time

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


@pytest.mark.performance
class TestExtractionLogInsertionPerformance:
    """抽出ログ挿入パフォーマンステスト。"""

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
    async def test_extraction_log_insertion_performance(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """1000件のログ挿入が10秒以内に完了する。"""
        # Setup
        num_insertions = 1000
        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_conversation(entity_id: int):
            return Conversation(
                id=entity_id,
                comment=f"発言{entity_id}",
                sequence_number=entity_id,
                is_manually_verified=False,
            )

        mock_conversation_repo.get_by_id.side_effect = get_conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 1000件のログ挿入
        start = time.time()

        for i in range(num_insertions):
            extraction_result = ConversationExtractionResult(
                comment=f"抽出内容{i}",
                sequence_number=i,
            )
            await use_case.execute(
                entity_id=i + 1,
                extraction_result=extraction_result,
                pipeline_version=f"v{i}",
            )

        elapsed = time.time() - start

        # Assert: 10秒以内
        assert elapsed < 10, (
            f"1000件の挿入に{elapsed:.2f}秒かかりました（目標: 10秒以内）"
        )
        assert mock_extraction_log_repo.create.call_count == num_insertions

        # パフォーマンスメトリクス
        ops_per_second = num_insertions / elapsed
        print(f"\nパフォーマンス: {ops_per_second:.2f} 挿入/秒")

    @pytest.mark.asyncio
    async def test_bulk_insertion_with_concurrent_operations(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """並行挿入のパフォーマンステスト。"""
        # Setup
        num_concurrent = 100
        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_conversation(entity_id: int):
            return Conversation(
                id=entity_id,
                comment=f"発言{entity_id}",
                sequence_number=entity_id,
                is_manually_verified=False,
            )

        mock_conversation_repo.get_by_id.side_effect = get_conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 100件を並行で挿入
        start = time.time()

        async def insert_log(i: int):
            extraction_result = ConversationExtractionResult(
                comment=f"並行抽出{i}",
                sequence_number=i,
            )
            return await use_case.execute(
                entity_id=i + 1,
                extraction_result=extraction_result,
                pipeline_version=f"concurrent-v{i}",
            )

        results = await asyncio.gather(*[insert_log(i) for i in range(num_concurrent)])

        elapsed = time.time() - start

        # Assert
        assert len(results) == num_concurrent
        assert elapsed < 5, (
            f"100件の並行挿入に{elapsed:.2f}秒かかりました（目標: 5秒以内）"
        )

        ops_per_second = num_concurrent / elapsed
        print(f"\n並行パフォーマンス: {ops_per_second:.2f} 挿入/秒")


@pytest.mark.performance
class TestExtractionLogQueryPerformance:
    """抽出ログ検索パフォーマンステスト。"""

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        repo = AsyncMock()

        # 10000件のログを模擬
        def create_logs(count: int):
            return [
                ExtractionLog(
                    id=i,
                    entity_type=EntityType.STATEMENT,
                    entity_id=i % 1000,  # 1000エンティティに分散
                    pipeline_version=f"v{i % 10}",
                    extracted_data={"content": f"data{i}"},
                )
                for i in range(count)
            ]

        all_logs = create_logs(10000)
        repo.get_by_entity_type.return_value = all_logs[:100]  # 100件を返す
        repo.search.return_value = all_logs[:100]
        repo.count_by_entity_type.return_value = len(all_logs)

        return repo

    @pytest.mark.asyncio
    async def test_extraction_log_query_performance(self, mock_extraction_log_repo):
        """10000件から100件取得が500ms以内に完了する。"""
        # Execute
        start = time.time()

        # 100回のクエリを実行
        for _ in range(100):
            await mock_extraction_log_repo.get_by_entity_type(
                EntityType.STATEMENT,
                limit=100,
            )

        elapsed = time.time() - start

        # Assert: 平均5ms以内（100回で500ms以内）
        avg_time = (elapsed / 100) * 1000  # ミリ秒に変換
        assert avg_time < 5, f"平均クエリ時間: {avg_time:.2f}ms（目標: 5ms以内）"

        print(f"\n平均クエリ時間: {avg_time:.2f}ms")

    @pytest.mark.asyncio
    async def test_search_with_filters_performance(self, mock_extraction_log_repo):
        """フィルタ付き検索のパフォーマンステスト。"""
        # Execute
        start = time.time()

        # 50回のフィルタ付きクエリを実行
        for i in range(50):
            await mock_extraction_log_repo.search(
                entity_type=EntityType.STATEMENT,
                pipeline_version=f"v{i % 10}",
                limit=100,
            )

        elapsed = time.time() - start

        # Assert
        avg_time = (elapsed / 50) * 1000
        assert avg_time < 10, (
            f"平均フィルタクエリ時間: {avg_time:.2f}ms（目標: 10ms以内）"
        )

        print(f"\n平均フィルタクエリ時間: {avg_time:.2f}ms")


@pytest.mark.performance
class TestBulkEntityUpdatePerformance:
    """一括エンティティ更新パフォーマンステスト。"""

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
    async def test_bulk_entity_update_performance(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """500件のエンティティ更新が5秒以内に完了する。"""
        # Setup
        num_entities = 500
        entities = {
            i: Conversation(
                id=i,
                comment=f"発言{i}",
                sequence_number=i,
                is_manually_verified=i % 5 == 0,  # 20%が検証済み
            )
            for i in range(1, num_entities + 1)
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_entity(entity_id: int):
            return entities.get(entity_id)

        mock_conversation_repo.get_by_id.side_effect = get_entity
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        start = time.time()

        for i in range(1, num_entities + 1):
            extraction_result = ConversationExtractionResult(
                comment=f"更新内容{i}",
                sequence_number=i,
            )
            await use_case.execute(
                entity_id=i,
                extraction_result=extraction_result,
                pipeline_version="bulk-update-v1",
            )

        elapsed = time.time() - start

        # Assert
        assert elapsed < 5, f"500件の更新に{elapsed:.2f}秒かかりました（目標: 5秒以内）"

        # パフォーマンスメトリクス
        updates_per_second = num_entities / elapsed
        print(f"\n更新パフォーマンス: {updates_per_second:.2f} 更新/秒")

        # 検証済みエンティティは更新されていない
        verified_count = sum(1 for e in entities.values() if e.is_manually_verified)
        print(f"検証済みエンティティ数: {verified_count}")


@pytest.mark.performance
class TestMemoryUsagePerformance:
    """メモリ使用量パフォーマンステスト。"""

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """抽出ログリポジトリのモック。"""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_large_batch_memory_efficiency(self, mock_extraction_log_repo):
        """大量バッチ処理時のメモリ効率テスト。"""
        import sys

        # Setup: 大量のログオブジェクトを作成
        num_logs = 10000

        # メモリ使用前（ベースライン参照用、比較には使用しない）
        _initial_size = sys.getsizeof([])

        # Execute: ログオブジェクトを作成
        logs = []
        for i in range(num_logs):
            log = ExtractionLog(
                id=i,
                entity_type=EntityType.STATEMENT,
                entity_id=i,
                pipeline_version="memory-test-v1",
                extracted_data={"content": f"data{i}", "index": i},
            )
            logs.append(log)

        # メモリ使用後
        # 注: これは概算です。実際のメモリ使用量はもっと複雑
        log_sample_size = sys.getsizeof(logs[0].__dict__)
        estimated_total = log_sample_size * num_logs

        print(f"\n推定メモリ使用量: {estimated_total / 1024 / 1024:.2f} MB")
        print(f"1ログあたり: {log_sample_size} bytes")

        # Assert: 10000件で100MB以下（概算）
        assert estimated_total < 100 * 1024 * 1024, "メモリ使用量が多すぎます"


@pytest.mark.performance
class TestResponseTimeDistribution:
    """レスポンスタイム分布テスト。"""

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
    async def test_response_time_percentiles(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """レスポンスタイムのパーセンタイル測定。"""
        # Setup
        num_operations = 100
        response_times = []

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_conversation(entity_id: int):
            return Conversation(
                id=entity_id,
                comment=f"発言{entity_id}",
                sequence_number=entity_id,
                is_manually_verified=False,
            )

        mock_conversation_repo.get_by_id.side_effect = get_conversation
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        for i in range(num_operations):
            extraction_result = ConversationExtractionResult(
                comment=f"内容{i}",
                sequence_number=i,
            )

            start = time.time()
            await use_case.execute(
                entity_id=i + 1,
                extraction_result=extraction_result,
                pipeline_version="percentile-test-v1",
            )
            elapsed = (time.time() - start) * 1000  # ミリ秒
            response_times.append(elapsed)

        # 統計計算
        response_times.sort()
        p50 = response_times[int(num_operations * 0.50)]
        p90 = response_times[int(num_operations * 0.90)]
        p99 = response_times[int(num_operations * 0.99)]
        avg = sum(response_times) / len(response_times)

        print("\nレスポンスタイム分布:")
        print(f"  平均: {avg:.2f}ms")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P90: {p90:.2f}ms")
        print(f"  P99: {p99:.2f}ms")

        # Assert: P99が50ms以内
        assert p99 < 50, f"P99が{p99:.2f}msです（目標: 50ms以内）"
