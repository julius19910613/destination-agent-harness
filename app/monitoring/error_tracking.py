"""Error tracking and recovery mechanisms."""
import logging
import asyncio
import time
from typing import Callable, Type, Optional, Tuple
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject all requests
    HALF_OPEN = "half-open"  # Testing if recovered


class RetryWithBackoff:
    """Retry mechanism with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry mechanism.
        
        Args:
            max_retries: Maximum number of retry attempts.
            base_delay: Base delay in seconds.
            max_delay: Maximum delay in seconds.
            exponential_base: Exponential base for backoff.
            exceptions: Exception types to retry on.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_count = 0
            
            while retry_count < self.max_retries:
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    retry_count += 1
                    
                    if retry_count >= self.max_retries:
                        logger.error(
                            f"All {self.max_retries} retries failed for {func.__name__}: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.base_delay * (self.exponential_base ** retry_count),
                        self.max_delay
                    )
                    
                    logger.warning(
                        f"Retry {retry_count}/{self.max_retries} for {func.__name__} "
                        f"after {delay:.2f}s: {e}"
                    )
                    
                    await asyncio.sleep(delay)
            
            # Should not reach here, but just in case
            return await func(*args, **kwargs)
        
        return wrapper


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Time in seconds before attempting recovery.
            expected_exception: Exception type to track.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker entering HALF_OPEN state for {func.__name__}")
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN for {func.__name__}. "
                        f"Retry after {self.recovery_timeout}s"
                    )
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset circuit if in half-open state
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker recovered to CLOSED state for {func.__name__}")
                
                return result
            
            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                logger.error(
                    f"Circuit breaker failure {self.failure_count}/{self.failure_threshold} "
                    f"for {func.__name__}: {e}"
                )
                
                # Open circuit if threshold reached
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.error(
                        f"Circuit breaker OPENED for {func.__name__}. "
                        f"Will retry after {self.recovery_timeout}s"
                    )
                
                raise
        
        return wrapper


class FallbackStrategy:
    """Fallback strategy for when operations fail."""
    
    @staticmethod
    def return_default(value: any):
        """Return a default value on failure."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        f"Fallback triggered for {func.__name__}: {e}. "
                        f"Returning default value."
                    )
                    return value
            return wrapper
        return decorator
    
    @staticmethod
    def return_none(func: Callable):
        """Return None on failure."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Fallback triggered for {func.__name__}: {e}. "
                    f"Returning None."
                )
                return None
        return wrapper


# Example usage
if __name__ == "__main__":
    # Retry with backoff
    @RetryWithBackoff(max_retries=3, base_delay=1.0)
    async def unstable_operation():
        import random
        if random.random() < 0.7:
            raise Exception("Random failure")
        return "Success"
    
    # Circuit breaker
    @CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    async def protected_operation():
        import random
        if random.random() < 0.5:
            raise Exception("Operation failed")
        return "Success"
    
    # Fallback
    @FallbackStrategy.return_default("default_value")
    async def operation_with_fallback():
        raise Exception("Always fails")
