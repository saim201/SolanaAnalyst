"""
Common decorators for the application.
"""
import time
from functools import wraps
from typing import Callable


def timer(func: Callable) -> Callable:
    """
    Decorator to measure and log function execution time.
    
    Usage:
        @timer
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        print(f"⏱️  {func.__name__} took {duration:.4f} seconds")
        return result
    return wrapper


def log_errors(func: Callable) -> Callable:
    """
    Decorator to log function errors.
    
    Usage:
        @log_errors
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error in {func.__name__}: {str(e)}")
            raise
    return wrapper


def retry(max_attempts: int = 3, delay_seconds: float = 1.0):
    """
    Decorator to retry function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries in seconds
    
    Usage:
        @retry(max_attempts=5, delay_seconds=2.0)
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay_seconds

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    print(
                        f"⚠️  {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s... Error: {str(e)}"
                    )
                    time.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff

        return wrapper
    return decorator
