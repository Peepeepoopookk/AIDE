"""
AIDE Signal Scoring Pipeline
Entry point for GitHub Actions cron job.

Run:   python -m aide_router.pipeline
Env:   SUPABASE_URL, SUPABASE_KEY, CEREBRAS_API_KEY, GROQ_API_KEY,
       MISTRAL_API_KEY, OPENROUTER_API_KEY
"""

import json
import logging
import os
import sys
import time

from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()

from .llm.scorer import SignalScorer
from .llm.router import LLMRouter

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aide.pipeline")


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

class SupabaseClient:
    def __init__(self):
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        self.client = create_client(url, key)

    def fetch_unscored(self, limit: int = 50) -> list:
        try:
            response = (self.client.table("signals")
                .select("*")
                .eq("scored", False)
                .order("created", desc=False)
                .limit(limit)
                .execute())
            return response.data
        except Exception as e:
            logger.error("Failed to fetch unscored signals: %s", e)
            return []

    def write_result(self, record_id: str, data: dict):
        try:
            payload = {
                "scored": data.get("scored", True),
                "classification": data.get("classification") or {},
                "score_data": data.get("score") or {},
                "summary_data": data.get("summary") or {},
                "analysis_data": data.get("analysis") or {},
                "skip_reason": data.get("skip_reason", ""),
            }
            self.client.table("signals").update(payload).eq("id", record_id).execute()
        except Exception as e:
            logger.error("Failed to write result for id=%s: %s", record_id, e)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(batch_size: int = 50, delay_between: float = 0.5):
    """
    Main entry point.
    Fetches up to `batch_size` unscored signals, scores them, writes back.
    """
    logger.info("=== AIDE scoring pipeline starting ===")

    pb      = SupabaseClient()
    scorer  = SignalScorer()
    router  = scorer.router

    signals = pb.fetch_unscored(limit=batch_size)
    logger.info("Fetched %d unscored signals", len(signals))

    if not signals:
        logger.info("Nothing to score. Exiting cleanly.")
        router.log_budget()
        return

    success = 0
    failed  = 0

    for i, signal in enumerate(signals, 1):
        sid = signal["id"]
        logger.info("--- Signal %d/%d  id=%s ---", i, len(signals), sid)

        try:
            result = scorer.process_signal(signal)
            pb.write_result(sid, result)
            success += 1
            logger.info("Written id=%s  provider=%s",
                        sid, (result.get("score") or {}).get("_provider", "?"))
        except Exception as e:
            failed += 1
            logger.error("Failed on id=%s: %s", sid, e)
            # Don't crash the whole batch — continue to next signal

        time.sleep(delay_between)  # gentle pacing between calls

    logger.info(
        "=== Pipeline done: %d succeeded, %d failed ===",
        success, failed,
    )
    router.log_budget()


if __name__ == "__main__":
    # Allow overriding batch size from CLI: python -m aide_router.pipeline 100
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(batch_size=batch)
