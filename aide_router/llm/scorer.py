"""
AIDE Signal Scorer
Defines the prompts and scoring logic for each signal type.
The router picks the provider; this module owns the prompts.
"""

import json
import logging
import re
from typing import Optional

from .router import LLMRouter
from .config import TaskType

logger = logging.getLogger("aide.scorer")


# ---------------------------------------------------------------------------
# System prompt shared by all scoring tasks
# ---------------------------------------------------------------------------
BASE_SYSTEM = """You are a financial and market intelligence analyst.
You process signals (news headlines, social posts, forum threads, financial events).
Always respond with valid JSON only. No preamble, no markdown fences, no explanation.
Be precise and concise."""


class SignalScorer:
    """
    High-level interface for scoring AIDE signals.
    One method per task type — call whichever fits the signal.
    """

    def __init__(self):
        self.router = LLMRouter()

    # ------------------------------------------------------------------
    # Task 1: Classify — fast, simple, uses Groq 8B first
    # ------------------------------------------------------------------

    def classify(self, signal_text: str, signal_source: str = "") -> dict:
        """
        Classify a signal into categories and assign basic tags.
        Returns: { category, tags, language, is_relevant }
        """
        messages = [{
            "role": "user",
            "content": (
                f"Signal source: {signal_source}\n"
                f"Signal text: {signal_text}\n\n"
                "Classify this signal. Be strict about is_relevant — only mark true if the signal "
                "is genuinely about AI, machine learning, software engineering, or technology research.\n"
                "A signal about calculators, fashion, food, sports, or unrelated news is NOT relevant.\n"
                "Return JSON:\n"
                "{\n"
                '  "category": one of [research|tool|model|dataset|news|other],\n'
                '  "tags": [list of 2-5 short topic tags based on actual content],\n'
                '  "language": ISO 639-1 code,\n'
                '  "is_relevant": true/false\n'
                "}"
            )
        }]
        result = self.router.call(
            task_type=TaskType.CLASSIFY,
            messages=messages,
            estimated_tokens=300,
            system_prompt=BASE_SYSTEM,
        )
        return self._parse_json(result, fallback={
            "category": "other",
            "tags": [],
            "language": "en",
            "is_relevant": False,
            "_provider": result["provider"],
        })

    # ------------------------------------------------------------------
    # Task 2: Score — numeric relevance + urgency
    # ------------------------------------------------------------------

    def score(self, signal_text: str, asset: Optional[str] = None) -> dict:
        """
        Score a signal's relevance and urgency numerically.
        Returns: { relevance_score, urgency_score, sentiment, confidence }
        """
        asset_ctx = f"Focus asset: {asset}\n" if asset else ""
        messages = [{
            "role": "user",
            "content": (
                f"{asset_ctx}Signal: {signal_text}\n\n"
                "Score this signal carefully based on its actual content. "
                "Scores must reflect the real importance of this specific signal — do not return generic scores.\n"
                "Return JSON:\n"
                "{\n"
                '  "relevance_score": 0-10 (how relevant is this to AI/ML/tech — be precise),\n'
                '  "urgency_score": 0-10 (how time-sensitive is this news),\n'
                '  "sentiment": one of [bullish|bearish|neutral],\n'
                '  "confidence": 0.0-1.0 (your confidence in this scoring, vary this per signal)\n'
                "}"
            )
        }]
        result = self.router.call(
            task_type=TaskType.SCORE,
            messages=messages,
            estimated_tokens=400,
            system_prompt=BASE_SYSTEM,
        )
        return self._parse_json(result, fallback={
            "relevance_score": 0,
            "urgency_score": 0,
            "sentiment": "neutral",
            "confidence": 0,
            "_provider": result["provider"],
        })

    # ------------------------------------------------------------------
    # Task 3: Summarize — concise distillation
    # ------------------------------------------------------------------

    def summarize(self, signal_text: str) -> dict:
        """
        Produce a brief structured summary.
        Returns: { headline, summary, key_entities, potential_impact }
        """
        messages = [{
            "role": "user",
            "content": (
                f"Signal: {signal_text}\n\n"
                "Summarize this signal. Return JSON:\n"
                "{\n"
                '  "headline": one-sentence summary (max 15 words),\n'
                '  "summary": 2-3 sentence explanation,\n'
                '  "key_entities": [companies, people, countries mentioned],\n'
                '  "potential_impact": brief market impact hypothesis\n'
                "}"
            )
        }]
        result = self.router.call(
            task_type=TaskType.SUMMARIZE,
            messages=messages,
            estimated_tokens=500,
            system_prompt=BASE_SYSTEM,
        )
        return self._parse_json(result, fallback={
            "headline": "",
            "summary": "",
            "key_entities": [],
            "potential_impact": "",
            "_provider": result["provider"],
        })

    # ------------------------------------------------------------------
    # Task 4: Analyze — deep pass for high-value signals
    # ------------------------------------------------------------------

    def analyze(self, signal_text: str) -> dict:
        """
        Deep analysis — runs only on signals with relevance_score >= 7.
        Returns full structured breakdown.
        """
        messages = [{
            "role": "user",
            "content": (
                f"Signal: {signal_text}\n\n"
                "Perform deep analysis. Return JSON:\n"
                "{\n"
                '  "primary_theme": main topic,\n'
                '  "secondary_themes": [list],\n'
                '  "named_entities": { "companies": [], "people": [], "locations": [] },\n'
                '  "sentiment_breakdown": { "overall": bullish/bearish/neutral, "magnitude": 0-1 },\n'
                '  "risk_factors": [list of identified risks],\n'
                '  "opportunity_signals": [list of positive signals],\n'
                '  "recommended_action": monitor/investigate/alert/ignore\n'
                "}"
            )
        }]
        result = self.router.call(
            task_type=TaskType.ANALYZE,
            messages=messages,
            estimated_tokens=700,
            system_prompt=BASE_SYSTEM,
        )
        return self._parse_json(result, fallback={
            "primary_theme": "",
            "secondary_themes": [],
            "named_entities": {},
            "sentiment_breakdown": {},
            "risk_factors": [],
            "opportunity_signals": [],
            "recommended_action": "monitor",
            "_provider": result["provider"],
        })

    # ------------------------------------------------------------------
    # Convenience: full pipeline for a single signal
    # ------------------------------------------------------------------

    def _build_signal_text(self, signal: dict) -> str:
        """
        Build clean signal text from title + raw_content.
        Strips arXiv junk prefixes and ensures LLM always gets meaningful content.
        """
        import re
        title = signal.get("title", "").strip()
        raw = signal.get("raw_content", "") or signal.get("content", "") or ""

        # Strip arXiv announce prefix
        raw = re.sub(r'^arXiv:\S+\s+Announce Type:\s*\w+\s*Abstract:\s*', '', raw, flags=re.IGNORECASE).strip()

        # Strip leading/trailing whitespace and normalize spaces
        raw = re.sub(r'\s+', ' ', raw).strip()

        if title and raw:
            return f"Title: {title}\n\nContent: {raw}"
        elif title:
            return f"Title: {title}"
        else:
            return raw

    def process_signal(self, signal: dict) -> dict:
        """
        Run the full scoring pipeline for one signal dict from PocketBase.
        Automatically selects which tasks to run based on content and scores.

        Returns enriched signal dict ready to write back.
        """
        text   = self._build_signal_text(signal)
        source = signal.get("source", "")
        asset  = signal.get("asset", None)

        # Step 1: always classify
        classification = self.classify(text, source)
        logger.info(
            "[scorer] classified → %s (relevant=%s) via %s",
            classification.get("category"),
            classification.get("is_relevant"),
            classification.get("_provider", "?"),
        )

        # Step 2: skip irrelevant signals early — save budget
        if not classification.get("is_relevant", True):
            return {
                **signal,
                "scored": True,
                "classification": classification,
                "score": None,
                "summary": None,
                "analysis": None,
                "skip_reason": "not_relevant",
            }

        # Step 3: score
        scoring = self.score(text, asset)
        logger.info(
            "[scorer] scored → relevance=%s urgency=%s via %s",
            scoring.get("relevance_score"),
            scoring.get("urgency_score"),
            scoring.get("_provider", "?"),
        )

        # Step 4: summarize
        summary = self.summarize(text)

        # Step 5: deep analysis only for high-relevance signals
        analysis = None
        if scoring.get("relevance_score", 0) >= 7:
            logger.info("[scorer] high relevance — running deep analysis")
            analysis = self.analyze(text)

        return {
            **signal,
            "scored":         True,
            "classification": classification,
            "score":          scoring,
            "summary":        summary,
            "analysis":       analysis,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _parse_json(self, llm_result: dict, fallback: dict) -> dict:
        """Parse JSON from LLM response, returning fallback on failure."""
        try:
            raw = llm_result["content"]
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw.strip(), flags=re.IGNORECASE)
            raw = re.sub(r'\n?```\s*$', '', raw).strip()
            parsed = json.loads(raw)
            parsed["_provider"]    = llm_result["provider"]
            parsed["_model"]       = llm_result["model"]
            parsed["_tokens_used"] = llm_result["tokens_used"]
            return parsed
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("[scorer] JSON parse failed: %s", e)
            fallback["_parse_error"] = str(e)
            return fallback
