import time
import random
import functools
from typing import Callable, Any, Tuple, Type
from utils.logger import get_logger

logger = get_logger('aide.retry')

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        logger.error("Function %s failed after %d retries: %s",
                                     func.__name__, max_retries, e)
                        raise
                    current_delay = min(delay, max_delay)
                    if jitter:
                        current_delay *= (0.5 + random.random())
                    logger.warning("Function %s attempt %d failed: %s. Retrying in %.1fs",
                                   func.__name__, attempt + 1, e, current_delay)
                    time.sleep(current_delay)
                    delay *= backoff_factor
            raise last_exc
        return wrapper
    return decorator
