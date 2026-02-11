"""Tests for BAML Parliamentary Group Judge Extraction Service

会派賛否抽出サービスのテスト。
BAMLクライアントをモックして、外部サービス呼び出しなしでテストを実行します。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from baml_client.types import JudgmentType

from src.infrastructure.external.parliamentary_group_judge_extraction import (
    BAMLParliamentaryGroupJudgeExtractionService,
)


pytestmark = pytest.mark.baml

BAML_SERVICE_MODULE = (
    "src.infrastructure.external.parliamentary_group_judge_extraction"
    ".baml_parliamentary_group_judge_extraction_service.b"
)


@pytest.fixture
def mock_baml_client():
    """BAMLクライアントをモック"""
    with patch(BAML_SERVICE_MODULE) as mock_b:
        mock_extract = AsyncMock()
        mock_b.ExtractParliamentaryGroupJudges = mock_extract
        yield mock_b


class TestBAMLParliamentaryGroupJudgeExtractionService:
    """BAML Parliamentary Group Judge Extraction Service tests"""

    @pytest.mark.asyncio
    async def test_extract_judges_success(self, mock_baml_client):
        """正常な会派賛否抽出テスト（複数会派の賛成・反対）"""
        # BAMLの戻り値をモック
        mock_judge1 = MagicMock()
        mock_judge1.group_name = "自由民主党京都市会議員団"
        mock_judge1.judgment = JudgmentType.FOR
        mock_judge1.member_count = 20
        mock_judge1.note = None

        mock_judge2 = MagicMock()
        mock_judge2.group_name = "日本共産党京都市会議員団"
        mock_judge2.judgment = JudgmentType.AGAINST
        mock_judge2.member_count = 14
        mock_judge2.note = None

        mock_baml_client.ExtractParliamentaryGroupJudges.return_value = [
            mock_judge1,
            mock_judge2,
        ]

        # サービスを実行
        service = BAMLParliamentaryGroupJudgeExtractionService()
        html_text = """
        <table>
        <tr><td>自由民主党京都市会議員団</td><td>賛成</td><td>20人</td></tr>
        <tr><td>日本共産党京都市会議員団</td><td>反対</td><td>14人</td></tr>
        </table>
        """
        results = await service.extract_parliamentary_group_judges(
            html_text=html_text,
            proposal_id=1,
            source_url="https://example.com/gian.html",
        )

        # 検証
        assert len(results) == 2

        assert (
            results[0].extracted_parliamentary_group_name == "自由民主党京都市会議員団"
        )
        assert results[0].extracted_judgment == "賛成"
        assert results[0].proposal_id == 1
        assert results[0].source_url == "https://example.com/gian.html"
        assert results[0].additional_data == "member_count=20"

        assert (
            results[1].extracted_parliamentary_group_name == "日本共産党京都市会議員団"
        )
        assert results[1].extracted_judgment == "反対"
        assert results[1].additional_data == "member_count=14"

        # BAML呼び出しの検証
        mock_baml_client.ExtractParliamentaryGroupJudges.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_judges_none_input(self, mock_baml_client):
        """Noneが渡された場合のテスト"""
        service = BAMLParliamentaryGroupJudgeExtractionService()

        results = await service.extract_parliamentary_group_judges(html_text=None)

        assert results == []
        mock_baml_client.ExtractParliamentaryGroupJudges.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_judges_empty_text(self, mock_baml_client):
        """空のHTMLテキストの場合のテスト"""
        service = BAMLParliamentaryGroupJudgeExtractionService()

        results = await service.extract_parliamentary_group_judges(html_text="")

        assert results == []
        mock_baml_client.ExtractParliamentaryGroupJudges.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_judges_whitespace_only(self, mock_baml_client):
        """空白のみのテキストの場合のテスト"""
        service = BAMLParliamentaryGroupJudgeExtractionService()

        results = await service.extract_parliamentary_group_judges(
            html_text="   \n\t   "
        )

        assert results == []
        mock_baml_client.ExtractParliamentaryGroupJudges.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_judges_error_handling(self, mock_baml_client):
        """BAML APIエラー時のハンドリングテスト"""
        mock_baml_client.ExtractParliamentaryGroupJudges.side_effect = Exception(
            "BAML API Error"
        )

        service = BAMLParliamentaryGroupJudgeExtractionService()
        results = await service.extract_parliamentary_group_judges(
            html_text="<html>テスト用HTML</html>"
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_extract_judges_multiple_judgment_types(self, mock_baml_client):
        """棄権・欠席を含む複数の賛否タイプのテスト"""
        mock_for = MagicMock()
        mock_for.group_name = "A会派"
        mock_for.judgment = JudgmentType.FOR
        mock_for.member_count = 10
        mock_for.note = None

        mock_against = MagicMock()
        mock_against.group_name = "B会派"
        mock_against.judgment = JudgmentType.AGAINST
        mock_against.member_count = 5
        mock_against.note = None

        mock_abstain = MagicMock()
        mock_abstain.group_name = "C会派"
        mock_abstain.judgment = JudgmentType.ABSTAIN
        mock_abstain.member_count = 2
        mock_abstain.note = "一部議員は退席"

        mock_absent = MagicMock()
        mock_absent.group_name = "D会派"
        mock_absent.judgment = JudgmentType.ABSENT
        mock_absent.member_count = 1
        mock_absent.note = None

        mock_baml_client.ExtractParliamentaryGroupJudges.return_value = [
            mock_for,
            mock_against,
            mock_abstain,
            mock_absent,
        ]

        service = BAMLParliamentaryGroupJudgeExtractionService()
        results = await service.extract_parliamentary_group_judges(
            html_text="<html>テスト</html>"
        )

        assert len(results) == 4
        assert results[0].extracted_judgment == "賛成"
        assert results[1].extracted_judgment == "反対"
        assert results[2].extracted_judgment == "棄権"
        assert results[3].extracted_judgment == "欠席"

    @pytest.mark.asyncio
    async def test_extract_judges_no_member_count(self, mock_baml_client):
        """人数情報がない場合のテスト"""
        mock_judge = MagicMock()
        mock_judge.group_name = "公明党"
        mock_judge.judgment = JudgmentType.FOR
        mock_judge.member_count = None
        mock_judge.note = None

        mock_baml_client.ExtractParliamentaryGroupJudges.return_value = [mock_judge]

        service = BAMLParliamentaryGroupJudgeExtractionService()
        results = await service.extract_parliamentary_group_judges(
            html_text="<html>テスト</html>"
        )

        assert len(results) == 1
        assert results[0].extracted_parliamentary_group_name == "公明党"
        assert results[0].additional_data is None

    @pytest.mark.asyncio
    async def test_extract_judges_empty_results(self, mock_baml_client):
        """BAMLが空リストを返した場合のテスト"""
        mock_baml_client.ExtractParliamentaryGroupJudges.return_value = []

        service = BAMLParliamentaryGroupJudgeExtractionService()
        results = await service.extract_parliamentary_group_judges(
            html_text="<html>賛否情報なし</html>"
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_extract_judges_truncates_long_text(self, mock_baml_client):
        """長いテキストが切り詰められることをテスト"""
        mock_baml_client.ExtractParliamentaryGroupJudges.return_value = []

        service = BAMLParliamentaryGroupJudgeExtractionService()

        # 100000文字を超えるテキストを作成
        long_text = "a" * 110000

        await service.extract_parliamentary_group_judges(html_text=long_text)

        # BAML呼び出しの引数を検証
        call_args = mock_baml_client.ExtractParliamentaryGroupJudges.call_args
        passed_text = call_args[0][0]  # positional argument

        # 切り詰められたテキストは100000 + 3("...")文字
        assert len(passed_text) == 100003
        assert passed_text.endswith("...")
