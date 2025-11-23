"""ユーザー統計取得ユースケースのテスト"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.dtos.work_history_dto import WorkHistoryDTO, WorkType
from src.application.usecases.get_user_statistics_usecase import (
    GetUserStatisticsUseCase,
)


@pytest.mark.asyncio
async def test_get_user_statistics_basic():
    """基本的なユーザー統計を取得するテスト"""
    # Arrange
    user_id_1 = uuid4()
    user_id_2 = uuid4()

    # テストデータの作成
    work_histories = [
        WorkHistoryDTO(
            user_id=user_id_1,
            user_name="User 1",
            user_email="user1@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Speaker 1",
            executed_at=datetime(2024, 1, 1, 10, 0, 0),
        ),
        WorkHistoryDTO(
            user_id=user_id_1,
            user_name="User 1",
            user_email="user1@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Speaker 2",
            executed_at=datetime(2024, 1, 2, 11, 0, 0),
        ),
        WorkHistoryDTO(
            user_id=user_id_2,
            user_name="User 2",
            user_email="user2@example.com",
            work_type=WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION,
            target_data="Membership 1",
            executed_at=datetime(2024, 1, 3, 12, 0, 0),
        ),
    ]

    # GetWorkHistoryUseCaseをモック
    mock_work_history_usecase = MagicMock()
    mock_work_history_usecase.execute = AsyncMock(return_value=work_histories)

    usecase = GetUserStatisticsUseCase(work_history_usecase=mock_work_history_usecase)

    # Act
    stats = await usecase.execute()

    # Assert
    assert stats.total_count == 3
    assert len(stats.work_type_counts) == 2
    assert stats.work_type_counts[WorkType.SPEAKER_POLITICIAN_MATCHING.value] == 2
    assert (
        stats.work_type_counts[WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION.value]
        == 1
    )
    assert len(stats.user_counts) == 2
    assert len(stats.timeline_data) == 3  # 3日分のデータ
    assert len(stats.top_contributors) == 2  # 2人のユーザー


@pytest.mark.asyncio
async def test_get_user_statistics_top_contributors():
    """上位貢献者ランキングのテスト"""
    # Arrange
    user_id_1 = uuid4()
    user_id_2 = uuid4()
    user_id_3 = uuid4()

    work_histories = [
        # User 1: 3件
        WorkHistoryDTO(
            user_id=user_id_1,
            user_name="User 1",
            user_email="user1@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Data 1",
            executed_at=datetime.now(),
        ),
        WorkHistoryDTO(
            user_id=user_id_1,
            user_name="User 1",
            user_email="user1@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Data 2",
            executed_at=datetime.now(),
        ),
        WorkHistoryDTO(
            user_id=user_id_1,
            user_name="User 1",
            user_email="user1@example.com",
            work_type=WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION,
            target_data="Data 3",
            executed_at=datetime.now(),
        ),
        # User 2: 2件
        WorkHistoryDTO(
            user_id=user_id_2,
            user_name="User 2",
            user_email="user2@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Data 4",
            executed_at=datetime.now(),
        ),
        WorkHistoryDTO(
            user_id=user_id_2,
            user_name="User 2",
            user_email="user2@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Data 5",
            executed_at=datetime.now(),
        ),
        # User 3: 1件
        WorkHistoryDTO(
            user_id=user_id_3,
            user_name="User 3",
            user_email="user3@example.com",
            work_type=WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION,
            target_data="Data 6",
            executed_at=datetime.now(),
        ),
    ]

    mock_work_history_usecase = MagicMock()
    mock_work_history_usecase.execute = AsyncMock(return_value=work_histories)

    usecase = GetUserStatisticsUseCase(work_history_usecase=mock_work_history_usecase)

    # Act
    stats = await usecase.execute(top_n=2)

    # Assert
    assert len(stats.top_contributors) == 2
    assert stats.top_contributors[0].rank == 1
    assert stats.top_contributors[0].user_name == "User 1"
    assert stats.top_contributors[0].total_works == 3
    assert stats.top_contributors[1].rank == 2
    assert stats.top_contributors[1].user_name == "User 2"
    assert stats.top_contributors[1].total_works == 2


@pytest.mark.asyncio
async def test_get_user_statistics_timeline():
    """時系列データのテスト"""
    # Arrange
    user_id = uuid4()

    work_histories = [
        WorkHistoryDTO(
            user_id=user_id,
            user_name="User",
            user_email="user@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Data 1",
            executed_at=datetime(2024, 1, 1, 10, 0, 0),
        ),
        WorkHistoryDTO(
            user_id=user_id,
            user_name="User",
            user_email="user@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="Data 2",
            executed_at=datetime(2024, 1, 1, 11, 0, 0),
        ),
        WorkHistoryDTO(
            user_id=user_id,
            user_name="User",
            user_email="user@example.com",
            work_type=WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION,
            target_data="Data 3",
            executed_at=datetime(2024, 1, 2, 10, 0, 0),
        ),
    ]

    mock_work_history_usecase = MagicMock()
    mock_work_history_usecase.execute = AsyncMock(return_value=work_histories)

    usecase = GetUserStatisticsUseCase(work_history_usecase=mock_work_history_usecase)

    # Act
    stats = await usecase.execute()

    # Assert
    assert len(stats.timeline_data) == 2  # 2日分のデータ
    # 1月1日: 2件
    day1_data = [d for d in stats.timeline_data if d.date == date(2024, 1, 1)]
    assert len(day1_data) == 1
    assert day1_data[0].count == 2
    # 1月2日: 1件
    day2_data = [d for d in stats.timeline_data if d.date == date(2024, 1, 2)]
    assert len(day2_data) == 1
    assert day2_data[0].count == 1


@pytest.mark.asyncio
async def test_get_user_statistics_empty():
    """データが空の場合のテスト"""
    # Arrange
    mock_work_history_usecase = MagicMock()
    mock_work_history_usecase.execute = AsyncMock(return_value=[])

    usecase = GetUserStatisticsUseCase(work_history_usecase=mock_work_history_usecase)

    # Act
    stats = await usecase.execute()

    # Assert
    assert stats.total_count == 0
    assert len(stats.work_type_counts) == 0
    assert len(stats.user_counts) == 0
    assert len(stats.timeline_data) == 0
    assert len(stats.top_contributors) == 0
