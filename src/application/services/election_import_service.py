"""選挙インポート共通サービス.

国政選挙（小選挙区）インポートと比例代表インポートの共通ロジックを提供する。
- 候補者名の正規化
- 政党の解決（キャッシュ付き）
- 政治家の名寄せ
- 新規政治家の作成
"""

import logging
import re
import unicodedata

from datetime import date
from typing import Literal

from src.domain.entities.election import Election
from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.domain.repositories.politician_repository import PoliticianRepository


logger = logging.getLogger(__name__)

MatchStatus = Literal["matched", "not_found", "ambiguous"]

# 政党名の略称→正式名マッピング
_PARTY_ALIAS_MAP: dict[str, str] = {
    "自民": "自由民主党",
    "自民党": "自由民主党",
    "公明": "公明党",
    "共産": "日本共産党",
    "共産党": "日本共産党",
    "社民": "社会民主党",
    "社民党": "社会民主党",
    "立憲": "立憲民主党",
    "民主": "民主党",
    "民進": "民進党",
    "参政": "参政党",
    "れ新": "れいわ新選組",
    "維新": "日本維新の会",
    "維新の会": "日本維新の会",
    "日本維新": "日本維新の会",
    "幸福": "幸福実現党",
    "幸福実現等": "幸福実現党",
    "日本のこころを": "日本のこころを大切にする党",
    "保守": "保守党",
}


def normalize_name(name: str) -> str:
    """候補者名の空白を全て除去して正規化する."""
    return name.replace(" ", "").replace("\u3000", "")


def normalize_party_name(name: str) -> str:
    """政党名を正規化する.

    1. NFKC正規化（全角英数→半角）
    2. 括弧除去
    3. 空白除去・改行除去
    4. 略称→正式名変換
    """
    if not name:
        return name

    # NFKC正規化（ＮＨＫ→NHK等）
    normalized = unicodedata.normalize("NFKC", name)

    # 先頭・末尾の括弧除去: (xxx), （xxx）, [xxx]
    normalized = re.sub(r"^[(\[（](.+?)[)\]）]$", r"\1", normalized)

    # 空白・改行除去
    normalized = normalized.replace("\u3000", "").replace(" ", "").replace("\n", "")

    # 略称→正式名
    if normalized in _PARTY_ALIAS_MAP:
        return _PARTY_ALIAS_MAP[normalized]

    return normalized


