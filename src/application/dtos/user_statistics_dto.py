"""ユーザー統計に関するDTOモジュール

このモジュールは、ユーザー別の作業統計情報を表現するDTOを提供します。
"""

from dataclasses import dataclass
from datetime import date

from src.application.dtos.work_history_dto import WorkType


@dataclass
class TimelineDataPoint:
    """時系列データポイント

    Attributes:
        date: データの日付
        count: 作業件数
        work_type: 作業タイプ（Noneの場合は全タイプの集計）
    """

    date: date
    count: int
    work_type: WorkType | None = None


@dataclass
class ContributorRank:
    """貢献者ランキング

    Attributes:
        rank: ランキング順位（1から開始）
        user_name: ユーザーの表示名
        user_email: ユーザーのメールアドレス
        total_works: 総作業件数
        work_type_breakdown: 作業タイプ別の内訳
    """

    rank: int
    user_name: str | None
    user_email: str | None
    total_works: int
    work_type_breakdown: dict[str, int]


@dataclass
class UserStatisticsDTO:
    """ユーザー統計情報を表現するDTO

    Attributes:
        total_count: 総作業件数
        work_type_counts: 作業タイプごとの件数
        user_counts: ユーザーごとの件数
        timeline_data: 時系列データのリスト
        top_contributors: 上位貢献者のリスト
    """

    total_count: int
    work_type_counts: dict[str, int]
    user_counts: dict[str, int]
    timeline_data: list[TimelineDataPoint]
    top_contributors: list[ContributorRank]
