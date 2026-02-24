"""SmartNewsSmriSangiinGianImporterのテスト."""

import json
import tempfile

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.importers.smartnews_smri_sangiin_gian_importer import (
    SmartNewsSmriSangiinGianImporter,
)


def _make_row(
    session_number: str = "153",
    proposal_type: str = "法律案（内閣提出）",
    submission_session: str = "153",
    proposal_number: str = "1",
    title: str = "テスト法案",
    gian_url: str = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/153/meisai/m15303153001.htm",
    summary_url: str = "",
    submitted_law: str = "",
    submitted_date: str = "2001-09-28",
    received_date: str = "",
    sent_date: str = "",
    priority: str = "",
    continuation: str = "",
    initiator: str = "",
    submitter: str = "",
    submitter_type: str = "",
    committee_referral_date: str = "",
    committee_name: str = "",
    committee_vote_date: str = "",
    committee_result: str = "",
    plenary_vote_date: str = "2001-11-09",
    plenary_result: str = "可決",
    committee_member: str = "",
    vote_manner: str = "多数",
    vote_method: str = "押しボタン",
    vote_result_url: str = "",
    hor_committee_date: str = "",
    hor_committee_name: str = "",
    hor_committee_vote_date: str = "",
    hor_committee_result: str = "",
    hor_plenary_vote_date: str = "",
    hor_plenary_result: str = "",
    hor_committee_member: str = "",
    hor_vote_manner: str = "",
    hor_vote_method: str = "",
    promulgation_date: str = "",
    law_number: str = "",
    enacted_law: str = "",
    remarks: str = "",
) -> list[Any]:
    """テスト用の参議院gian.jsonデータ行を作成する."""
    return [
        session_number,
        proposal_type,
        submission_session,
        proposal_number,
        title,
        gian_url,
        summary_url,
        submitted_law,
        submitted_date,
        received_date,
        sent_date,
        priority,
        continuation,
        initiator,
        submitter,
        submitter_type,
        committee_referral_date,
        committee_name,
        committee_vote_date,
        committee_result,
        plenary_vote_date,
        plenary_result,
        committee_member,
        vote_manner,
        vote_method,
        vote_result_url,
        hor_committee_date,
        hor_committee_name,
        hor_committee_vote_date,
        hor_committee_result,
        hor_plenary_vote_date,
        hor_plenary_result,
        hor_committee_member,
        hor_vote_manner,
        hor_vote_method,
        promulgation_date,
        law_number,
        enacted_law,
        remarks,
    ]


HEADER_ROW = [
    "審議回次",
    "種類",
    "提出回次",
    "提出番号",
    "件名",
    "議案URL",
    "議案要旨",
    "提出法律案",
    "議案審議情報一覧 - 提出日",
    "議案審議情報一覧 - 衆議院から受領／提出日",
    "議案審議情報一覧 - 衆議院へ送付／提出日",
    "議案審議情報一覧 - 先議区分",
    "議案審議情報一覧 - 継続区分",
    "議案審議情報一覧 - 発議者",
    "議案審議情報一覧 - 提出者",
    "議案審議情報一覧 - 提出者区分",
    "参議院委員会等経過情報 - 本付託日",
    "参議院委員会等経過情報 - 付託委員会等",
    "参議院委員会等経過情報 - 議決日",
    "参議院委員会等経過情報 - 議決・継続結果",
    "参議院本会議経過情報 - 議決日",
    "参議院本会議経過情報 - 議決",
    "参議院本会議経過情報 - 委員名",
    "参議院本会議経過情報 - 採決態様",
    "参議院本会議経過情報 - 採決方法",
    "参議院本会議経過情報 - 投票結果",
    "衆議院委員会等経過情報 - 本付託日",
    "衆議院委員会等経過情報 - 付託委員会等",
    "衆議院委員会等経過情報 - 議決日",
    "衆議院委員会等経過情報 - 議決・継続結果",
    "衆議院本会議経過情報 - 議決日",
    "衆議院本会議経過情報 - 議決",
    "衆議院本会議経過情報 - 委員名",
    "衆議院本会議経過情報 - 採決態様",
    "衆議院本会議経過情報 - 採決方法",
    "その他の情報 - 公布年月日",
    "その他の情報 - 法律番号",
    "成立法律",
    "備考",
]


class TestSmartNewsSmriSangiinGianImporterLoadJson:
    def test_load_json_skip_header(self) -> None:
        """ヘッダー行をスキップしてデータ行のみ返すことを確認."""
        data = [HEADER_ROW, _make_row(title="法案1"), _make_row(title="法案2")]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            importer = SmartNewsSmriSangiinGianImporter(
                governing_body_id=1, conference_id=10
            )
            rows = importer.load_json(Path(f.name))
            assert len(rows) == 2
            assert rows[0][4] == "法案1"

    def test_load_json_empty_data(self) -> None:
        """ヘッダーのみの場合は空リストを返すことを確認."""
        data = [HEADER_ROW]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            importer = SmartNewsSmriSangiinGianImporter(
                governing_body_id=1, conference_id=10
            )
            rows = importer.load_json(Path(f.name))
            assert rows == []


