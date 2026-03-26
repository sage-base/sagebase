"""BQカバレッジ集計リポジトリインターフェース."""

from abc import ABC, abstractmethod

from src.domain.entities.bq_coverage_stats import (
    BQCoverageSummary,
    PrefectureCoverageStats,
)


class IBQDataCoverageRepository(ABC):
    """BigQueryからカバレッジ指標を取得するリポジトリインターフェース.

    国会と地方議会を分離して集計し、
    都道府県別の内訳も提供する。
    """

    @abstractmethod
    async def get_coverage_summary(self) -> BQCoverageSummary:
        """カバレッジページに必要な全指標を取得する.

        Returns:
            BQCoverageSummary: 国会/地方分離された全集計結果
        """

    @abstractmethod
    async def get_prefecture_stats(self) -> list[PrefectureCoverageStats]:
        """都道府県別のカバレッジ統計を取得する.

        Returns:
            list[PrefectureCoverageStats]: 都道府県ごとの集計結果
        """
