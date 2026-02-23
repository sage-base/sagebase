"""参議院選挙データインポートユースケース.

SmartNews SMRI の giin.json から参議院議員データを読み込み、
選挙回次ごとにElection・ElectionMemberレコードを作成する。

処理フロー:
    1. データソースから議員データ取得
    2. 各議員の当選年を回次に変換
    3. 回次ごとにElectionレコード作成（冪等性: 既存メンバーを削除して再作成）
    4. 各議員について名寄せ + ElectionMember作成
    5. レポート出力
"""

import logging

from datetime import date

from src.application.dtos.sangiin_election_import_dto import (
    ImportSangiinElectionInputDto,
    ImportSangiinElectionOutputDto,
)
from src.application.services.election_import_service import ElectionImportService
from src.domain.entities.election import Election
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
from src.domain.services.interfaces.sangiin_election_data_source_service import (
    ISangiinElectionDataSourceService,
)
from src.domain.value_objects.sangiin_candidate import SangiinCandidateRecord


logger = logging.getLogger(__name__)

# 参議院通常選挙の回次 → 選挙年 対応表
SANGIIN_ELECTION_YEARS: dict[int, int] = {
    26: 2022,
    25: 2019,
    24: 2016,
    23: 2013,
    22: 2010,
    21: 2007,
    20: 2004,
    19: 2001,
}

# 逆引き: 選挙年 → 回次
_YEAR_TO_TERM: dict[int, int] = {v: k for k, v in SANGIIN_ELECTION_YEARS.items()}


