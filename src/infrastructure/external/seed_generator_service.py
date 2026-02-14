"""シードファイル生成サービスの実装."""

from src.domain.services.interfaces.seed_generator_service import SeedFileResult
from src.seed_generator import SeedGenerator


DEFAULT_ELECTIONS_SEED_PATH = "database/seed_elections_generated.sql"
DEFAULT_ELECTION_MEMBERS_SEED_PATH = "database/seed_election_members_generated.sql"


class SeedGeneratorServiceImpl:
    """シードファイル生成サービスの実装."""

    def __init__(
        self,
        output_path: str = DEFAULT_ELECTIONS_SEED_PATH,
        election_members_output_path: str = DEFAULT_ELECTION_MEMBERS_SEED_PATH,
    ) -> None:
        self._output_path = output_path
        self._election_members_output_path = election_members_output_path

    def generate_and_save_elections_seed(self) -> SeedFileResult:
        """選挙SEEDファイルを生成・保存し、結果を返す."""
        generator = SeedGenerator()
        content = generator.generate_elections_seed()

        with open(self._output_path, "w") as f:
            f.write(content)

        return SeedFileResult(content=content, file_path=self._output_path)

    def generate_and_save_election_members_seed(self) -> SeedFileResult:
        """選挙結果メンバーSEEDファイルを生成・保存し、結果を返す."""
        generator = SeedGenerator()
        content = generator.generate_election_members_seed()

        with open(self._election_members_output_path, "w") as f:
            f.write(content)

        return SeedFileResult(
            content=content, file_path=self._election_members_output_path
        )
