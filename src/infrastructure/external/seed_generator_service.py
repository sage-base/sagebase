"""シードファイル生成サービスの実装."""

from src.seed_generator import SeedGenerator


class SeedGeneratorServiceImpl:
    """シードファイル生成サービスの実装."""

    def generate_elections_seed(self) -> str:
        """選挙のSEEDコンテンツ（SQL文字列）を生成する."""
        generator = SeedGenerator()
        return generator.generate_elections_seed()

    def write_seed_file(self, content: str, output_path: str) -> str:
        """コンテンツをファイルに書き出し、書き出したパスを返す."""
        with open(output_path, "w") as f:
            f.write(content)
        return output_path
