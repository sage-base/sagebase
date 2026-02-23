"""参議院選挙候補者データの値オブジェクト."""

from dataclasses import dataclass


@dataclass
class SangiinCandidateRecord:
    """参議院選挙の議員データを表す値オブジェクト.

    giin.jsonから読み込んだ1レコード分のデータを保持する。
    """

    name: str
    """議員氏名."""
    furigana: str
    """読み方."""
    party_name: str
    """会派名."""
    district_name: str
    """選挙区（都道府県名 or "比例"）."""
    elected_years: list[int]
    """当選年リスト（新しい順）."""
    election_count: int
    """当選回数."""
    profile_url: str | None
    """紹介URL."""
    is_proportional: bool
    """比例区かどうか（district_name == "比例"）."""
