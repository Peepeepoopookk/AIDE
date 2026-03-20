"""
AIDE Signal Scoring Pipeline
Entry point for GitHub Actions cron job.

Run:   python -m aide_router.pipeline
Env:   POCKETBASE_URL, CEREBRAS_API_KEY, GROQ_API_KEY,
       MISTRAL_API_KEY, OPENROUTER_API_KEY
"""

import json
import logging
import os
import sys
import time

import requests

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
# PocketBase helpers
# ---------------------------------------------------------------------------

class PocketBaseClient:
    def __init__(self):
        self.base = os.environ["POCKETBASE_URL"].rstrip("/")
        self.token = self._authenticate()

    def _authenticate(self) -> str:
        email    = os.environ["PB_ADMIN_EMAIL"]
        password = os.environ["PB_ADMIN_PASSWORD"]
        resp = requests.post(
            f"{self.base}/api/admins/auth-with-password",
            json={"identity": email, "password": password},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def _headers(self) -> dict:
        return {"Authorization": self.token}

    def fetch_unscored(self, collection: str = "signals", limit: int = 50) -> list:
        """Fetch signals where scored = false, oldest first."""
        resp = requests.get(
            f"{self.base}/api/collections/{collection}/records",
            headers=self._headers(),
            params={
                "filter": 'scored=false',
                "sort":   "created",
                "perPage": limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    def write_result(self, record_id: str, data: dict, collection: str = "signals"):
        """Patch a signal record with its scoring results."""
        payload = {
            "scored":         data.get("scored", True),
            "classification": json.dumps(data.get("classification")),
            "score_data":     json.dumps(data.get("score")),
            "summary_data":   json.dumps(data.get("summary")),
            "analysis_data":  json.dumps(data.get("analysis")),
            "skip_reason":    data.get("skip_reason", ""),
        }
        resp = requests.patch(
            f"{self.base}/api/collections/{collection}/records/{record_id}",
            headers=self._headers(),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(batch_size: int = 50, delay_between: float = 0.5):
    """
    Main entry point.
    Fetches up to `batch_size` unscored signals, scores them, writes back.
    """
    logger.info("=== AIDE scoring pipeline starting ===")

    pb      = PocketBaseClient()
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
                        sid, result.get("score", {}).get("_provider", "?"))
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
