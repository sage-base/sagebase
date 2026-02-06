"""シードファイル生成サービスのインターフェース."""

from typing import Protocol


class ISeedGeneratorService(Protocol):
    """シードファイル生成サービスのインターフェース."""

    def generate_elections_seed(self) -> str:
        """選挙のSEEDコンテンツ（SQL文字列）を生成する."""
        ...

    def write_seed_file(self, content: str, output_path: str) -> str:
        """コンテンツをファイルに書き出し、書き出したパスを返す."""
        ...
