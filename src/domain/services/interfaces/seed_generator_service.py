"""シードファイル生成サービスのインターフェース."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SeedFileResult:
    """シードファイル生成結果."""

    content: str
    file_path: str


class ISeedGeneratorService(Protocol):
    """シードファイル生成サービスのインターフェース."""

    def generate_and_save_elections_seed(self) -> SeedFileResult:
        """選挙SEEDファイルを生成・保存し、結果を返す."""
        ...
