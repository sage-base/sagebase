"""国政選挙データインポートユースケース.

外部データソースからパースした候補者データをDBにインポートする。

処理フロー:
    1. データソースから候補者データ取得
    2. Electionレコード作成（冪等性: 既存の場合はメンバーを削除して再作成）
    3. 各候補者について名寄せ + ElectionMember作成
    4. レポート出力
"""

import logging

from datetime import date

from src.application.dtos.national_election_import_dto import (
    ImportNationalElectionInputDto,
    ImportNationalElectionOutputDto,
)
from src.application.services.election_import_service import ElectionImportService
from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.election_data_source_service import (
    IElectionDataSourceService,
)
from src.domain.value_objects.election_candidate import CandidateRecord


logger = logging.getLogger(__name__)


class ImportNationalElectionUseCase:
    """国政選挙データインポートのユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        politician_repository: PoliticianRepository,
        political_party_repository: PoliticalPartyRepository,
        election_data_source: IElectionDataSourceService,
        import_service: ElectionImportService | None = None,
        party_membership_history_repository: (
            PartyMembershipHistoryRepository | None
        ) = None,
    ) -> None:
        self._election_repo = election_repository
        self._member_repo = election_member_repository
        self._politician_repo = politician_repository
        self._data_source = election_data_source
        self._import_service = import_service or ElectionImportService(
            politician_repository=politician_repository,
            political_party_repository=political_party_repository,
            election_repository=election_repository,
            party_membership_history_repository=party_membership_history_repository,
        )

        # 同一選挙内で処理済みのpolitician_idを追跡（重複ElectionMember防止）
        self._processed_politician_ids: set[int] = set()

    async def execute(
        self,
        input_dto: ImportNationalElectionInputDto,
    ) -> ImportNationalElectionOutputDto:
        """インポートを実行する."""
        self._processed_politician_ids.clear()
        self._import_service.clear_cache()
        output = ImportNationalElectionOutputDto(
            election_number=input_dto.election_number
        )

        # 1. データソースから候補者データを取得
        election_info, all_candidates = await self._data_source.fetch_candidates(
            input_dto.election_number,
        )

        if not all_candidates:
            logger.error("候補者データが取得できません")
            output.errors = 1
            output.error_details.append("候補者データの取得に失敗")
            return output

        election_date = election_info.election_date if election_info else None
        output.total_candidates = len(all_candidates)
        logger.info("合計 %d 候補者を取得", len(all_candidates))

        if input_dto.dry_run:
            logger.info("ドライラン: DB書き込みをスキップ")
            self._print_dry_run_report(all_candidates)
            return output

        # 2. Electionレコード作成
        election = await self._import_service.get_or_create_election(
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

        # 3. 各候補者を処理
        for candidate in all_candidates:
            try:
                await self._process_candidate(
                    candidate, election.id, output, election_date
                )
            except Exception:
                logger.exception("候補者処理失敗: %s", candidate.name)
                output.errors += 1
                output.error_details.append(f"候補者処理失敗: {candidate.name}")

        logger.info(
            "インポート完了: 候補者=%d, マッチ=%d, 新規政治家=%d, 新規政党=%d, "
            "曖昧スキップ=%d, 重複スキップ=%d, ElectionMember=%d, エラー=%d",
            output.total_candidates,
            output.matched_politicians,
            output.created_politicians,
            output.created_parties,
            output.skipped_ambiguous,
            output.skipped_duplicate,
            output.election_members_created,
            output.errors,
        )
        return output

    async def _process_candidate(
        self,
        candidate: CandidateRecord,
        election_id: int,
        output: ImportNationalElectionOutputDto,
        election_date: date | None = None,
    ) -> None:
        """候補者1名分の処理（政党解決→名寄せ→ElectionMember作成）."""
        # 政党を解決
        party, is_new_party = await self._import_service.resolve_party(
            candidate.party_name
        )
        party_id = party.id if party else None
        if is_new_party:
            output.created_parties += 1

        # 政治家を名寄せ
        politician, status = await self._import_service.match_politician(
            candidate.name, party_id, election_date=election_date
        )

        if status == "ambiguous":
            output.skipped_ambiguous += 1
            logger.warning(
                "同姓同名スキップ: %s (%s)", candidate.name, candidate.district_name
            )
            return

        if politician is None:
            # 新規作成
            politician = await self._import_service.create_politician(
                candidate.name,
                candidate.prefecture,
                candidate.district_name,
                party_id,
                election_date=election_date,
            )
            output.created_politicians += 1
        else:
            output.matched_politicians += 1

        if politician is None or politician.id is None:
            output.errors += 1
            output.error_details.append(f"政治家作成失敗: {candidate.name}")
            return

        # 同一選挙内で同じpoliticianのElectionMemberが既に作成済みの場合はスキップ
        if politician.id in self._processed_politician_ids:
            output.skipped_duplicate += 1
            logger.warning(
                "同一政治家の重複スキップ: %s (politician_id=%d, %s)",
                candidate.name,
                politician.id,
                candidate.district_name,
            )
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
        self._processed_politician_ids.add(politician.id)
        output.election_members_created += 1

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
