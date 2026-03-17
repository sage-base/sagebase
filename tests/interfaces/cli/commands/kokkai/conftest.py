"""kokkai CLIコマンドテスト共通フィクスチャ."""

from unittest.mock import MagicMock, patch

import pytest


_DI_PATH = "src.interfaces.cli.base"


@pytest.fixture
def mock_container() -> MagicMock:  # type: ignore[misc]
    """get_containerをモックし、MagicMockコンテナを返すフィクスチャ.

    ensure_container()は内部でget_container()を呼ぶため、
    get_containerをパッチすることで全CLIコマンドのDI解決をモックできる。
    """
    with patch(f"{_DI_PATH}.get_container") as mock_get:
        container = MagicMock()
        mock_get.return_value = container
        yield container
