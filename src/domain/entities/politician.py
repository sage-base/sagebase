"""Politician entity."""

from src.domain.entities.base import BaseEntity


def _sanitize_name(name: str) -> str:
    """全角スペースを除去し、前後の空白を除去する."""
    return name.replace("\u3000", "").strip()


class Politician(BaseEntity):
    """政治家を表すエンティティ."""

    def __init__(
        self,
        name: str,
        prefecture: str,
        district: str,
        furigana: str | None = None,
        profile_page_url: str | None = None,
        party_position: str | None = None,
        id: int | None = None,
        is_lastname_hiragana: bool = False,
        is_firstname_hiragana: bool = False,
        kanji_name: str | None = None,
    ) -> None:
        super().__init__(id)
        self.name = _sanitize_name(name)
        self.prefecture = prefecture
        self.district = district
        self.furigana = furigana
        self.profile_page_url = profile_page_url
        self.party_position = party_position
        self.is_lastname_hiragana = is_lastname_hiragana
        self.is_firstname_hiragana = is_firstname_hiragana
        self.kanji_name = _sanitize_name(kanji_name) if kanji_name else None

    def __str__(self) -> str:
        return self.name
