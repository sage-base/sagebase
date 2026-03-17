"""ensure_container ヘルパーのテスト."""

from unittest.mock import MagicMock, patch

from src.interfaces.cli.base import ensure_container


class TestEnsureContainer:
    """ensure_container() のテスト."""

    @patch("src.interfaces.cli.base.get_container")
    def test_returns_existing_container_when_already_initialized(  # noqa: N802
        self, mock_get: MagicMock
    ) -> None:
        mock_container = MagicMock()
        mock_get.return_value = mock_container

        result = ensure_container()

        assert result is mock_container
        mock_get.assert_called_once()

    @patch("src.interfaces.cli.base.init_container")
    @patch("src.interfaces.cli.base.get_container")
    def test_initializes_container_when_not_yet_initialized(  # noqa: N802
        self, mock_get: MagicMock, mock_init: MagicMock
    ) -> None:
        mock_get.side_effect = RuntimeError("Container not initialized")
        mock_container = MagicMock()
        mock_init.return_value = mock_container

        result = ensure_container()

        assert result is mock_container
        mock_get.assert_called_once()
        mock_init.assert_called_once()
