import json
import tempfile

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.proposal import Proposal
from src.infrastructure.importers.smartnews_smri_importer import (
    CATEGORY_MAP,
    RESULT_MAP,
    ImportResult,
    SmartNewsSmriImporter,
)


def _make_record(
    proposal_type: str = "衆法",
    session_number: str = "200",
    proposal_number: str = "42",
    title: str = "テスト法案",
    current_session: str = "200",
    result: str = "成立",
    proposer: str = "提出者",
    parties: str = "政党A",
    supporter: str = "",
    opponent: str = "",
    url: str = "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/keika/TEST.htm",
) -> list[Any]:
    return [
        proposal_type,
        session_number,
        proposal_number,
        title,
        current_session,
        result,
        proposer,
        parties,
        supporter,
        opponent,
        [
            [
                current_session,
                result,
                "経過",
                url,
                "",
                "",
                proposal_type,
                *[""] * 16,
            ]
        ],
    ]


class TestSmartNewsSmriImporterParseRecord:
    @pytest.fixture
    def importer(self) -> SmartNewsSmriImporter:
        repo = AsyncMock()
        return SmartNewsSmriImporter(
            proposal_repository=repo,
            governing_body_id=1,
        )

    def test_parse_basic_record(self, importer: SmartNewsSmriImporter) -> None:
        record = _make_record()
        proposal = importer.parse_record(record)

        assert proposal.title == "テスト法案"
        assert proposal.proposal_type == "衆法"
        assert proposal.proposal_category == "legislation"
        assert proposal.session_number == 200
        assert proposal.proposal_number == 42
        assert proposal.governing_body_id == 1
        assert proposal.deliberation_result == "passed"
        assert proposal.external_id == (
            "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/keika/TEST.htm"
        )
        assert proposal.detail_url == proposal.external_id

    def test_parse_record_without_proposal_number(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        record = _make_record(proposal_type="予算", proposal_number="")
        proposal = importer.parse_record(record)

        assert proposal.proposal_number is None
        assert proposal.proposal_category == "budget"
        assert not proposal.has_business_key

    def test_parse_record_empty_type(self, importer: SmartNewsSmriImporter) -> None:
        record = _make_record(proposal_type="", proposal_number="")
        proposal = importer.parse_record(record)

        assert proposal.proposal_type is None
        assert proposal.proposal_category == "other"

    def test_parse_record_empty_result(self, importer: SmartNewsSmriImporter) -> None:
        record = _make_record(result="")
        proposal = importer.parse_record(record)

        assert proposal.deliberation_result is None

    def test_parse_record_no_url(self, importer: SmartNewsSmriImporter) -> None:
        record = _make_record(url="")
        proposal = importer.parse_record(record)

        assert proposal.external_id is None

    def test_parse_record_malformed_nested(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        record: list[Any] = [
            "衆法",
            "200",
            "1",
            "テスト",
            "200",
            "成立",
            "",
            "",
            "",
            "",
            [],
        ]
        proposal = importer.parse_record(record)

        assert proposal.external_id is None
        assert proposal.title == "テスト"

    def test_parse_various_category_mappings(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        for raw_type, expected in [
            ("条約", "treaty"),
            ("承認", "approval"),
            ("承諾", "approval"),
            ("決算", "audit"),
            ("国有財産", "audit"),
            ("ＮＨＫ決算", "audit"),
            ("決議", "other"),
        ]:
            record = _make_record(proposal_type=raw_type)
            proposal = importer.parse_record(record)
            assert proposal.proposal_category == expected, f"{raw_type} -> {expected}"

    def test_parse_various_result_mappings(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        for raw_result, expected in [
            ("未了", "expired"),
            ("撤回", "withdrawn"),
            ("衆議院で閉会中審査", "pending"),
            ("両院の意見が一致しない旨報告", "rejected"),
        ]:
            record = _make_record(result=raw_result)
            proposal = importer.parse_record(record)
            assert proposal.deliberation_result == expected, (
                f"{raw_result} -> {expected}"
            )

    def test_parse_unknown_result_returns_none(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        record = _make_record(result="不明な結果")
        proposal = importer.parse_record(record)
        assert proposal.deliberation_result is None


class TestCategoryMapping:
    def test_all_known_types_mapped(self) -> None:
        known_types = [
            "衆法",
            "閣法",
            "参法",
            "予算",
            "条約",
            "承認",
            "承諾",
            "決算",
            "国有財産",
            "ＮＨＫ決算",
            "決議",
            "規程",
            "規則",
            "議決",
            "国庫債務",
            "憲法八条議決案",
        ]
        for t in known_types:
            assert t in CATEGORY_MAP, f"{t} not in CATEGORY_MAP"

    def test_legislation_mapping(self) -> None:
        for t in ["衆法", "閣法", "参法"]:
            assert CATEGORY_MAP[t] == "legislation"

    def test_budget_mapping(self) -> None:
        assert CATEGORY_MAP["予算"] == "budget"

    def test_treaty_mapping(self) -> None:
        assert CATEGORY_MAP["条約"] == "treaty"

    def test_approval_mapping(self) -> None:
        for t in ["承認", "承諾"]:
            assert CATEGORY_MAP[t] == "approval"

    def test_audit_mapping(self) -> None:
        for t in ["決算", "国有財産", "ＮＨＫ決算"]:
            assert CATEGORY_MAP[t] == "audit"

    def test_other_mapping(self) -> None:
        for t in [
            "決議",
            "規程",
            "規則",
            "議決",
            "国庫債務",
            "憲法八条議決案",
        ]:
            assert CATEGORY_MAP[t] == "other"

    def test_unknown_type_defaults_to_other(self) -> None:
        assert CATEGORY_MAP.get("不明な種類", "other") == "other"


class TestResultNormalization:
    def test_passed_results(self) -> None:
        passed_originals = [
            "成立",
            "本院議了",
            "両院承認",
            "両院承諾",
            "本院可決",
            "参議院回付案（同意）",
            "衆議院議決案（可決）",
            "参議院議了",
            "両院議決",
            "承認",
            "修正承諾",
            "撤回承諾",
            "議決不要",
            "本院修正議決",
        ]
        for r in passed_originals:
            assert RESULT_MAP[r] == "passed", f"{r} should map to passed"

    def test_expired_result(self) -> None:
        assert RESULT_MAP["未了"] == "expired"

    def test_withdrawn_result(self) -> None:
        assert RESULT_MAP["撤回"] == "withdrawn"

    def test_pending_results(self) -> None:
        for r in [
            "衆議院で閉会中審査",
            "参議院で閉会中審査",
            "中間報告",
        ]:
            assert RESULT_MAP[r] == "pending"

    def test_rejected_results(self) -> None:
        for r in [
            "両院の意見が一致しない旨報告",
            "参議院回付案（不同意）",
            "承諾なし",
        ]:
            assert RESULT_MAP[r] == "rejected"

    def test_empty_result_not_in_map(self) -> None:
        assert "" not in RESULT_MAP


class TestLoadJson:
    def test_load_json_file(self) -> None:
        repo = AsyncMock()
        importer = SmartNewsSmriImporter(proposal_repository=repo, governing_body_id=1)
        data = [_make_record(), _make_record(title="法案2")]

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = importer.load_json(Path(f.name))

        assert len(result) == 2
        assert result[0][3] == "テスト法案"
        assert result[1][3] == "法案2"


class TestImportData:
    @pytest.fixture
    def mock_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.find_by_identifier = AsyncMock(return_value=None)
        repo.find_by_url = AsyncMock(return_value=None)
        repo.create = AsyncMock(
            side_effect=lambda p: Proposal(
                title=p.title,
                id=1,
            )
        )
        return repo

    @pytest.fixture
    def importer(self, mock_repo: AsyncMock) -> SmartNewsSmriImporter:
        return SmartNewsSmriImporter(
            proposal_repository=mock_repo,
            governing_body_id=1,
        )

    @pytest.mark.asyncio
    async def test_import_creates_proposals(
        self,
        importer: SmartNewsSmriImporter,
        mock_repo: AsyncMock,
    ) -> None:
        records = [
            _make_record(),
            _make_record(title="法案2"),
        ]
        result = await importer.import_data(records, batch_size=10)

        assert result.total == 2
        assert result.created == 2
        assert result.skipped == 0
        assert result.errors == 0
        assert mock_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_import_skips_duplicates_by_identifier(
        self,
        importer: SmartNewsSmriImporter,
        mock_repo: AsyncMock,
    ) -> None:
        existing = Proposal(title="既存", id=99)
        mock_repo.find_by_identifier.return_value = existing

        records = [_make_record()]
        result = await importer.import_data(records, batch_size=10)

        assert result.skipped == 1
        assert result.created == 0
        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_skips_duplicates_by_url(
        self,
        importer: SmartNewsSmriImporter,
        mock_repo: AsyncMock,
    ) -> None:
        existing = Proposal(title="既存", id=99)
        mock_repo.find_by_url.return_value = existing

        record = _make_record(proposal_number="")
        records = [record]
        result = await importer.import_data(records, batch_size=10)

        assert result.skipped == 1
        assert result.created == 0

    @pytest.mark.asyncio
    async def test_import_handles_errors(
        self,
        importer: SmartNewsSmriImporter,
        mock_repo: AsyncMock,
    ) -> None:
        mock_repo.create.side_effect = Exception("DB error")

        records = [_make_record()]
        result = await importer.import_data(records, batch_size=10)

        assert result.errors == 1
        assert result.created == 0

    @pytest.mark.asyncio
    async def test_import_batch_processing(
        self,
        importer: SmartNewsSmriImporter,
        mock_repo: AsyncMock,
    ) -> None:
        records = [_make_record(title=f"法案{i}") for i in range(5)]
        result = await importer.import_data(records, batch_size=2)

        assert result.total == 5
        assert result.created == 5

    @pytest.mark.asyncio
    async def test_import_empty_records(self, importer: SmartNewsSmriImporter) -> None:
        result = await importer.import_data([], batch_size=10)

        assert result.total == 0
        assert result.created == 0


class TestImportResult:
    def test_default_values(self) -> None:
        result = ImportResult()
        assert result.total == 0
        assert result.created == 0
        assert result.skipped == 0
        assert result.errors == 0
