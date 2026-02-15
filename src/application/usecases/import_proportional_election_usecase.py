"""比例代表選挙データインポートユースケース.

外部データソースからパースした比例代表候補者データをDBにインポートする。

処理フロー:
    1. データソースから比例代表候補者データ取得
    2. Electionレコード作成（冪等性: 既存の場合はメンバーを削除して再作成）
    3. 各候補者について名寄せ + ElectionMember作成
    4. レポート出力

比例復活当選の判定ロジック:
    - smd_result == "当" → スキップ（小選挙区当選者、比例レコード不要）
    - smd_result == "落" + is_elected → result="比例復活"
    - smd_result == "" + is_elected → result="比例当選"
"""

import logging

from src.application.dtos.proportional_election_import_dto import (
    ImportProportionalElectionInputDto,
    ImportProportionalElectionOutputDto,
)
from src.application.services.election_import_service import ElectionImportService
from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.proportional_election_data_source_service import (
    IProportionalElectionDataSourceService,
)
from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
)


logger = logging.getLogger(__name__)


class ImportProportionalElectionUseCase:
    """比例代表選挙データインポートのユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        politician_repository: PoliticianRepository,
        political_party_repository: PoliticalPartyRepository,
        proportional_data_source: IProportionalElectionDataSourceService,
        import_service: ElectionImportService | None = None,
    ) -> None:
        self._election_repo = election_repository
        self._member_repo = election_member_repository
        self._politician_repo = politician_repository
        self._data_source = proportional_data_source
        self._import_service = import_service or ElectionImportService(
            politician_repository=politician_repository,
            political_party_repository=political_party_repository,
            election_repository=election_repository,
        )

        self._processed_politician_ids: set[int] = set()
        self._existing_members_by_politician: dict[int, ElectionMember] = {}

    async def execute(
        self,
        input_dto: ImportProportionalElectionInputDto,
    ) -> ImportProportionalElectionOutputDto:
        """インポートを実行する."""
        self._processed_politician_ids.clear()
        self._import_service.clear_cache()
        output = ImportProportionalElectionOutputDto(
            election_number=input_dto.election_number
        )

        # 1. データソースから比例代表候補者データを取得
        (
            election_info,
            all_candidates,
        ) = await self._data_source.fetch_proportional_candidates(
            input_dto.election_number,
        )

        if not all_candidates:
            logger.error("比例代表候補者データが取得できません")
            output.errors = 1
            output.error_details.append("比例代表候補者データの取得に失敗")
            return output

        # 当選者のみをフィルタリング
        elected = [c for c in all_candidates if c.is_elected]
        output.total_candidates = len(all_candidates)
        output.elected_candidates = len(elected)
        logger.info(
            "合計 %d 候補者を取得（当選者 %d 名）",
            len(all_candidates),
            len(elected),
        )

        if input_dto.dry_run:
            logger.info("ドライラン: DB書き込みをスキップ")
            self._print_dry_run_report(all_candidates, elected)
            return output

        election_date = election_info.election_date if election_info else None

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

        # 既存の比例代表メンバーのみ削除（冪等性のため）
        # 小選挙区メンバーは保持する
        proportional_results = [
            ElectionMember.RESULT_PROPORTIONAL_ELECTED,
            ElectionMember.RESULT_PROPORTIONAL_REVIVAL,
        ]
        deleted_count = await self._member_repo.delete_by_election_id_and_results(
            election.id, proportional_results
        )
        if deleted_count > 0:
            logger.info("既存の比例代表ElectionMember %d件を削除", deleted_count)

        # 既存メンバーをキャッシュ（小選挙区メンバーとの重複チェック用）
        existing_members = await self._member_repo.get_by_election_id(election.id)
        self._existing_members_by_politician = {
            m.politician_id: m for m in existing_members if m.politician_id
        }

        # 3. 当選者を処理
        for candidate in elected:
            try:
                await self._process_candidate(candidate, election.id, output)
            except Exception:
                logger.exception("候補者処理失敗: %s", candidate.name)
                output.errors += 1
                output.error_details.append(f"候補者処理失敗: {candidate.name}")

        logger.info(
            "比例代表インポート完了: 候補者=%d, 当選=%d, 比例当選=%d, "
            "比例復活=%d, マッチ=%d, 新規政治家=%d, 新規政党=%d, "
            "小選挙区当選スキップ=%d, 曖昧スキップ=%d, 重複スキップ=%d, "
            "ElectionMember=%d, エラー=%d",
            output.total_candidates,
            output.elected_candidates,
            output.proportional_elected,
            output.proportional_revival,
            output.matched_politicians,
            output.created_politicians,
            output.created_parties,
            output.skipped_smd_winner,
            output.skipped_ambiguous,
            output.skipped_duplicate,
            output.election_members_created,
            output.errors,
        )
        return output

    async def _process_candidate(
        self,
        candidate: ProportionalCandidateRecord,
        election_id: int,
        output: ImportProportionalElectionOutputDto,
    ) -> None:
        """候補者1名分の処理."""
        # 小選挙区当選者はスキップ（比例レコード不要）
        if candidate.smd_result == "当":
            output.skipped_smd_winner += 1
            logger.debug(
                "小選挙区当選者スキップ: %s (%s)", candidate.name, candidate.block_name
            )
            return

        # 政党を解決
        party, is_new_party = await self._import_service.resolve_party(
            candidate.party_name
        )
        party_id = party.id if party else None
        if is_new_party:
            output.created_parties += 1

        # 政治家を名寄せ
        politician, status = await self._import_service.match_politician(
            candidate.name, party_id
        )

        if status == "ambiguous":
            output.skipped_ambiguous += 1
            logger.warning(
                "同姓同名スキップ: %s (%s)", candidate.name, candidate.block_name
            )
            return

        if politician is None:
            # 新規作成
            politician = await self._import_service.create_politician(
                candidate.name, "", candidate.block_name, party_id
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
                candidate.block_name,
            )
            return

        # 比例復活 vs 比例当選の判定
        if candidate.smd_result == "落":
            result = ElectionMember.RESULT_PROPORTIONAL_REVIVAL
            output.proportional_revival += 1
        else:
            result = ElectionMember.RESULT_PROPORTIONAL_ELECTED
            output.proportional_elected += 1

        # 小選挙区インポートで既にElectionMemberが存在する場合はresultを更新
        existing_member = self._existing_members_by_politician.get(politician.id)
        if existing_member is not None:
            existing_member.result = result
            existing_member.rank = (
                candidate.list_order if candidate.list_order > 0 else None
            )
            await self._member_repo.update(existing_member)
            logger.debug("既存ElectionMemberを更新: %s → %s", candidate.name, result)
        else:
            member = ElectionMember(
                election_id=election_id,
                politician_id=politician.id,
                result=result,
                rank=candidate.list_order if candidate.list_order > 0 else None,
            )
            await self._member_repo.create(member)
        self._processed_politician_ids.add(politician.id)
        output.election_members_created += 1

    def _print_dry_run_report(
        self,
        all_candidates: list[ProportionalCandidateRecord],
        elected: list[ProportionalCandidateRecord],
    ) -> None:
        """ドライラン時のレポートを出力する."""
        blocks = {c.block_name for c in all_candidates}
        parties = {c.party_name for c in all_candidates if c.party_name}
        smd_winners = [c for c in elected if c.smd_result == "当"]
        revivals = [c for c in elected if c.smd_result == "落"]
        pure_proportional = [c for c in elected if c.smd_result == ""]

        logger.info("--- ドライランレポート（比例代表） ---")
        logger.info("ブロック数: %d", len(blocks))
        logger.info("総候補者数: %d", len(all_candidates))
        logger.info("当選者数: %d", len(elected))
        logger.info("  比例単独当選: %d", len(pure_proportional))
        logger.info("  比例復活当選: %d", len(revivals))
        logger.info("  小選挙区当選（スキップ対象）: %d", len(smd_winners))
        logger.info("政党数: %d", len(parties))
        logger.info("政党名: %s", ", ".join(sorted(parties)))
