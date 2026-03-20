"""
AIDE Budget Tracker
Persists daily token usage per provider to a JSON file.
Resets automatically at midnight UTC each day.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import PROVIDERS, BUDGET_STATE_FILE, SAFETY_MARGIN_TOKENS


class BudgetTracker:
    """
    Reads and writes a JSON file that tracks how many tokens
    each provider has consumed today. Resets at UTC midnight.
    
    File format:
    {
        "date": "2025-03-20",
        "usage": {
            "cerebras":    150000,
            "groq_fast":   80000,
            "groq_strong": 12000,
            "mistral":     5000,
            "openrouter":  0
        }
    }
    """

    def __init__(self, state_file: str = BUDGET_STATE_FILE):
        self.state_file = Path(state_file)
        self._state = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_budget(self, provider_name: str, estimated_tokens: int = 500) -> bool:
        """Return True if provider has enough budget left for this call."""
        remaining = self.remaining_tokens(provider_name)
        return remaining >= (estimated_tokens + SAFETY_MARGIN_TOKENS)

    def remaining_tokens(self, provider_name: str) -> int:
        limit = PROVIDERS[provider_name]["daily_token_limit"]
        used  = self._state["usage"].get(provider_name, 0)
        return max(0, limit - used)

    def record_usage(self, provider_name: str, tokens_used: int):
        """Call this after every successful LLM response."""
        self._state["usage"][provider_name] = (
            self._state["usage"].get(provider_name, 0) + tokens_used
        )
        self._save()

    def summary(self) -> dict:
        """Return a human-readable budget summary for logging."""
        out = {}
        for name in PROVIDERS:
            limit     = PROVIDERS[name]["daily_token_limit"]
            used      = self._state["usage"].get(name, 0)
            remaining = max(0, limit - used)
            out[name] = {
                "used":      used,
                "remaining": remaining,
                "pct_used":  round(used / limit * 100, 1) if limit else 0,
            }
        return out

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load(self) -> dict:
        today = self._today()
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                if data.get("date") == today:
                    return data
            except (json.JSONDecodeError, KeyError):
                pass
        # New day or corrupt file — reset
        return {"date": today, "usage": {}}

    def _save(self):
        self.state_file.write_text(json.dumps(self._state, indent=2))
