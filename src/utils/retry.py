from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.utils.logger import logger


def log_retry(retry_state: object) -> None:
    logger.warning(
        "retry.attempt",
        attempt=getattr(retry_state, "attempt_number", 0),
        exception=str(getattr(retry_state, "outcome", None)),
    )


api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=log_retry,
    reraise=True,
)

ingestion_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    before_sleep=log_retry,
    reraise=True,
)