class ImportSangiinElectionUseCase:
    """参議院選挙データインポートのユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        politician_repository: PoliticianRepository,
        political_party_repository: PoliticalPartyRepository,
        data_source: ISangiinElectionDataSourceService,
        import_service: ElectionImportService | None = None,
        party_membership_history_repository: (
            PartyMembershipHistoryRepository | None
        ) = None,
    ) -> None:
        self._election_repo = election_repository
        self._member_repo = election_member_repository
        self._politician_repo = politician_repository
        self._data_source = data_source
        self._import_service = import_service or ElectionImportService(
            politician_repository=politician_repository,
            political_party_repository=political_party_repository,
            election_repository=election_repository,
            party_membership_history_repository=party_membership_history_repository,
        )

        # 回次ごとに処理済みのpolitician_idを追跡（重複ElectionMember防止）
        self._processed_politician_ids: dict[int, set[int]] = {}

    async def execute(
        self,
        input_dto: ImportSangiinElectionInputDto,
    ) -> ImportSangiinElectionOutputDto:
        """インポートを実行する."""
        self._processed_politician_ids.clear()
        self._import_service.clear_cache()
        output = ImportSangiinElectionOutputDto()

        # 1. データソースから議員データを取得
        councillors = await self._data_source.fetch_councillors(input_dto.file_path)

        if not councillors:
            logger.error("議員データが取得できません")
            output.errors = 1
            output.error_details.append("議員データの取得に失敗")
            return output

        output.total_councillors = len(councillors)
        logger.info("合計 %d 名の議員データを取得", len(councillors))

        if input_dto.dry_run:
            logger.info("ドライラン: DB書き込みをスキップ")
            self._print_dry_run_report(councillors)
            return output

        # 2. 回次ごとにElectionレコードを準備
        election_cache: dict[int, Election] = {}

        # 3. 各議員を処理
        for councillor in councillors:
            try:
                await self._process_councillor(
                    councillor,
                    input_dto.governing_body_id,
                    election_cache,
                    output,
                )
            except Exception:
                logger.exception("議員処理失敗: %s", councillor.name)
                output.errors += 1
                output.error_details.append(f"議員処理失敗: {councillor.name}")

        logger.info(
            "インポート完了: 議員=%d, 選挙作成=%d, マッチ=%d, 新規政治家=%d, "
            "新規政党=%d, 曖昧スキップ=%d, 重複スキップ=%d, ElectionMember=%d, "
            "エラー=%d",
            output.total_councillors,
            output.elections_created,
            output.matched_politicians,
            output.created_politicians,
            output.created_parties,
            output.skipped_ambiguous,
            output.skipped_duplicate,
            output.election_members_created,
            output.errors,
        )
        return output

    async def _process_councillor(
        self,
        councillor: SangiinCandidateRecord,
        governing_body_id: int,
        election_cache: dict[int, Election],
        output: ImportSangiinElectionOutputDto,
    ) -> None:
        """議員1名分の処理（当選年ごとにElectionMemberを作成）."""
        # 政党を解決
        party, is_new_party = await self._import_service.resolve_party(
            councillor.party_name
        )
        party_id = party.id if party else None
        if is_new_party:
            output.created_parties += 1

        # 最も新しい当選年から election_date を算出
        # match_politician / create_politician で所属履歴の参照・作成に使用する。
        # create_politician は1議員につき1回のみ呼ばれるため、
        # 所属履歴もこの最新当選年1回分のみ作成される（意図通りの動作）。
        latest_year = (
            max(councillor.elected_years) if councillor.elected_years else None
        )
        election_date_for_match = (
            date(latest_year, 7, 1) if latest_year is not None else None
        )

        # 政治家を名寄せ
        politician, status = await self._import_service.match_politician(
            councillor.name, party_id, election_date=election_date_for_match
        )

        if status == "ambiguous":
            output.skipped_ambiguous += 1
            logger.warning(
                "同姓同名スキップ: %s (%s)", councillor.name, councillor.district_name
            )
            return

        if politician is None:
            # 新規作成（参議院は都道府県名がdistrictに入る）
            prefecture = "" if councillor.is_proportional else councillor.district_name
            politician = await self._import_service.create_politician(
                councillor.name,
                prefecture,
                councillor.district_name,
                party_id,
                election_date=election_date_for_match,
            )
            output.created_politicians += 1
        else:
            output.matched_politicians += 1

        if politician is None or politician.id is None:
            output.errors += 1
            output.error_details.append(f"政治家作成失敗: {councillor.name}")
            return

        # 各当選年について回次を特定し、ElectionMemberを作成
        for elected_year in councillor.elected_years:
            term_number = _YEAR_TO_TERM.get(elected_year)
            if term_number is None:
                logger.debug(
                    "当選年 %d は対応表にないためスキップ: %s",
                    elected_year,
                    councillor.name,
                )
                continue

            # Election取得/作成
            election = await self._get_or_create_election(
                term_number,
                elected_year,
                governing_body_id,
                election_cache,
                output,
            )
            if election is None or election.id is None:
                output.errors += 1
                output.error_details.append(
                    f"Election作成失敗: 第{term_number}回 ({councillor.name})"
                )
                continue

            # 同一回次内で同じpoliticianの重複チェック
            if term_number not in self._processed_politician_ids:
                self._processed_politician_ids[term_number] = set()

            if politician.id in self._processed_politician_ids[term_number]:
                output.skipped_duplicate += 1
                logger.warning(
                    "同一回次内の重複スキップ: %s (第%d回, politician_id=%d)",
                    councillor.name,
                    term_number,
                    politician.id,
                )
                continue

            # ElectionMember作成
            result = (
                ElectionMember.RESULT_PROPORTIONAL_ELECTED
                if councillor.is_proportional
                else ElectionMember.RESULT_ELECTED
            )
            member = ElectionMember(
                election_id=election.id,
                politician_id=politician.id,
                result=result,
            )
            await self._member_repo.create(member)
            self._processed_politician_ids[term_number].add(politician.id)
            output.election_members_created += 1

    async def _get_or_create_election(
        self,
        term_number: int,
        elected_year: int,
        governing_body_id: int,
        cache: dict[int, Election],
        output: ImportSangiinElectionOutputDto,
    ) -> Election | None:
        """回次に対応するElectionレコードを取得/作成する."""
        if term_number in cache:
            return cache[term_number]

        # 選挙日は7/1をデフォルトとする（参議院選挙は通常7月実施）
        election_date = date(elected_year, 7, 1)

        # 新規作成かどうかを判定するため、事前に既存レコードを確認
        existing = await self._election_repo.get_by_governing_body_and_term(
            governing_body_id, term_number
        )
        is_new = existing is None

        election = await self._import_service.get_or_create_election(
            governing_body_id,
            term_number,
            election_date,
            election_type=Election.ELECTION_TYPE_SANGIIN,
        )
        if election is not None:
            # 初回取得時に既存メンバーを削除（冪等性のため）
            if election.id is not None:
                deleted = await self._member_repo.delete_by_election_id(election.id)
                if deleted > 0:
                    logger.info(
                        "第%d回: 既存のElectionMember %d件を削除",
                        term_number,
                        deleted,
                    )
            cache[term_number] = election
            if is_new:
                output.elections_created += 1

        return election

    def _print_dry_run_report(self, councillors: list[SangiinCandidateRecord]) -> None:
        """ドライラン時のレポートを出力する."""
        parties = {c.party_name for c in councillors if c.party_name}
        districts = {c.district_name for c in councillors}
        proportional = [c for c in councillors if c.is_proportional]
        constituency = [c for c in councillors if not c.is_proportional]

        # 当選年から対応する回次を集計
        term_numbers: set[int] = set()
        for c in councillors:
            for year in c.elected_years:
                term = _YEAR_TO_TERM.get(year)
                if term is not None:
                    term_numbers.add(term)

        logger.info("--- ドライランレポート ---")
        logger.info("議員数: %d", len(councillors))
        logger.info("選挙区議員: %d", len(constituency))
        logger.info("比例議員: %d", len(proportional))
        logger.info("選挙区数: %d", len(districts))
        logger.info("対応回次: %s", sorted(term_numbers))
        logger.info("会派数: %d", len(parties))
        logger.info("会派名: %s", ", ".join(sorted(parties)))