class TestSmartNewsSmriSangiinGianImporterParseRecord:
    @pytest.fixture
    def importer(self) -> SmartNewsSmriSangiinGianImporter:
        return SmartNewsSmriSangiinGianImporter(governing_body_id=1, conference_id=10)

    def test_parse_basic_record(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row()
        proposal = importer.parse_record(row)

        assert proposal.title == "テスト法案"
        assert proposal.proposal_type == "法律案（内閣提出）"
        assert proposal.proposal_category == "legislation"
        assert proposal.session_number == 153
        assert proposal.proposal_number == 1
        assert proposal.governing_body_id == 1
        assert proposal.conference_id == 10
        assert proposal.deliberation_result == "passed"
        assert proposal.deliberation_status == "可決"
        assert proposal.submitted_date == date(2001, 9, 28)
        assert proposal.voted_date == date(2001, 11, 9)
        assert proposal.external_id == (
            "https://www.sangiin.go.jp/japanese/joho1/kousei/gian"
            "/153/meisai/m15303153001.htm"
        )

    def test_parse_record_rejected(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(plenary_result="否決")
        proposal = importer.parse_record(row)

        assert proposal.deliberation_result == "rejected"
        assert proposal.deliberation_status == "否決"

    def test_parse_record_modified(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(plenary_result="修正")
        proposal = importer.parse_record(row)

        assert proposal.deliberation_result == "passed"

    def test_parse_record_empty_result(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(plenary_result="")
        proposal = importer.parse_record(row)

        assert proposal.deliberation_result is None
        assert proposal.deliberation_status is None

    def test_parse_record_empty_dates(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(submitted_date="", plenary_vote_date="")
        proposal = importer.parse_record(row)

        assert proposal.submitted_date is None
        assert proposal.voted_date is None

    def test_parse_record_no_url(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(gian_url="")
        proposal = importer.parse_record(row)

        assert proposal.external_id is None
        assert proposal.detail_url is None

    def test_parse_record_sangiin_legislation(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(proposal_type="法律案（参議院提出）")
        proposal = importer.parse_record(row)

        assert proposal.proposal_category == "legislation"

    def test_parse_record_unknown_category(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(proposal_type="未知の種類")
        proposal = importer.parse_record(row)

        assert proposal.proposal_category == "other"

    def test_parse_record_empty_title_raises(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(title="")
        with pytest.raises(ValueError, match="件名が空です"):
            importer.parse_record(row)


class TestSmartNewsSmriSangiinGianImporterParseSubmitter:
    @pytest.fixture
    def importer(self) -> SmartNewsSmriSangiinGianImporter:
        return SmartNewsSmriSangiinGianImporter(governing_body_id=1, conference_id=10)

    def test_parse_submitter_politician(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(submitter="山田太郎", submitter_type="議員")
        submitter = importer.parse_submitter(row, proposal_id=42)

        assert submitter is not None
        assert submitter.proposal_id == 42
        assert submitter.raw_name == "山田太郎"
        assert submitter.submitter_type == SubmitterType.POLITICIAN
        assert submitter.is_representative is True

    def test_parse_submitter_committee(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(submitter="法務委員長", submitter_type="委員長")
        submitter = importer.parse_submitter(row, proposal_id=1)

        assert submitter is not None
        assert submitter.submitter_type == SubmitterType.COMMITTEE

    def test_parse_submitter_other_type(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(submitter="内閣総理大臣", submitter_type="内閣")
        submitter = importer.parse_submitter(row, proposal_id=1)

        assert submitter is not None
        assert submitter.submitter_type == SubmitterType.OTHER

    def test_parse_submitter_empty(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        row = _make_row(submitter="", initiator="")
        submitter = importer.parse_submitter(row, proposal_id=1)

        assert submitter is None

    def test_parse_submitter_fallback_to_initiator(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        """提出者が空の場合、発議者にフォールバックすることを確認."""
        row = _make_row(submitter="", initiator="鈴木一郎", submitter_type="議員")
        submitter = importer.parse_submitter(row, proposal_id=1)

        assert submitter is not None
        assert submitter.raw_name == "鈴木一郎"


class TestSmartNewsSmriSangiinGianImporterShortRow:
    """カラム不足の短い行のハンドリングテスト."""

    @pytest.fixture
    def importer(self) -> SmartNewsSmriSangiinGianImporter:
        return SmartNewsSmriSangiinGianImporter(governing_body_id=1, conference_id=10)

    def test_parse_record_short_row(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        """最低限のフィールド（タイトルまで）だけの行でもパースできることを確認."""
        short_row: list[Any] = ["153", "法律案（内閣提出）", "153", "1", "短い行の法案"]
        proposal = importer.parse_record(short_row)

        assert proposal.title == "短い行の法案"
        assert proposal.session_number == 153
        assert proposal.submitted_date is None
        assert proposal.voted_date is None
        assert proposal.external_id is None

    def test_parse_submitter_short_row(
        self, importer: SmartNewsSmriSangiinGianImporter
    ) -> None:
        """カラム不足の行では提出者がNoneになることを確認."""
        short_row: list[Any] = ["153", "法律案（内閣提出）", "153", "1", "法案"]
        submitter = importer.parse_submitter(short_row, proposal_id=1)

        assert submitter is None


class TestSmartNewsSmriSangiinGianImporterParseIsoDate:
    def test_valid_date(self) -> None:
        result = SmartNewsSmriSangiinGianImporter._parse_iso_date("2001-09-28")
        assert result == date(2001, 9, 28)

    def test_empty_string(self) -> None:
        result = SmartNewsSmriSangiinGianImporter._parse_iso_date("")
        assert result is None

    def test_whitespace_only(self) -> None:
        result = SmartNewsSmriSangiinGianImporter._parse_iso_date("  ")
        assert result is None

    def test_invalid_format(self) -> None:
        result = SmartNewsSmriSangiinGianImporter._parse_iso_date("2001/09/28")
        assert result is None

    def test_date_with_whitespace(self) -> None:
        result = SmartNewsSmriSangiinGianImporter._parse_iso_date(" 2001-09-28 ")
        assert result == date(2001, 9, 28)
