import time
import random
import functools

def retry(
    retry_on=Exception,
    max_retries=3,
    initial_delay=1.0,
    exponential=True,
    jitter=0.1,
      # Can be a single exception or tuple
):
    """
    Retry decorator with configurable behavior:
    - max_retries: Number of attempts before giving up
    - initial_delay: Delay in seconds before first retry
    - exponential: If True, doubles the delay after each attempt
    - jitter: Adds random jitter to delay (as a percentage of delay)
    - retry_on: Exception type(s) to trigger retry
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    if attempt == max_retries - 1:
                        raise
                    jitter_val = random.uniform(0, jitter * delay)
                    total_delay = delay + jitter_val
                    print(f"⚠️ Retry {attempt + 1}/{max_retries} due to {type(e).__name__}: {e}. Retrying in {total_delay:.2f}s...")
                    time.sleep(total_delay)
                    if exponential:
                        delay *= 2
        return wrapper
    return decorator