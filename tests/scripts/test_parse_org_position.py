"""parse_org_position()のテスト."""

import pytest

from scripts.import_government_officials import parse_org_position


class TestParseOrgPosition:
    """notes列を organization + position にパースするテスト."""

    @pytest.mark.parametrize(
        ("notes", "expected_org", "expected_pos"),
        [
            ("法務省刑事局長", "法務省", "刑事局長"),
            ("内閣府大臣政務官", "内閣府", "大臣政務官"),
            ("厚生労働省健康局長", "厚生労働省", "健康局長"),
            ("防衛庁長官", "防衛庁", "長官"),
            ("衆議院法制局長", "衆議院", "法制局長"),
            ("消費者委員会委員長", "消費者委員会", "委員長"),
            ("内閣官房内閣審議官", "内閣官房", "内閣審議官"),
            # 省庁名のみ（positionなし）
            ("法務省", "法務省", ""),
            ("内閣府", "内閣府", ""),
            # 空文字列
            ("", "", ""),
            ("  ", "", ""),
            # パターンに該当しない文字列
            ("参考人", "", "参考人"),
            ("弁護士", "", "弁護士"),
        ],
    )
    def test_parse_org_position(
        self, notes: str, expected_org: str, expected_pos: str
    ) -> None:
        org, pos = parse_org_position(notes)
        assert org == expected_org
        assert pos == expected_pos
