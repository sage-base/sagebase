"""ConferenceMemberの任期（start_date/end_date）算出ドメインサービス.

選挙データに基づいてConferenceMemberのend_dateを算出する。
- 衆議院: 同一院の次回選挙日-1
- 参議院: 半数改選のため同じパリティ（奇偶）の次回選挙日-1
"""

from __future__ import annotations

from datetime import date, timedelta

from src.domain.entities.election import Election


class ConferenceMemberTermService:
    """ConferenceMemberの任期を算出するドメインサービス."""

    @staticmethod
    def calculate_end_date(
        target_election: Election,
        same_chamber_elections: list[Election],
    ) -> date | None:
        """次回改選に基づくend_dateを算出する.

        Args:
            target_election: 対象の選挙
            same_chamber_elections: 同一院の全選挙（election_date昇順でソート済み）

        Returns:
            end_date（次回選挙日-1）。次回選挙が未登録の場合はNone。
        """
        if target_election.is_sangiin:
            return ConferenceMemberTermService._calculate_sangiin_end_date(
                target_election, same_chamber_elections
            )
        return ConferenceMemberTermService._calculate_shugiin_end_date(
            target_election, same_chamber_elections
        )

    @staticmethod
    def _calculate_sangiin_end_date(
        target_election: Election,
        same_chamber_elections: list[Election],
    ) -> date | None:
        """参議院: 同パリティ（奇偶）の次回選挙日-1."""
        same_parity = sorted(
            [
                e
                for e in same_chamber_elections
                if e.term_number % 2 == target_election.term_number % 2
            ],
            key=lambda e: e.election_date,
        )
        idx = next(
            (
                i
                for i, e in enumerate(same_parity)
                if e.term_number == target_election.term_number
            ),
            None,
        )
        if idx is not None and idx + 1 < len(same_parity):
            return same_parity[idx + 1].election_date - timedelta(days=1)
        return None

    @staticmethod
    def _calculate_shugiin_end_date(
        target_election: Election,
        same_chamber_elections: list[Election],
    ) -> date | None:
        """衆議院: 同一院の次回選挙日-1."""
        current_idx = next(
            (
                i
                for i, e in enumerate(same_chamber_elections)
                if e.term_number == target_election.term_number
            ),
            None,
        )
        if current_idx is not None and current_idx + 1 < len(same_chamber_elections):
            return same_chamber_elections[current_idx + 1].election_date - timedelta(
                days=1
            )
        return None
