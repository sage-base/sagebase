from typing import Any


def make_smri_record_with_judges(
    sansei: str = "",
    hantai: str = "",
    proposal_type: str = "衆法",
    session_number: str = "200",
    proposal_number: str = "42",
    title: str = "テスト法案",
    result: str = "成立",
    url: str = "https://www.shugiin.go.jp/keika/TEST.htm",
) -> list[Any]:
    nested_row = [
        "200",
        result,
        "経過",
        url,
        "",
        "",
        proposal_type,
        *[""] * 7,
        sansei,
        hantai,
        *[""] * 7,
    ]
    return [
        proposal_type,
        session_number,
        proposal_number,
        title,
        "200",
        result,
        "",
        "",
        "",
        "",
        [nested_row],
    ]
