"""選挙特定ドメインサービス."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from src.domain.entities.election import Election


@dataclass(frozen=True)
class ShugiinDietSessionMapping:
    """衆議院選挙回次→国会在籍期間のマッピング."""

    term_number: int
    election_date: date
    diet_sessions_start: int
    diet_sessions_end: int


class ElectionDomainService:
    """meeting.dateから有効な選挙を特定するドメインサービス.

    conferences.termを使わず、meeting.dateから直接
    「その日時点で有効な選挙」を特定するロジックを提供する。
    """

    # PBI-2（発言者-政治家の全量紐付け）で国会回次から選挙特定に使用予定
    SHUGIIN_DIET_SESSION_MAPPINGS: ClassVar[list[ShugiinDietSessionMapping]] = [
        ShugiinDietSessionMapping(45, date(2009, 8, 30), 172, 181),
        ShugiinDietSessionMapping(46, date(2012, 12, 16), 182, 187),
        ShugiinDietSessionMapping(47, date(2014, 12, 14), 188, 194),
        ShugiinDietSessionMapping(48, date(2017, 10, 22), 195, 205),
        ShugiinDietSessionMapping(49, date(2021, 10, 31), 206, 214),
        ShugiinDietSessionMapping(50, date(2024, 10, 27), 215, 215),
    ]

    def get_active_election_at_date(
        self,
        elections: list[Election],
        target_date: date,
        chamber: str | None = None,
    ) -> Election | None:
        """指定日時点で有効な選挙を返す.

        Args:
            elections: 検索対象の選挙一覧
            target_date: 検索基準日（通常はmeeting.date）
            chamber: 院名フィルタ（"衆議院", "参議院"等）。Noneの場合はフィルタなし。

        Returns:
            有効な選挙エンティティ。該当なしの場合はNone。
        """
        filtered = (
            [e for e in elections if e.chamber == chamber]
            if chamber is not None
            else elections
        )
        applicable = [e for e in filtered if e.election_date <= target_date]
        if not applicable:
            return None
        return max(applicable, key=lambda e: e.election_date)
