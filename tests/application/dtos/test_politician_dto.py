"""PoliticianOutputItem の単体テスト."""

from src.application.dtos.politician_dto import PoliticianOutputItem
from src.domain.entities import Politician


class TestPoliticianOutputItemFromEntity:
    """PoliticianOutputItem.from_entity() のテスト."""

    def test_from_entity_maps_all_fields(self) -> None:
        """全フィールドが正しくマッピングされることを確認."""
        entity = Politician(
            id=1,
            name="田中太郎",
            prefecture="東京都",
            district="新宿区",
            political_party_id=1,
            furigana="タナカタロウ",
            profile_page_url="https://example.com/tanaka",
            party_position="幹事長",
        )

        item = PoliticianOutputItem.from_entity(entity)

        assert item.id == 1
        assert item.name == "田中太郎"
        assert item.prefecture == "東京都"
        assert item.district == "新宿区"
        assert item.political_party_id == 1
        assert item.furigana == "タナカタロウ"
        assert item.profile_page_url == "https://example.com/tanaka"
        assert item.party_position == "幹事長"

    def test_from_entity_with_none_id(self) -> None:
        """idがNoneのエンティティでも変換できることを確認."""
        entity = Politician(
            name="田中太郎",
            prefecture="東京都",
            district="新宿区",
        )

        item = PoliticianOutputItem.from_entity(entity)

        assert item.id is None
        assert item.name == "田中太郎"

    def test_from_entity_with_optional_fields_none(self) -> None:
        """Optionalフィールドが全てNoneの場合もマッピングされることを確認."""
        entity = Politician(
            id=1,
            name="山田花子",
            prefecture="大阪府",
            district="中央区",
            political_party_id=None,
            furigana=None,
            profile_page_url=None,
            party_position=None,
        )

        item = PoliticianOutputItem.from_entity(entity)

        assert item.political_party_id is None
        assert item.furigana is None
        assert item.profile_page_url is None
        assert item.party_position is None