class ElectionImportService:
    """選挙インポート共通サービス."""

    def __init__(
        self,
        politician_repository: PoliticianRepository,
        political_party_repository: PoliticalPartyRepository,
        election_repository: ElectionRepository | None = None,
        party_membership_history_repository: (
            PartyMembershipHistoryRepository | None
        ) = None,
    ) -> None:
        self._politician_repo = politician_repository
        self._party_repo = political_party_repository
        self._election_repo = election_repository
        self._membership_history_repo = party_membership_history_repository
        self._party_cache: dict[str, PoliticalParty | None] = {}

    def clear_cache(self) -> None:
        """政党キャッシュをクリアする."""
        self._party_cache.clear()

    async def resolve_party(
        self, party_name: str
    ) -> tuple[PoliticalParty | None, bool]:
        """政党名からPoliticalPartyエンティティを取得/作成する.

        政党名は正規化される（括弧除去、略称→正式名変換、NFKC正規化）。

        Returns:
            (政党エンティティ, 新規作成フラグ)
        """
        if not party_name:
            return None, False

        # 政党名を正規化
        normalized = normalize_party_name(party_name)
        if not normalized:
            return None, False

        # キャッシュチェック
        if normalized in self._party_cache:
            return self._party_cache[normalized], False

        # DB検索
        party = await self._party_repo.get_by_name(normalized)
        if party:
            self._party_cache[normalized] = party
            return party, False

        # 新規作成
        logger.info("政党を新規作成: %s (元: %s)", normalized, party_name)
        new_party = PoliticalParty(name=normalized)
        created = await self._party_repo.create(new_party)
        self._party_cache[normalized] = created
        return created, True

    async def match_politician(
        self,
        name: str,
        party_id: int | None,
        election_date: date | None = None,
    ) -> tuple[Politician | None, MatchStatus]:
        """候補者名で既存政治家を検索する.

        Returns:
            (politician, status): statusは "matched", "not_found", "ambiguous"
        """
        normalized = normalize_name(name)
        candidates = await self._politician_repo.search_by_normalized_name(normalized)

        if len(candidates) == 0:
            return None, "not_found"
        elif len(candidates) == 1:
            return candidates[0], "matched"
        else:
            # 同姓同名: 政党で絞り込み
            if party_id is not None:
                party_filtered = await self._filter_by_party(
                    candidates, party_id, election_date
                )
                if len(party_filtered) == 1:
                    return party_filtered[0], "matched"
            logger.warning(
                "同姓同名の政治家が%d名: %s（party_id=%s）",
                len(candidates),
                name,
                party_id,
            )
            return None, "ambiguous"

    async def _filter_by_party(
        self,
        candidates: list[Politician],
        party_id: int,
        election_date: date | None,
    ) -> list[Politician]:
        """候補者リストを政党IDで絞り込む（party_membership_history経由）."""
        if self._membership_history_repo is not None and election_date is not None:
            candidate_ids = [c.id for c in candidates if c.id is not None]
            history_map = (
                await self._membership_history_repo.get_current_by_politicians(
                    candidate_ids, as_of_date=election_date
                )
            )
            filtered: list[Politician] = []
            for c in candidates:
                history = history_map.get(c.id) if c.id is not None else None
                if history is not None:
                    if history.political_party_id == party_id:
                        filtered.append(c)
            return filtered
        # 履歴リポジトリが未設定の場合は空リストを返す
        return []

    async def create_politician(
        self,
        name: str,
        prefecture: str,
        district: str,
        party_id: int | None,
        election_date: date | None = None,
    ) -> Politician | None:
        """新規政治家を作成する."""
        normalized = normalize_name(name)
        politician = Politician(
            name=normalized,
            prefecture=prefecture,
            district=district,
        )
        try:
            created = await self._politician_repo.create(politician)
            logger.debug("政治家を作成: %s (ID=%d)", created.name, created.id)
        except Exception:
            logger.exception("政治家作成失敗: %s", name)
            return None

        if (
            party_id is not None
            and self._membership_history_repo is not None
            and election_date is not None
            and created.id is not None
        ):
            try:
                history = PartyMembershipHistory(
                    politician_id=created.id,
                    political_party_id=party_id,
                    start_date=election_date,
                )
                await self._membership_history_repo.create(history)
                logger.debug(
                    "所属履歴を作成: politician_id=%d, party_id=%d, start_date=%s",
                    created.id,
                    party_id,
                    election_date,
                )
            except Exception:
                logger.warning(
                    "所属履歴の作成に失敗（政治家は作成済み）: %s",
                    name,
                    exc_info=True,
                )

        return created

    async def get_or_create_election(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date | None,
        election_type: str = Election.ELECTION_TYPE_GENERAL,
    ) -> Election | None:
        """Electionレコードを取得または作成する."""
        if self._election_repo is None:
            raise RuntimeError("election_repository is not set")

        existing = await self._election_repo.get_by_governing_body_and_term(
            governing_body_id, term_number, election_type=election_type
        )
        if existing:
            logger.info("既存のElectionを使用: %s (ID=%d)", existing, existing.id)
            return existing

        if election_date is None:
            logger.error("選挙日が不正: %s", election_date)
            return None

        election = Election(
            governing_body_id=governing_body_id,
            term_number=term_number,
            election_date=election_date,
            election_type=election_type,
        )
        created = await self._election_repo.create(election)
        logger.info("Electionを作成: %s (ID=%d)", created, created.id)
        return created
