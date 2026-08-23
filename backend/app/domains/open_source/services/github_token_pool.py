"""GitHub token pool - pure state machine for multi-token rotation.

Tracks per-token rate-limit state (remaining quota / reset windows),
selects the healthiest token before each request, blacklists tokens on
401, and rotates to the best alternative after 403/429.

Deliberately IO-free: no HTTP, no asyncio, no clocks. The transport layer
(``github_transport.GitHubTransport``) owns all request execution and feeds
response headers into :meth:`GitHubTokenPool.record_rate_limit`.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.core.config import settings


class GitHubTokenPool:
    """Rate-limit-aware pool over one or more GitHub tokens."""

    def __init__(self, token: str | None = None) -> None:
        self.tokens = self.parse_tokens(token)
        self.current_token_idx = 0
        # Per-token rate limit state for intelligent token selection
        self._token_remaining: dict[int, int] = {}
        self._token_reset_at: dict[int, int] = {}

    @staticmethod
    def parse_tokens(token: str | None) -> list[str]:
        if token:
            return [t.strip() for t in token.split(",") if t.strip()]
        tokens = settings.GITHUB_TOKENS
        if tokens:
            return [t.strip() for t in tokens.split(",") if t.strip()]
        return []

    def current_token(self) -> str | None:
        if not self.tokens:
            return None
        return self.tokens[self.current_token_idx % len(self.tokens)]

    def record_rate_limit(self, headers: Mapping[str, str]) -> None:
        """Update per-token rate limit state from response headers."""
        remaining = headers.get("X-RateLimit-Remaining")
        reset_at = headers.get("X-RateLimit-Reset")
        if remaining is not None:
            try:
                self._token_remaining[self.current_token_idx] = int(remaining)
            except ValueError:
                pass
        if reset_at is not None:
            try:
                self._token_reset_at[self.current_token_idx] = int(reset_at)
            except ValueError:
                pass

    def pick_best(self) -> None:
        """Switch to the token with the highest remaining quota before a request."""
        if len(self.tokens) <= 1:
            return
        best_idx = max(
            range(len(self.tokens)),
            key=lambda i: self._token_remaining.get(i, 5000),
        )
        if best_idx != self.current_token_idx:
            self.current_token_idx = best_idx

    def blacklist_current(self) -> None:
        """Mark the current token as having zero quota (401 bad credentials).

        Blacklisted tokens are recorded as 0 and thus never selected again by
        :meth:`pick_best` or :meth:`switch_to_best_alternative`.
        """
        self._token_remaining[self.current_token_idx] = 0

    def switch_to_best_alternative(self) -> bool:
        """After hitting 403/429, switch to the healthiest alternative token."""
        if len(self.tokens) <= 1:
            return False
        best_idx = max(
            (i for i in range(len(self.tokens)) if i != self.current_token_idx),
            key=lambda i: self._token_remaining.get(i, 5000),
            default=None,
        )
        if best_idx is None:
            return False
        # Only switch if the alternative has meaningful quota left
        # (unknown quota = assume full, consistent with pick_best;
        # tokens blacklisted on 401 are recorded as 0 and thus refused)
        if self._token_remaining.get(best_idx, 5000) <= 0:
            return False
        self.current_token_idx = best_idx
        return True
