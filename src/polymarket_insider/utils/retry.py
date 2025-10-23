"""Retry utilities with exponential backoff and circuit breaker patterns."""

import asyncio
import functools
import logging
import random
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Type, Union, Tuple

from ..exceptions import APIError, ConnectionError, WebSocketError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60,
                 expected_exception: Type[Exception] = Exception):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await self._async_call(func, *args, **kwargs)
            else:
                return self._sync_call(func, *args, **kwargs)
        return async_wrapper

    async def _async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker."""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _sync_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with circuit breaker."""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)
        )

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.state = 'CLOSED'

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


def retry_async(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (APIError, ConnectionError, WebSocketError)
) -> Callable:
    """Async retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay between retries
        jitter: Whether to add random jitter to prevent thundering herd
        exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise

                    delay = min(
                        initial_delay * (backoff_factor ** attempt),
                        max_delay
                    )

                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)

            raise last_exception
        return wrapper
    return decorator


def rate_limit_async(calls_per_second: float) -> Callable:
    """Rate limiting decorator for async functions.

    Args:
        calls_per_second: Maximum number of calls per second

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        min_interval = 1.0 / calls_per_second
        last_called = [0.0]  # Use list to allow modification in closure

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            now = asyncio.get_event_loop().time()
            time_since_last_call = now - last_called[0]

            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                logger.debug(f"Rate limiting {func.__name__}: sleeping {sleep_time:.3f}s")
                await asyncio.sleep(sleep_time)

            last_called[0] = asyncio.get_event_loop().time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Preconfigured circuit breakers for different types of operations
api_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout=30,
    expected_exception=(APIError, ConnectionError)
)

websocket_circuit_breaker = CircuitBreaker(
    failure_threshold=2,
    timeout=60,
    expected_exception=WebSocketError
)