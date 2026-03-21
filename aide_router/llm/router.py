"""
AIDE Intelligent LLM Router
Routes each scoring task to the best available provider.
Falls back automatically when rate limits are hit or a provider fails.
"""

import json
import logging
import os
import re
import time
from typing import Any, Optional

import requests

from .budget import BudgetTracker
from .config import PROVIDERS, TASK_ROUTING, TaskType

logger = logging.getLogger("aide.router")


class LLMRouter:
    """
    Central router for all LLM calls in AIDE.

    Usage:
        router = LLMRouter()
        result = router.call(
            task_type=TaskType.SCORE,
            messages=[{"role": "user", "content": "..."}],
            estimated_tokens=400,
        )
    """

    def __init__(self):
        self.budget = BudgetTracker()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def call(
        self,
        task_type: str,
        messages: list[dict],
        estimated_tokens: int = 400,
        max_retries_per_provider: int = 2,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        Route a task to the best available provider.
        Returns a dict with keys: content, provider, model, tokens_used.
        Raises RuntimeError if every provider in the chain fails.
        """
        chain = self._build_chain(task_type)
        full_messages = self._build_messages(messages, system_prompt)

        for provider_name in chain:
            cfg = PROVIDERS[provider_name]

            if not self.budget.has_budget(provider_name, estimated_tokens):
                logger.info(
                    "[router] %s skipped — daily budget exhausted "
                    "(%d tokens remaining)",
                    provider_name,
                    self.budget.remaining_tokens(provider_name),
                )
                continue

            for attempt in range(1, max_retries_per_provider + 1):
                try:
                    logger.info(
                        "[router] %s → %s (attempt %d)",
                        provider_name, cfg["model"], attempt,
                    )
                    response = self._call_provider(
                        provider_name, cfg, full_messages
                    )
                    return response

                except RateLimitError:
                    logger.warning(
                        "[router] %s rate-limited — moving to next provider",
                        provider_name,
                    )
                    break  # Don't retry; move to next provider immediately

                except ProviderError as e:
                    logger.warning(
                        "[router] %s error on attempt %d: %s",
                        provider_name, attempt, e,
                    )
                    if attempt < max_retries_per_provider:
                        time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s
                    # After all retries, fall through to next provider

        raise RuntimeError(
            f"All providers failed for task_type={task_type}. "
            f"Chain tried: {chain}. Check API keys and budget state."
        )

    def log_budget(self):
        """Print a budget summary — useful at the end of each pipeline run."""
        summary = self.budget.summary()
        logger.info("[budget] Daily usage summary:")
        for name, stats in summary.items():
            logger.info(
                "  %-14s %6d used / %6d remaining  (%.1f%%)",
                name, stats["used"], stats["remaining"], stats["pct_used"],
            )

    # ------------------------------------------------------------------
    # Internal — routing
    # ------------------------------------------------------------------

    def _build_chain(self, task_type: str) -> list[str]:
        """Return ordered provider names for this task type."""
        if task_type in TASK_ROUTING:
            return TASK_ROUTING[task_type]
        # Fallback: sort all providers by global priority
        return sorted(PROVIDERS, key=lambda p: PROVIDERS[p]["priority"])

    def _build_messages(
        self, messages: list[dict], system_prompt: Optional[str]
    ) -> list[dict]:
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + messages
        return messages

    # ------------------------------------------------------------------
    # Internal — HTTP call
    # ------------------------------------------------------------------

    def _call_provider(
        self, provider_name: str, cfg: dict, messages: list[dict]
    ) -> dict:
        api_key = os.environ.get(cfg["api_key_env"])
        if not api_key:
            raise ProviderError(
                f"Missing env var {cfg['api_key_env']} for {provider_name}"
            )

        payload: dict[str, Any] = {
            "model":       cfg["model"],
            "messages":    messages,
            "max_tokens":  1024,
            "temperature": 0.1,
        }

        if cfg.get("supports_json"):
            payload["response_format"] = {"type": "json_object"}

        # OpenRouter needs an extra header
        headers = {
            "Authorization":  f"Bearer {api_key}",
            "Content-Type":   "application/json",
        }
        if provider_name == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/Peepeepoopookk/AIDE"
            headers["X-Title"]      = "AIDE"

        resp = requests.post(
            f"{cfg['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        # Handle rate limiting
        if resp.status_code == 429:
            raise RateLimitError(f"{provider_name} returned 429")

        if not resp.ok:
            raise ProviderError(
                f"{provider_name} HTTP {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        content       = data["choices"][0]["message"]["content"]
        # Strip chain-of-thought blocks from reasoning models
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        tokens_used   = data.get("usage", {}).get("total_tokens", 300)  # fallback estimate

        self.budget.record_usage(provider_name, tokens_used)

        # For providers without native JSON mode, try to extract JSON anyway
        if not cfg.get("supports_json"):
            content = self._extract_json(content)

        return {
            "content":      content,
            "provider":     provider_name,
            "model":        cfg["model"],
            "tokens_used":  tokens_used,
        }

    def _extract_json(self, text: str) -> str:
        """Pull a JSON object out of free-form text (for OpenRouter fallback)."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return text


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------

class RateLimitError(Exception):
    """Provider returned 429 — router should move to next in chain."""

class ProviderError(Exception):
    """Non-rate-limit error from provider — router will retry then move on."""
