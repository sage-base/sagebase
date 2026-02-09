import json
import tempfile

from pathlib import Path
from typing import Any

import pytest

from src.infrastructure.importers.smartnews_smri_importer import (
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
        return SmartNewsSmriImporter(governing_body_id=1)

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

    def test_parse_unknown_result_returns_other(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        record = _make_record(result="不明な結果")
        proposal = importer.parse_record(record)
        assert proposal.deliberation_result == "other"

    def test_parse_result_with_trailing_space(
        self, importer: SmartNewsSmriImporter
    ) -> None:
        record = _make_record(result="衆議院回付案(同意) ")
        proposal = importer.parse_record(record)
        assert proposal.deliberation_result == "passed"


class TestLoadJson:
    def test_load_json_file(self) -> None:
        importer = SmartNewsSmriImporter(governing_body_id=1)
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

    def test_load_json_file_not_found(self) -> None:
        importer = SmartNewsSmriImporter(governing_body_id=1)
        with pytest.raises(FileNotFoundError):
            importer.load_json(Path("/nonexistent/file.json"))

    def test_load_json_invalid_json(self) -> None:
        importer = SmartNewsSmriImporter(governing_body_id=1)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write("not valid json")
            f.flush()
            with pytest.raises(json.JSONDecodeError):
                importer.load_json(Path(f.name))
