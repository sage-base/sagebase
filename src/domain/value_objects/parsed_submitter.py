"""提出者文字列のパース結果を表す値オブジェクト."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedSubmitter:
    """提出者文字列のパース結果.

    提出者文字列を解析した結果として、個人名リストと総人数を保持する。
    """

    names: tuple[str, ...]
    total_count: int

    def __post_init__(self) -> None:
        if self.total_count < len(self.names):
            msg = (
                f"total_count({self.total_count})はnames数({len(self.names)})以上"
                "でなければなりません"
            )
            raise ValueError(msg)
