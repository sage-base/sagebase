"""Base presenter for Streamlit interface layer.

This module provides the base presenter class that all Streamlit presenters
should inherit from. It handles dependency injection, error handling, and
common presenter functionality.
"""

import asyncio
import threading

from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any, Generic, TypeVar

from src.common.logging import get_logger
from src.infrastructure.di.container import Container


T = TypeVar("T")
R = TypeVar("R")

# 専用バックグラウンドスレッドのevent loop
# Streamlit/TornadoのメインEvent Loopに干渉しないよう、非同期処理は別スレッドで実行する
_dedicated_loop: asyncio.AbstractEventLoop | None = None
_dedicated_loop_lock = threading.Lock()


def _get_dedicated_loop() -> asyncio.AbstractEventLoop:
    """非同期処理用の専用event loopを取得する（なければ起動する）."""
    global _dedicated_loop
    with _dedicated_loop_lock:
        if _dedicated_loop is None or _dedicated_loop.is_closed():
            _dedicated_loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=_dedicated_loop.run_forever, daemon=True, name="presenter-async"
            )
            thread.start()
        return _dedicated_loop


class BasePresenter(ABC, Generic[T]):  # noqa: UP046
    """Base presenter class for Streamlit interface layer.

    This class provides common functionality for all presenters including:
    - Dependency injection via container
    - Logging
    - Error handling
    - State management abstraction
    """

    def __init__(self, container: Container | None = None):
        """Initialize the base presenter.

        Args:
            container: Dependency injection container. If None, creates a new instance.
        """
        self.container = container or Container.create_for_environment()
        self.logger = get_logger(self.__class__.__name__)

    def _run_async(self, coro: Coroutine[Any, Any, R]) -> R:
        """Run an async coroutine from sync context.

        専用バックグラウンドスレッドのevent loopでコルーチンを実行する。
        Streamlit/TornadoのメインEvent Loopには一切触れないため、
        WebSocketClosedErrorやevent loop衝突が発生しない。

        Args:
            coro: The async coroutine to run

        Returns:
            The result of the coroutine

        Raises:
            Exception: If the async operation fails
        """
        try:
            loop = _get_dedicated_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        except Exception as e:
            self.logger.error(f"Failed to run async operation: {e}")
            raise

    @abstractmethod
    def load_data(self) -> T:
        """Load data for the view.

        This method should be implemented by each presenter to load
        the necessary data for its view.

        Returns:
            The loaded data in the appropriate format for the view.
        """
        pass

    @abstractmethod
    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions from the view.

        This method should be implemented by each presenter to handle
        user interactions and business logic.

        Args:
            action: The action to perform (e.g., 'create', 'update', 'delete')
            **kwargs: Additional parameters for the action

        Returns:
            Result of the action
        """
        pass

    def handle_error(self, error: Exception, context: str = "") -> str:
        """Handle errors in a consistent way.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            User-friendly error message
        """
        error_msg = f"Error in {context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg, exc_info=True)
        return error_msg

    def validate_input(
        self, data: dict[str, Any], required_fields: list[str]
    ) -> tuple[bool, str]:
        """Validate input data.

        Args:
            data: The input data to validate
            required_fields: List of required field names

        Returns:
            Tuple of (is_valid, error_message)
        """
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return False, f"必須フィールドが不足しています: {', '.join(missing_fields)}"
        return True, ""


class CRUDPresenter(BasePresenter[T], ABC):
    """Base presenter for CRUD operations.

    Extends BasePresenter with standard CRUD operation methods.
    """

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle CRUD actions.

        Args:
            action: The CRUD action ('create', 'read', 'update', 'delete')
            **kwargs: Parameters for the action

        Returns:
            Result of the action
        """
        try:
            if action == "create":
                return self.create(**kwargs)
            elif action == "read":
                return self.read(**kwargs)
            elif action == "update":
                return self.update(**kwargs)
            elif action == "delete":
                return self.delete(**kwargs)
            elif action == "list":
                return self.list(**kwargs)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            raise Exception(self.handle_error(e, f"handling {action}")) from e

    @abstractmethod
    def create(self, **kwargs: Any) -> Any:
        """Create a new entity."""
        pass

    @abstractmethod
    def read(self, **kwargs: Any) -> Any:
        """Read an entity."""
        pass

    @abstractmethod
    def update(self, **kwargs: Any) -> Any:
        """Update an entity."""
        pass

    @abstractmethod
    def delete(self, **kwargs: Any) -> Any:
        """Delete an entity."""
        pass

    @abstractmethod
    def list(self, **kwargs: Any) -> list[Any]:
        """List entities."""
        pass
