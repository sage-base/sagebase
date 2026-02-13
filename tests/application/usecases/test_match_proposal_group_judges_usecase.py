from unittest.mock import AsyncMock

import pytest

from src.application.dtos.match_proposal_group_judges_dto import (
    MatchProposalGroupJudgesInputDto,
    MatchProposalGroupJudgesOutputDto,
)
from src.application.usecases.match_proposal_group_judges_usecase import (
    MatchProposalGroupJudgesUseCase,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.domain.value_objects.judge_type import JudgeType


def _make_extracted_judge(
    judge_id: int,
    proposal_id: int,
    group_name: str,
    judgment: str,
) -> ExtractedProposalJudge:
    return ExtractedProposalJudge(
        id=judge_id,
        proposal_id=proposal_id,
        extracted_parliamentary_group_name=group_name,
        extracted_judgment=judgment,
        matching_status="pending",
    )


def _make_group(
    group_id: int, name: str, governing_body_id: int = 1
) -> ParliamentaryGroup:
    return ParliamentaryGroup(
        id=group_id,
        name=name,
        governing_body_id=governing_body_id,
    )


class TestMatchProposalGroupJudgesUseCase:
    @pytest.fixture
    def mock_extracted_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ExtractedProposalJudgeRepository)
        repo.get_all_pending = AsyncMock(return_value=[])
        repo.update_matching_result = AsyncMock(return_value=None)
        repo.mark_processed = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_group_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ParliamentaryGroupRepository)
        repo.get_by_governing_body_id = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_judge_repo(self) -> AsyncMock:
        repo = AsyncMock(spec=ProposalParliamentaryGroupJudgeRepository)
        repo.bulk_create = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def use_case(
        self,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
        mock_judge_repo: AsyncMock,
    ) -> MatchProposalGroupJudgesUseCase:
        return MatchProposalGroupJudgesUseCase(
            extracted_proposal_judge_repository=mock_extracted_repo,
            parliamentary_group_repository=mock_group_repo,
            proposal_group_judge_repository=mock_judge_repo,
        )

    @pytest.mark.asyncio
    async def test_no_pending_records(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
    ) -> None:
        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1)
        result = await use_case.execute(input_dto)

        assert result.total_pending == 0
        assert result.matched == 0
        assert result.unmatched == 0

    @pytest.mark.asyncio
    async def test_exact_name_match_with_gold_layer_verification(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
        mock_judge_repo: AsyncMock,
    ) -> None:
        judges = [
            _make_extracted_judge(1, 100, "自由民主党・無所属の会", "賛成"),
            _make_extracted_judge(2, 100, "公明党", "賛成"),
            _make_extracted_judge(3, 100, "立憲民主党・無所属", "反対"),
        ]
        mock_extracted_repo.get_all_pending.return_value = judges

        groups = [
            _make_group(8, "自由民主党・無所属の会"),
            _make_group(18, "公明党"),
            _make_group(9, "立憲民主党・無所属"),
        ]
        mock_group_repo.get_by_governing_body_id.return_value = groups

        created_judges = [
            ProposalParliamentaryGroupJudge(
                id=1,
                proposal_id=100,
                judgment="賛成",
                judge_type=JudgeType.PARLIAMENTARY_GROUP,
                parliamentary_group_ids=[8, 18],
            ),
            ProposalParliamentaryGroupJudge(
                id=2,
                proposal_id=100,
                judgment="反対",
                judge_type=JudgeType.PARLIAMENTARY_GROUP,
                parliamentary_group_ids=[9],
            ),
        ]
        mock_judge_repo.bulk_create.return_value = created_judges

        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1)
        result = await use_case.execute(input_dto)

        assert result.total_pending == 3
        assert result.matched == 3
        assert result.unmatched == 0
        assert result.judges_created == 2
        assert result.unmatched_names == []
        assert mock_extracted_repo.update_matching_result.call_count == 3

        mock_judge_repo.bulk_create.assert_called_once()
        entities = mock_judge_repo.bulk_create.call_args[0][0]
        assert len(entities) == 2

        sansei = [e for e in entities if e.judgment == "賛成"][0]
        assert sansei.proposal_id == 100
        assert sansei.judge_type == JudgeType.PARLIAMENTARY_GROUP
        assert sorted(sansei.parliamentary_group_ids) == [8, 18]

        hantai = [e for e in entities if e.judgment == "反対"][0]
        assert hantai.proposal_id == 100
        assert sorted(hantai.parliamentary_group_ids) == [9]

        assert mock_extracted_repo.mark_processed.call_count == 3
        processed_ids = sorted(
            call.args[0] for call in mock_extracted_repo.mark_processed.call_args_list
        )
        assert processed_ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_unmatched_group_names(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        judges = [
            _make_extracted_judge(1, 100, "存在しない会派", "賛成"),
            _make_extracted_judge(2, 100, "もう一つ不明な会派", "反対"),
        ]
        mock_extracted_repo.get_all_pending.return_value = judges
        mock_group_repo.get_by_governing_body_id.return_value = [
            _make_group(8, "自由民主党・無所属の会"),
        ]

        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1)
        result = await use_case.execute(input_dto)

        assert result.total_pending == 2
        assert result.matched == 0
        assert result.unmatched == 2
        assert "存在しない会派" in result.unmatched_names
        assert "もう一つ不明な会派" in result.unmatched_names

        # unmatched のステータス更新が呼ばれること
        assert mock_extracted_repo.update_matching_result.call_count == 2

    @pytest.mark.asyncio
    async def test_dry_run_skips_gold_layer(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
        mock_judge_repo: AsyncMock,
    ) -> None:
        judges = [_make_extracted_judge(1, 100, "公明党", "賛成")]
        mock_extracted_repo.get_all_pending.return_value = judges
        mock_group_repo.get_by_governing_body_id.return_value = [
            _make_group(18, "公明党"),
        ]

        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1, dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.matched == 1
        assert result.judges_created == 0
        mock_judge_repo.bulk_create.assert_not_called()
        mock_extracted_repo.mark_processed.assert_not_called()
        mock_extracted_repo.update_matching_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_records_without_group_name(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        pending = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=100,
                extracted_politician_name="山田太郎",
                extracted_parliamentary_group_name=None,
                extracted_judgment="賛成",
                matching_status="pending",
            ),
            _make_extracted_judge(2, 100, "公明党", "賛成"),
        ]
        mock_extracted_repo.get_all_pending.return_value = pending
        mock_group_repo.get_by_governing_body_id.return_value = [
            _make_group(18, "公明党"),
        ]

        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1, dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.total_pending == 1
        assert result.matched == 1

    @pytest.mark.asyncio
    async def test_mixed_matched_and_unmatched(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        judges = [
            _make_extracted_judge(1, 100, "公明党", "賛成"),
            _make_extracted_judge(2, 100, "未知の会派X", "反対"),
        ]
        mock_extracted_repo.get_all_pending.return_value = judges
        mock_group_repo.get_by_governing_body_id.return_value = [
            _make_group(18, "公明党"),
        ]

        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1, dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.matched == 1
        assert result.unmatched == 1
        assert result.unmatched_names == ["未知の会派X"]

    @pytest.mark.asyncio
    async def test_whitespace_in_group_name(
        self,
        use_case: MatchProposalGroupJudgesUseCase,
        mock_extracted_repo: AsyncMock,
        mock_group_repo: AsyncMock,
    ) -> None:
        judges = [_make_extracted_judge(1, 100, " 公明党 ", "賛成")]
        mock_extracted_repo.get_all_pending.return_value = judges
        mock_group_repo.get_by_governing_body_id.return_value = [
            _make_group(18, "公明党"),
        ]

        input_dto = MatchProposalGroupJudgesInputDto(governing_body_id=1, dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.matched == 1
        assert result.unmatched == 0


class TestMatchProposalGroupJudgesDtos:
    def test_input_dto_defaults(self) -> None:
        dto = MatchProposalGroupJudgesInputDto(governing_body_id=1)
        assert dto.dry_run is False

    def test_output_dto_defaults(self) -> None:
        dto = MatchProposalGroupJudgesOutputDto()
        assert dto.total_pending == 0
        assert dto.matched == 0
        assert dto.unmatched == 0
        assert dto.judges_created == 0
        assert dto.unmatched_names == []
