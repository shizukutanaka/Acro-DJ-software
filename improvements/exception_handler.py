# Copyright (c) 2024 Acro DJ Mixer Contributors
# Licensed under the MIT License - see LICENSE file for details

"""
Standardized Exception Handling

Provides consistent error handling patterns across the application.
"""

import logging
import functools
import traceback
from typing import Callable, Any, Optional, Type
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class AcroDJException(Exception):
    """Base exception for Acro DJ Mixer."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[dict] = None
    ):
        """Initialize exception."""
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.details = details or {}

    def __str__(self) -> str:
        """Return formatted error message."""
        return f"[{self.severity.value}] {self.message}"


class AudioProcessingError(AcroDJException):
    """Audio processing error."""
    pass


class FileLoadError(AcroDJException):
    """File loading error."""
    pass


class ConfigurationError(AcroDJException):
    """Configuration error."""
    pass


class PluginError(AcroDJException):
    """Plugin system error."""
    pass


class ThreadingError(AcroDJException):
    """Threading-related error."""
    pass


class ExceptionHandler:
    """Centralized exception handler."""

    @staticmethod
    def log_exception(
        exc: Exception,
        context: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> None:
        """Log exception with context."""
        message = f"{context}: {str(exc)}" if context else str(exc)

        if severity == ErrorSeverity.CRITICAL:
            logger.critical(message, exc_info=True)
        elif severity == ErrorSeverity.ERROR:
            logger.error(message, exc_info=True)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(message)
        else:
            logger.info(message)

    @staticmethod
    def handle_error(
        exc: Exception,
        context: Optional[str] = None,
        recovery_fn: Optional[Callable] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        reraise: bool = False
    ) -> Any:
        """
        Handle error with optional recovery.

        Args:
            exc: Exception to handle
            context: Context description
            recovery_fn: Optional recovery function
            severity: Error severity
            reraise: Whether to re-raise exception

        Returns:
            Result of recovery function or None
        """
        ExceptionHandler.log_exception(exc, context, severity)

        result = None
        if recovery_fn:
            try:
                result = recovery_fn()
            except Exception as recovery_exc:
                logger.error(f"Recovery function failed: {recovery_exc}")
                if reraise:
                    raise recovery_exc

        if reraise:
            raise exc

        return result


def safe_execute(
    func: Callable,
    *args,
    context: Optional[str] = None,
    default_return: Any = None,
    log_errors: bool = True,
    **kwargs
) -> Any:
    """
    Execute function with exception handling.

    Args:
        func: Function to execute
        context: Context description
        default_return: Value to return on error
        log_errors: Whether to log errors
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        if log_errors:
            ExceptionHandler.log_exception(
                exc,
                context or f"Error in {func.__name__}",
                ErrorSeverity.ERROR
            )
        return default_return


def safe_execute_async(
    func: Callable,
    on_error: Optional[Callable] = None,
    context: Optional[str] = None
) -> Callable:
    """
    Decorator for safe async function execution.

    Args:
        func: Async function to wrap
        on_error: Error callback
        context: Context description

    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            error_context = context or f"Async error in {func.__name__}"
            ExceptionHandler.log_exception(exc, error_context)
            if on_error:
                await on_error(exc)
            return None

    return wrapper


class ErrorRecoveryContext:
    """Context manager for error recovery."""

    def __init__(
        self,
        context: str,
        recovery_fn: Optional[Callable] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        suppress: bool = False
    ):
        """Initialize recovery context."""
        self.context = context
        self.recovery_fn = recovery_fn
        self.severity = severity
        self.suppress = suppress

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Handle exception on exit."""
        if exc_type is not None:
            exc = exc_val or exc_type()
            ExceptionHandler.log_exception(exc, self.context, self.severity)

            if self.recovery_fn:
                try:
                    self.recovery_fn()
                except Exception as recovery_exc:
                    logger.error(f"Recovery failed: {recovery_exc}")

            return self.suppress

        return False


class AudioCallbackErrorHandler:
    """Special handler for audio callback errors."""

    @staticmethod
    def handle_callback_error(
        exc: Exception,
        deck_id: Optional[str] = None
    ) -> None:
        """
        Handle audio callback error.

        Critical errors must be logged but not raise exceptions.
        """
        context = f"Audio callback error (deck: {deck_id})" if deck_id else "Audio callback error"
        logger.error(context, exc_info=exc)

        # Alert user about audio processing issue
        # (In real app, would notify UI)

    @staticmethod
    def safe_get_chunk(
        deck,
        frames: int,
        deck_id: str
    ) -> Optional[Any]:
        """Safely get audio chunk from deck."""
        try:
            return deck.get_chunk(frames)
        except Exception as exc:
            AudioCallbackErrorHandler.handle_callback_error(exc, deck_id)
            return None


class FileOperationErrorHandler:
    """Handler for file operations."""

    @staticmethod
    def safe_load_file(
        filepath: str,
        load_fn: Callable
    ) -> Optional[Any]:
        """Safely load file."""
        try:
            return load_fn(filepath)
        except FileNotFoundError as exc:
            raise FileLoadError(
                f"File not found: {filepath}",
                severity=ErrorSeverity.ERROR
            ) from exc
        except Exception as exc:
            raise FileLoadError(
                f"Failed to load file: {filepath}",
                severity=ErrorSeverity.ERROR,
                details={"error": str(exc)}
            ) from exc

    @staticmethod
    def safe_save_file(
        filepath: str,
        data: Any,
        save_fn: Callable
    ) -> bool:
        """Safely save file."""
        try:
            save_fn(filepath, data)
            return True
        except Exception as exc:
            logger.error(f"Failed to save file {filepath}: {exc}")
            return False
