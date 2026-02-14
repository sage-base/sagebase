"""総務省比例代表PDF抽出のテスト."""

import json

from src.infrastructure.importers.soumu_proportional_pdf_extractor import (
    _parse_gemini_response,
)


class TestParseGeminiResponse:
    """Gemini API応答のパースをテストする."""

    def _make_response_json(self) -> str:
        """テスト用JSONレスポンスを生成する."""
        data = {
            "election_date": "2024-10-27",
            "blocks": [
                {
                    "block_name": "北海道",
                    "parties": [
                        {
                            "party_name": "自由民主党",
                            "votes": 641127,
                            "winners_count": 3,
                            "candidates": [
                                {
                                    "name": "渡辺 孝一",
                                    "list_order": 1,
                                    "smd_result": "落",
                                    "loss_ratio": 92.714,
                                },
                                {
                                    "name": "佐藤 花子",
                                    "list_order": 2,
                                    "smd_result": "",
                                    "loss_ratio": None,
                                },
                                {
                                    "name": "鈴木 次郎",
                                    "list_order": 3,
                                    "smd_result": "当",
                                    "loss_ratio": None,
                                },
                            ],
                        },
                        {
                            "party_name": "立憲民主党",
                            "votes": 400000,
                            "winners_count": 1,
                            "candidates": [
                                {
                                    "name": "高橋 三郎",
                                    "list_order": 1,
                                    "smd_result": "落",
                                    "loss_ratio": 85.5,
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        return json.dumps(data, ensure_ascii=False)

    def test_parse_valid_json(self) -> None:
        """正しいJSONをパースできる."""
        response = self._make_response_json()
        info, candidates = _parse_gemini_response(response, 50)

        assert info is not None
        assert info.election_number == 50
        assert info.election_date.year == 2024
        assert info.election_date.month == 10
        assert info.election_date.day == 27

        assert len(candidates) == 4

        # 渡辺: 小選挙区落選、比例復活候補（当選枠内）
        assert candidates[0].name == "渡辺 孝一"
        assert candidates[0].party_name == "自由民主党"
        assert candidates[0].block_name == "北海道"
        assert candidates[0].list_order == 1
        assert candidates[0].smd_result == "落"
        assert candidates[0].loss_ratio == 92.714
        assert candidates[0].is_elected is True

        # 佐藤: 比例単独（当選枠内）
        assert candidates[1].name == "佐藤 花子"
        assert candidates[1].smd_result == ""
        assert candidates[1].is_elected is True

        # 鈴木: 小選挙区当選（当選枠内だが、smd_result="当"）
        assert candidates[2].name == "鈴木 次郎"
        assert candidates[2].smd_result == "当"
        assert candidates[2].is_elected is True

        # 高橋: 立憲民主党、当選
        assert candidates[3].name == "高橋 三郎"
        assert candidates[3].party_name == "立憲民主党"
        assert candidates[3].is_elected is True

    def test_parse_markdown_wrapped_json(self) -> None:
        """マークダウンコードブロックでラップされたJSONをパースできる."""
        raw_json = self._make_response_json()
        response = f"```json\n{raw_json}\n```"
        info, candidates = _parse_gemini_response(response, 50)

        assert info is not None
        assert len(candidates) == 4

    def test_parse_invalid_json(self) -> None:
        """不正なJSONでエラーにならない."""
        info, candidates = _parse_gemini_response("this is not json", 50)

        assert info is None
        assert len(candidates) == 0

    def test_parse_empty_blocks(self) -> None:
        """空のブロックリストの場合."""
        data = {"election_date": "2024-10-27", "blocks": []}
        response = json.dumps(data)
        info, candidates = _parse_gemini_response(response, 50)

        assert info is not None
        assert len(candidates) == 0

    def test_parse_unknown_block_name_skipped(self) -> None:
        """未知のブロック名がスキップされる."""
        data = {
            "election_date": "2024-10-27",
            "blocks": [
                {
                    "block_name": "未知ブロック",
                    "parties": [
                        {
                            "party_name": "テスト党",
                            "votes": 100,
                            "winners_count": 1,
                            "candidates": [
                                {
                                    "name": "テスト 太郎",
                                    "list_order": 1,
                                    "smd_result": "",
                                    "loss_ratio": None,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        response = json.dumps(data, ensure_ascii=False)
        info, candidates = _parse_gemini_response(response, 50)

        assert len(candidates) == 0

    def test_elected_determination_by_winners_count(self) -> None:
        """当選判定がwinners_countに基づいて正しく行われる."""
        data = {
            "election_date": "2024-10-27",
            "blocks": [
                {
                    "block_name": "東京",
                    "parties": [
                        {
                            "party_name": "自由民主党",
                            "votes": 1000000,
                            "winners_count": 2,
                            "candidates": [
                                {
                                    "name": "候補者A",
                                    "list_order": 1,
                                    "smd_result": "",
                                },
                                {
                                    "name": "候補者B",
                                    "list_order": 2,
                                    "smd_result": "",
                                },
                                {
                                    "name": "候補者C",
                                    "list_order": 3,
                                    "smd_result": "",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        response = json.dumps(data, ensure_ascii=False)
        _, candidates = _parse_gemini_response(response, 50)

        assert len(candidates) == 3
        assert candidates[0].is_elected is True  # 1位 <= 2
        assert candidates[1].is_elected is True  # 2位 <= 2
        assert candidates[2].is_elected is False  # 3位 > 2
