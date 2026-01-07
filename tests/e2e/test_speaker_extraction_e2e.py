"""E2Eテスト: Speaker抽出の完全なフロー (Issue #871).

発言者情報の抽出・政治家紐付け・手動修正保護の完全なE2Eフローをテスト。

フロー：
1. 議事録からの発言者抽出
2. 政治家とのマッチング
3. 手動修正（紐付け訂正）
4. 再マッチング
5. 手動修正が保護されていることを確認
"""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)
from src.application.usecases.update_speaker_from_extraction_usecase import (
    UpdateSpeakerFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.speaker import Speaker


@pytest.mark.e2e
class TestSpeakerExtractionFullFlow:
    """Speaker抽出の完全なE2Eフローテスト。"""

    @pytest.fixture
    def mock_speaker_repo(self):
        """発言者リポジトリのモック。"""
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
        self, mock_speaker_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateSpeakerFromExtractionUseCaseのインスタンス。"""
        return UpdateSpeakerFromExtractionUseCase(
            speaker_repo=mock_speaker_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_speaker_extraction_full_flow(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """Speaker抽出の完全なE2Eフロー。"""
        # ============================================
        # Step 1: 議事録からの発言者抽出
        # ============================================
        speaker = Speaker(
            id=1,
            name="山田太郎",
            is_politician=False,
            politician_id=None,
            is_manually_verified=False,
        )

        extraction_result_1 = SpeakerExtractionResult(
            name="山田太郎",
            type="議員",
            political_party_name="自民党",
            is_politician=True,
            politician_id=100,  # AIがマッチングした政治家ID
        )
        extraction_log_1 = ExtractionLog(
            id=4000,
            entity_type=EntityType.SPEAKER,
            entity_id=1,
            pipeline_version="speaker-matching-rule-based-v1",
            extracted_data=extraction_result_1.to_dict(),
        )

        mock_speaker_repo.get_by_id.return_value = speaker
        mock_extraction_log_repo.create.return_value = extraction_log_1

        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="speaker-matching-rule-based-v1",
        )

        # Step 1 検証
        assert result_1.updated is True
        assert result_1.extraction_log_id == 4000
        assert speaker.is_politician is True
        assert speaker.politician_id == 100

        # ============================================
        # Step 2: ログ確認
        # ============================================
        mock_extraction_log_repo.get_by_entity.return_value = [extraction_log_1]
        logs = await mock_extraction_log_repo.get_by_entity(EntityType.SPEAKER, 1)
        assert len(logs) == 1

        # ============================================
        # Step 3: 手動修正（紐付け訂正）
        # ============================================
        # ユーザーがAIの紐付けを訂正
        speaker.politician_id = 200  # 正しい政治家ID
        speaker.mark_as_manually_verified()

        assert speaker.is_manually_verified is True
        assert speaker.politician_id == 200

        # ============================================
        # Step 4: 再マッチング
        # ============================================
        extraction_result_2 = SpeakerExtractionResult(
            name="山田太郎",
            type="議員",
            is_politician=True,
            politician_id=300,  # AIは別の政治家を推定
        )
        extraction_log_2 = ExtractionLog(
            id=4001,
            entity_type=EntityType.SPEAKER,
            entity_id=1,
            pipeline_version="speaker-matching-llm-v1",
            extracted_data=extraction_result_2.to_dict(),
        )

        mock_extraction_log_repo.create.return_value = extraction_log_2

        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="speaker-matching-llm-v1",
        )

        # ============================================
        # Step 5: 手動修正が保護されていることを確認
        # ============================================
        assert result_2.updated is False
        assert result_2.reason == "manually_verified"
        assert speaker.politician_id == 200  # 手動修正が保持


@pytest.mark.e2e
class TestSpeakerMatchingMethods:
    """発言者マッチング方法のE2Eテスト。"""

    @pytest.fixture
    def mock_speaker_repo(self):
        """発言者リポジトリのモック。"""
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
        self, mock_speaker_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateSpeakerFromExtractionUseCaseのインスタンス。"""
        return UpdateSpeakerFromExtractionUseCase(
            speaker_repo=mock_speaker_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_rule_based_to_llm_matching_transition(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """ルールベースからLLMマッチングへの遷移E2Eテスト。"""
        # Setup
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

        mock_speaker_repo.get_by_id.return_value = speaker
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute 1: ルールベースマッチング（マッチなし）
        extraction_result_1 = SpeakerExtractionResult(
            name="山田太郎",
            is_politician=False,  # マッチなし
            politician_id=None,
        )
        result_1 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_1,
            pipeline_version="speaker-matching-rule-based-v1",
        )

        assert result_1.updated is True
        assert speaker.is_politician is False

        # Execute 2: LLMマッチング（マッチあり）
        extraction_result_2 = SpeakerExtractionResult(
            name="山田太郎",
            is_politician=True,
            politician_id=500,  # LLMがマッチングした政治家
        )
        result_2 = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result_2,
            pipeline_version="speaker-matching-llm-v1",
        )

        assert result_2.updated is True
        assert speaker.is_politician is True
        assert speaker.politician_id == 500

        # 2つのログが作成された
        assert mock_extraction_log_repo.create.call_count == 2


@pytest.mark.e2e
class TestSpeakerTypeClassification:
    """発言者タイプ分類のE2Eテスト。"""

    @pytest.fixture
    def mock_speaker_repo(self):
        """発言者リポジトリのモック。"""
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
        self, mock_speaker_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdateSpeakerFromExtractionUseCaseのインスタンス。"""
        return UpdateSpeakerFromExtractionUseCase(
            speaker_repo=mock_speaker_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_various_speaker_types(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """様々な発言者タイプのE2Eテスト。"""
        # Setup
        speaker_types = [
            ("議員", True),
            ("参考人", False),
            ("傍聴人", False),
            ("委員長", True),
            ("政府参考人", False),
        ]

        speakers = {
            i: Speaker(
                id=i,
                name=f"発言者{i}",
                is_politician=False,
                is_manually_verified=False,
            )
            for i in range(1, len(speaker_types) + 1)
        }

        log_id_counter = [0]

        def create_log(log: ExtractionLog) -> ExtractionLog:
            log_id_counter[0] += 1
            log.id = log_id_counter[0]
            return log

        def get_speaker(entity_id: int):
            return speakers.get(entity_id)

        mock_speaker_repo.get_by_id.side_effect = get_speaker
        mock_extraction_log_repo.create.side_effect = create_log

        # Execute
        for i, (speaker_type, is_politician) in enumerate(speaker_types, start=1):
            extraction_result = SpeakerExtractionResult(
                name=f"発言者{i}",
                type=speaker_type,
                is_politician=is_politician,
            )
            await use_case.execute(
                entity_id=i,
                extraction_result=extraction_result,
                pipeline_version="speaker-classification-v1",
            )

        # Assert: 各発言者タイプが正しく設定された
        for i, (speaker_type, is_politician) in enumerate(speaker_types, start=1):
            assert speakers[i].type == speaker_type
            assert speakers[i].is_politician == is_politician
