"""Tests for ElectionMember entity."""

import pytest

from src.domain.entities.election_member import ElectionMember


class TestElectionMember:
    """ElectionMemberエンティティのテスト."""

    def test_initialization_with_required_fields(self) -> None:
        """必須フィールドのみで初期化できること."""
        member = ElectionMember(election_id=1, politician_id=2, result="当選")

        assert member.election_id == 1
        assert member.politician_id == 2
        assert member.result == "当選"
        assert member.votes is None
        assert member.rank is None
        assert member.id is None

    def test_initialization_with_all_fields(self) -> None:
        """全フィールドで初期化できること."""
        member = ElectionMember(
            id=10,
            election_id=1,
            politician_id=2,
            result="当選",
            votes=5000,
            rank=1,
        )

        assert member.id == 10
        assert member.votes == 5000
        assert member.rank == 1


class TestIsElected:
    """is_electedプロパティのテスト."""

    @pytest.mark.parametrize(
        ("result", "expected"),
        [
            ("当選", True),
            ("繰上当選", True),
            ("無投票当選", True),
            ("落選", False),
            ("次点", False),
        ],
    )
    def test_is_elected(self, result: str, expected: bool) -> None:
        """各選挙結果に対してis_electedが正しく判定されること."""
        member = ElectionMember(election_id=1, politician_id=2, result=result)
        assert member.is_elected is expected
