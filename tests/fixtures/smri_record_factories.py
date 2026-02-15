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
    submitted_date: str = "",
    voted_date: str = "",
) -> list[Any]:
    nested_row = [
        "200",  # 0
        result,  # 1
        "経過",  # 2
        url,  # 3
        "",  # 4
        "",  # 5
        proposal_type,  # 6
        "",  # 7
        "",  # 8
        submitted_date,  # 9 (_IDX_NESTED_SUBMITTED_DATE)
        "",  # 10
        "",  # 11
        voted_date,  # 12 (_IDX_NESTED_VOTED_DATE)
        "",  # 13
        sansei,  # 14 (_IDX_NESTED_SANSEI_KAIHA)
        hantai,  # 15 (_IDX_NESTED_HANTAI_KAIHA)
        *[""] * 7,  # 16-22
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
