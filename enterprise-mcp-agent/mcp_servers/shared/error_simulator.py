"""Error simulation for testing agent resilience."""

import random
from typing import Any


class TimeoutError(Exception):
    """Simulated timeout error."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' timed out after 30s")
        self.tool_name = tool_name


class RateLimitError(Exception):
    """Simulated rate limit error."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Rate limit exceeded for '{tool_name}'. Retry after 60 seconds."
        )
        self.tool_name = tool_name
        self.retry_after = 60


class NotFoundError(Exception):
    """Simulated resource not found error."""

    def __init__(self, tool_name: str, resource: str = "resource") -> None:
        super().__init__(f"'{tool_name}': {resource} not found")
        self.tool_name = tool_name


class PermissionDeniedError(Exception):
    """Simulated permission denied error."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"Permission denied for '{tool_name}'. Insufficient access rights."
        )
        self.tool_name = tool_name


class ServerError(Exception):
    """Simulated internal server error."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Internal server error in '{tool_name}'. Please try again.")
        self.tool_name = tool_name


ERROR_MAP = {
    "timeout": TimeoutError,
    "rate_limit": RateLimitError,
    "not_found": NotFoundError,
    "permission_denied": PermissionDeniedError,
    "server_error": ServerError,
}


class ErrorSimulator:
    """Simulates errors for testing agent error-handling capabilities."""

    def __init__(
        self,
        error_rate: float = 0.0,
        forced_errors: dict[str, str] | None = None,
    ) -> None:
        """
        Args:
            error_rate: Probability (0.0-1.0) that any call randomly fails.
            forced_errors: Map of tool_name -> error_type for deterministic failures.
                           Error types: timeout, rate_limit, not_found,
                           permission_denied, server_error.
        """
        self.error_rate = max(0.0, min(1.0, error_rate))
        self.forced_errors: dict[str, str] = forced_errors or {}

    def maybe_error(self, tool_name: str) -> None:
        """Possibly raise an error for the given tool call.

        Checks forced errors first, then random error rate.
        Raises nothing if no error is triggered.
        """
        # Check forced errors first (deterministic)
        if tool_name in self.forced_errors:
            error_type = self.forced_errors[tool_name]
            error_cls = ERROR_MAP.get(error_type)
            if error_cls:
                raise error_cls(tool_name)

        # Random error based on error_rate
        if self.error_rate > 0.0 and random.random() < self.error_rate:
            error_type = random.choice(list(ERROR_MAP.keys()))
            raise ERROR_MAP[error_type](tool_name)
