from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImportSmartNewsSmriInputDto:
    file_path: Path
    governing_body_id: int
    batch_size: int = 100


@dataclass
class ImportSmartNewsSmriOutputDto:
    total: int = 0
    created: int = 0
    skipped: int = 0
    errors: int = 0
