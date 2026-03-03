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
    ) -> None:
        super().__init__(id)
        self.name = _sanitize_name(name)
        self.prefecture = prefecture
        self.district = district
        self.furigana = furigana
        self.profile_page_url = profile_page_url
        self.party_position = party_position

    def __str__(self) -> str:
        return self.name
