"""ElectionOutputItem の単体テスト."""

from datetime import date

from src.application.dtos.election_dto import ElectionOutputItem
from src.domain.entities import Election


class TestElectionOutputItemFromEntity:
    """ElectionOutputItem.from_entity() のテスト."""

    def test_from_entity_maps_all_fields(self) -> None:
        """全フィールドが正しくマッピングされることを確認."""
        entity = Election(
            id=1,
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type="統一地方選挙",
        )

        item = ElectionOutputItem.from_entity(entity)

        assert item.id == 1
        assert item.governing_body_id == 88
        assert item.term_number == 21
        assert item.election_date == date(2023, 4, 9)
        assert item.election_type == "統一地方選挙"

    def test_from_entity_with_none_id(self) -> None:
        """idがNoneのエンティティでも変換できることを確認."""
        entity = Election(
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
        )

        item = ElectionOutputItem.from_entity(entity)

        assert item.id is None
        assert item.governing_body_id == 88

    def test_from_entity_with_none_election_type(self) -> None:
        """election_typeがNoneの場合もNoneがマッピングされることを確認."""
        entity = Election(
            id=1,
            governing_body_id=88,
            term_number=21,
            election_date=date(2023, 4, 9),
            election_type=None,
        )

        item = ElectionOutputItem.from_entity(entity)

        assert item.election_type is None
