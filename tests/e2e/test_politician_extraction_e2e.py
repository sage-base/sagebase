"""E2Eテスト: Politician抽出の完全なフロー (Issue #871).

政治家情報のスクレイピング・更新・手動修正保護の完全なE2Eフローをテスト。

フロー：
1. 政党メンバーページからの抽出
2. ログ確認
3. 手動修正
4. 再抽出
5. 手動修正が保護されていることを確認
"""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.politician_extraction_result import (
    PoliticianExtractionResult,
)
from src.application.usecases.update_politician_from_extraction_usecase import (
    UpdatePoliticianFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.politician import Politician


@pytest.mark.e2e
class TestPoliticianExtractionFullFlow:
    """Politician抽出の完全なE2Eフローテスト。"""

    @pytest.fixture
    def mock_politician_repo(self):
        """政治家リポジトリのモック。"""
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
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdatePoliticianFromExtractionUseCaseのインスタンス。"""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_politician_extraction_full_flow(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """Politician抽出の完全なE2Eフロー。"""
        # ============================================
        # Step 1: 政党ページからの初回抽出
        # ============================================
        politician = Politician(
            id=1,
            name="山田太郎",
            furigana="やまだたろう",
            district="東京1区",
            is_manually_verified=False,
        )

        extraction_result_1 = PoliticianExtractionResult(
            name="山田太郎",
            furigana="やまだたろう",
            district="東京1区",
            political_party_id=1,
            profile_page_url="https://example.com/yamada",
            confidence_score=0.95,
        )
        extraction_log_1 = ExtractionLog(
            id=2000,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="party-scraping-v1",
            extracted_data=extraction_result_1.to_dict(),
        )

        mock_politician_repo.get_by_id.return_value = politician
        mock_extraction_log_repo.create.return_value = extraction_log_1

        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="party-scraping-v1",
        )

        # Step 1 検証
        assert result_1.updated is True
        assert result_1.extraction_log_id == 2000
        assert politician.profile_page_url == "https://example.com/yamada"
        assert politician.political_party_id == 1

        # ============================================
        # Step 2: ログ確認
        # ============================================
        mock_extraction_log_repo.get_by_entity.return_value = [extraction_log_1]
        logs = await mock_extraction_log_repo.get_by_entity(EntityType.POLITICIAN, 1)
        assert len(logs) == 1

        # ============================================
        # Step 3: 手動修正
        # ============================================
        politician.district = "手動修正: 東京2区"  # 選挙区を修正
        politician.mark_as_manually_verified()

        assert politician.is_manually_verified is True

        # ============================================
        # Step 4: 再抽出
        # ============================================
        extraction_result_2 = PoliticianExtractionResult(
            name="山田太郎",
            furigana="やまだたろう",
            district="東京3区",  # AIは異なる選挙区を抽出
            confidence_score=0.90,
        )
        extraction_log_2 = ExtractionLog(
            id=2001,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="party-scraping-v2",
            extracted_data=extraction_result_2.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log_2

        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="party-scraping-v2",
        )

        # ============================================
        # Step 5: 手動修正が保護されていることを確認
        # ============================================
        assert result_2.updated is False
        assert result_2.reason == "manually_verified"
        assert politician.district == "手動修正: 東京2区"  # 手動修正が保持

        # ログは2つ作成されている
        assert mock_extraction_log_repo.create.call_count == 2


@pytest.mark.e2e
class TestPoliticianMatchingFlow:
    """Politician マッチングフローのE2Eテスト。"""

    @pytest.fixture
    def mock_politician_repo(self):
        """政治家リポジトリのモック。"""
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
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdatePoliticianFromExtractionUseCaseのインスタンス。"""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_politician_matching_log_only(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """マッチング処理ではログのみ記録される（エンティティ更新なし）。"""
        # Setup: nameがNoneの場合はマッチング処理
        politician = Politician(
            id=1,
            name="山田太郎",
            is_manually_verified=False,
        )

        # マッチング処理の結果（nameはNone）
        extraction_result = PoliticianExtractionResult(
            name=None,  # nameがNoneはマッチング処理
            matched_from_speaker_id=100,
            match_confidence=0.95,
            match_reason="完全一致",
        )
        extraction_log = ExtractionLog(
            id=3000,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="speaker-matching-v1",
            extracted_data=extraction_result.to_dict(),
        )

        mock_politician_repo.get_by_id.return_value = politician
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="speaker-matching-v1",
        )

        # Assert: ログは保存されるが、エンティティは更新されない
        mock_extraction_log_repo.create.assert_called_once()
        assert result.updated is True  # 処理は成功
        # マッチング処理ではupdate_from_extraction_logは呼ばれない
        # (nameがNoneの場合は_apply_extractionでスキップされる)


@pytest.mark.e2e
class TestPoliticianBulkExtraction:
    """Politician一括抽出のE2Eテスト。"""

    @pytest.fixture
    def mock_politician_repo(self):
        """政治家リポジトリのモック。"""
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
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdatePoliticianFromExtractionUseCaseのインスタンス。"""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_bulk_politician_extraction(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """複数政治家の一括抽出E2Eテスト。"""
        # Setup: 10人の政治家
        politicians = {
            i: Politician(
                id=i,
                name=f"政治家{i}",
                is_manually_verified=False,
            )
            for i in range(1, 11)
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_politician(entity_id: int):
            return politicians.get(entity_id)

        mock_politician_repo.get_by_id.side_effect = get_politician
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute: 10人を順番に抽出
        results = []
        for i in range(1, 11):
            extraction_result = PoliticianExtractionResult(
                name=f"政治家{i}",
                district=f"選挙区{i}",
                confidence_score=0.9,
            )
            result = await use_case.execute(
                entity_id=i,
                extraction_result=extraction_result,
                pipeline_version="bulk-scraping-v1",
            )
            results.append(result)

        # Assert: 全て成功
        assert all(r.updated is True for r in results)
        assert mock_extraction_log_repo.create.call_count == 10

        # 各政治家が正しく更新された
        for i in range(1, 11):
            assert politicians[i].district == f"選挙区{i}"
