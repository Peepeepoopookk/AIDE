"""
AIDE LLM Provider Configuration
All rate limits, task routing rules, and model assignments live here.
Edit this file when you add a new provider or adjust quotas.
"""

import os

# ---------------------------------------------------------------------------
# Task types — every signal scoring job maps to exactly one of these
# ---------------------------------------------------------------------------
class TaskType:
    CLASSIFY   = "classify"    # Simple: category / tag assignment
    SCORE      = "score"       # Medium: numeric relevance 0-10
    SUMMARIZE  = "summarize"   # Medium: short text summary
    ANALYZE    = "analyze"     # Complex: deep sentiment + entities + themes
    CRITICAL   = "critical"    # Complex: high-stakes financial or breaking news


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------
PROVIDERS = {

    "cerebras": {
        "base_url":    "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "model":       "llama3.1-8b",
        "daily_token_limit": 1_000_000,
        "rpm_limit":   30,
        "supports_json": True,
        "priority":    1,                          # 1 = try first
        "best_for":    [TaskType.SCORE, TaskType.SUMMARIZE, TaskType.ANALYZE, TaskType.CLASSIFY],
        "notes":       "Primary — 1M tok/day, continuous replenishment",
    },

    "groq_fast": {
        "base_url":    "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model":       "llama-3.1-8b-instant",
        "daily_token_limit": 500_000,
        "rpm_limit":   30,
        "supports_json": True,
        "priority":    2,
        "best_for":    [TaskType.CLASSIFY],        # 8B is perfect for simple tasks
        "notes":       "Fast lane — classification only, very high throughput",
    },

    "groq_strong": {
        "base_url":    "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model":       "llama-3.3-70b-versatile",
        "daily_token_limit": 200_000,              # shared key — reserve budget
        "rpm_limit":   30,
        "supports_json": True,
        "priority":    3,
        "best_for":    [TaskType.CRITICAL, TaskType.ANALYZE],
        "notes":       "Reserve for high-stakes analysis when Cerebras is exhausted",
    },

    "mistral": {
        "base_url":    "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "model":       "mistral-small-latest",
        "daily_token_limit": 33_000_000,           # 1B/month ÷ 30
        "rpm_limit":   5,                          # conservative — real limit unclear
        "supports_json": True,
        "priority":    4,
        "best_for":    [TaskType.CLASSIFY, TaskType.SCORE],
        "notes":       "Tertiary — huge monthly budget but low RPM",
    },

    "openrouter": {
        "base_url":    "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model":       "meta-llama/llama-3.1-8b-instruct:free",
        "daily_token_limit": 50_000,               # conservative estimate
        "rpm_limit":   10,
        "supports_json": False,                    # parse manually
        "priority":    5,
        "best_for":    [TaskType.CLASSIFY],
        "notes":       "Emergency fallback only — unpredictable throughput",
    },
}


# ---------------------------------------------------------------------------
# Task → provider priority override
# Override the global priority for specific task types.
# If a task type is not listed here, global priority order is used.
# ---------------------------------------------------------------------------
TASK_ROUTING = {
    TaskType.CLASSIFY:  ["groq_fast", "cerebras", "mistral", "openrouter"],
    TaskType.SCORE:     ["groq_strong", "cerebras", "mistral"],
    TaskType.SUMMARIZE: ["groq_strong", "cerebras", "mistral"],
    TaskType.ANALYZE:   ["cerebras", "groq_strong"],
    TaskType.CRITICAL:  ["groq_strong", "cerebras"],
}


# ---------------------------------------------------------------------------
# Budget safety thresholds
# Provider is skipped if remaining_tokens < SAFETY_MARGIN_TOKENS
# ---------------------------------------------------------------------------
SAFETY_MARGIN_TOKENS = 5_000   # keep a buffer before hitting the wall

# Path where per-provider daily usage is persisted (relative to project root)
BUDGET_STATE_FILE = "llm_budget_state.json"
