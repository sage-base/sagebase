"""国政選挙データインポートユースケース.

総務省XLSファイルからパースした候補者データをDBにインポートする。

処理フロー:
    1. XLSファイルURLリストをスクレイパーで取得
    2. XLSファイルをダウンロード・パース
    3. Electionレコード作成（冪等性: 既存の場合はメンバーを削除して再作成）
    4. 各候補者について名寄せ + ElectionMember作成
    5. レポート出力
"""

import logging

from datetime import date
from pathlib import Path

from src.application.dtos.national_election_import_dto import (
    CandidateRecord,
    ImportNationalElectionInputDto,
    ImportNationalElectionOutputDto,
)
from src.domain.entities.election import Election
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.infrastructure.importers.soumu_election_scraper import (
    download_xls_files,
    fetch_xls_urls,
)
from src.infrastructure.importers.soumu_xls_parser import parse_xls_file


logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """候補者名の空白を全て除去して正規化する."""
    return name.replace(" ", "").replace("　", "").replace("\u3000", "")


class ImportNationalElectionUseCase:
    """国政選挙データインポートのユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        politician_repository: PoliticianRepository,
        political_party_repository: PoliticalPartyRepository,
    ) -> None:
        self._election_repo = election_repository
        self._member_repo = election_member_repository
        self._politician_repo = politician_repository
        self._party_repo = political_party_repository

        # 政党名キャッシュ（名前→エンティティ）
        self._party_cache: dict[str, PoliticalParty | None] = {}

    async def execute(
        self,
        input_dto: ImportNationalElectionInputDto,
        download_dir: Path | None = None,
    ) -> ImportNationalElectionOutputDto:
        """インポートを実行する."""
        output = ImportNationalElectionOutputDto(
            election_number=input_dto.election_number
        )

        # 1. XLSファイルURLを取得
        logger.info(
            "第%d回衆議院選挙のXLSファイルURL取得中...", input_dto.election_number
        )
        xls_files = fetch_xls_urls(input_dto.election_number)
        if not xls_files:
            logger.error("XLSファイルが見つかりません")
            output.errors = 1
            output.error_details.append("XLSファイルURLの取得に失敗")
            return output

        logger.info("%d個のXLSファイルを検出", len(xls_files))

        # 2. ダウンロード
        if download_dir is None:
            download_dir = Path("tmp") / f"soumu_election_{input_dto.election_number}"
        downloaded = download_xls_files(xls_files, download_dir)
        if not downloaded:
            logger.error("XLSファイルのダウンロードに失敗")
            output.errors = 1
            output.error_details.append("XLSファイルのダウンロードに失敗")
            return output

        # 3. パース
        all_candidates: list[CandidateRecord] = []
        election_date = None

        for xls_info, file_path in downloaded:
            election_info, candidates = parse_xls_file(file_path)
            if election_info and election_date is None:
                election_date = election_info.election_date
            all_candidates.extend(candidates)
            logger.info(
                "%s: %d候補者を抽出",
                xls_info.prefecture_name,
                len(candidates),
            )

        output.total_candidates = len(all_candidates)
        logger.info("合計 %d 候補者を抽出", len(all_candidates))

        if not all_candidates:
            logger.error("候補者データが抽出できません")
            output.errors = 1
            output.error_details.append("候補者データの抽出に失敗")
            return output

        if input_dto.dry_run:
            logger.info("ドライラン: DB書き込みをスキップ")
            self._print_dry_run_report(all_candidates)
            return output

        # 4. Electionレコード作成
        election = await self._get_or_create_election(
            input_dto.governing_body_id,
            input_dto.election_number,
            election_date,
        )
        if election is None or election.id is None:
            output.errors = 1
            output.error_details.append("Electionレコードの作成に失敗")
            return output

        output.election_id = election.id

        # 既存メンバーを削除（冪等性のため）
        deleted_count = await self._member_repo.delete_by_election_id(election.id)
        if deleted_count > 0:
            logger.info("既存のElectionMember %d件を削除", deleted_count)

        # 5. 各候補者を処理
        for candidate in all_candidates:
            try:
                await self._process_candidate(candidate, election.id, output)
            except Exception:
                logger.exception("候補者処理失敗: %s", candidate.name)
                output.errors += 1
                output.error_details.append(f"候補者処理失敗: {candidate.name}")

        logger.info(
            "インポート完了: 候補者=%d, マッチ=%d, 新規政治家=%d, 新規政党=%d, "
            "曖昧スキップ=%d, ElectionMember=%d, エラー=%d",
            output.total_candidates,
            output.matched_politicians,
            output.created_politicians,
            output.created_parties,
            output.skipped_ambiguous,
            output.election_members_created,
            output.errors,
        )
        return output

    async def _get_or_create_election(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date | None,
    ) -> Election | None:
        """Electionレコードを取得または作成する."""
        existing = await self._election_repo.get_by_governing_body_and_term(
            governing_body_id, term_number
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
            election_type="衆議院議員総選挙",
        )
        created = await self._election_repo.create(election)
        logger.info("Electionを作成: %s (ID=%d)", created, created.id)
        return created

    async def _process_candidate(
        self,
        candidate: CandidateRecord,
        election_id: int,
        output: ImportNationalElectionOutputDto,
    ) -> None:
        """候補者1名分の処理（政党解決→名寄せ→ElectionMember作成）."""
        # 政党を解決
        party = await self._resolve_party(candidate.party_name)
        party_id = party.id if party else None
        if (
            party
            and party.id is not None
            and candidate.party_name not in self._party_cache
        ):
            self._party_cache[candidate.party_name] = party

        # 政治家を名寄せ
        politician, status = await self._match_politician(candidate.name, party_id)

        if status == "ambiguous":
            output.skipped_ambiguous += 1
            logger.warning(
                "同姓同名スキップ: %s (%s)", candidate.name, candidate.district_name
            )
            return

        if politician is None:
            # 新規作成
            politician = await self._create_politician(candidate, party_id)
            output.created_politicians += 1
        else:
            output.matched_politicians += 1

        if politician is None or politician.id is None:
            output.errors += 1
            output.error_details.append(f"政治家作成失敗: {candidate.name}")
            return

        # ElectionMember作成
        result = (
            ElectionMember.RESULT_ELECTED
            if candidate.is_elected
            else ElectionMember.RESULT_LOST
        )
        member = ElectionMember(
            election_id=election_id,
            politician_id=politician.id,
            result=result,
            votes=candidate.total_votes if candidate.total_votes > 0 else None,
            rank=candidate.rank if candidate.rank > 0 else None,
        )
        await self._member_repo.create(member)
        output.election_members_created += 1

    async def _resolve_party(self, party_name: str) -> PoliticalParty | None:
        """政党名からPoliticalPartyエンティティを取得/作成する."""
        if not party_name:
            return None

        # キャッシュチェック
        if party_name in self._party_cache:
            return self._party_cache[party_name]

        # DB検索
        party = await self._party_repo.get_by_name(party_name)
        if party:
            self._party_cache[party_name] = party
            return party

        # 新規作成
        logger.info("政党を新規作成: %s", party_name)
        new_party = PoliticalParty(name=party_name)
        created = await self._party_repo.create(new_party)
        self._party_cache[party_name] = created
        return created

    async def _match_politician(
        self, name: str, party_id: int | None
    ) -> tuple[Politician | None, str]:
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
                party_filtered = [
                    c for c in candidates if c.political_party_id == party_id
                ]
                if len(party_filtered) == 1:
                    return party_filtered[0], "matched"
            logger.warning(
                "同姓同名の政治家が%d名: %s（party_id=%s）",
                len(candidates),
                name,
                party_id,
            )
            return None, "ambiguous"

    async def _create_politician(
        self, candidate: CandidateRecord, party_id: int | None
    ) -> Politician | None:
        """新規政治家を作成する."""
        politician = Politician(
            name=candidate.name,
            prefecture=candidate.prefecture,
            district=candidate.district_name,
            political_party_id=party_id,
        )
        try:
            created = await self._politician_repo.create(politician)
            logger.debug("政治家を作成: %s (ID=%d)", created.name, created.id)
            return created
        except Exception:
            logger.exception("政治家作成失敗: %s", candidate.name)
            return None

    def _print_dry_run_report(self, candidates: list[CandidateRecord]) -> None:
        """ドライラン時のレポートを出力する."""
        districts = {c.district_name for c in candidates}
        parties = {c.party_name for c in candidates if c.party_name}
        elected = [c for c in candidates if c.is_elected]

        logger.info("--- ドライランレポート ---")
        logger.info("選挙区数: %d", len(districts))
        logger.info("候補者数: %d", len(candidates))
        logger.info("当選者数: %d", len(elected))
        logger.info("政党数: %d", len(parties))
        logger.info("政党名: %s", ", ".join(sorted(parties)))
