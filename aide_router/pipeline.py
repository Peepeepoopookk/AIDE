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
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.config_validator import require_config; require_config(require_llm=True)

from .llm.scorer import SignalScorer
from .llm.router import LLMRouter

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.logger import get_logger
logger = get_logger('aide.pipeline')
from utils.task_manager import TaskManager, TaskStatus


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
            score = data.get("score") or {}
            classification = data.get("classification") or {}
            is_relevant = classification.get("is_relevant", False)

            payload = {
                "scored": True,
                "classification": classification,
                "score_data": score,
                "summary_data": data.get("summary") or {},
                "analysis_data": data.get("analysis") or {},
                "skip_reason": data.get("skip_reason", ""),
                "category": classification.get("category", ""),
            }

            if not is_relevant:
                payload["score_weighted"] = 0.0
                payload["score_total"] = 0.0
                payload["relevance"] = 0.0
                payload["score_novelty"] = 0.0
                payload["score_hype"] = 0.0
                payload["score_impact"] = 0.0
                payload["score_confidence"] = 0.0
            else:
                relevance = float(score.get("relevance_score") or 0)
                urgency = float(score.get("urgency_score") or 0)
                confidence = float(score.get("confidence") or 1)
                payload["relevance"] = relevance
                payload["score_novelty"] = float(score.get("novelty_score") or 0)
                payload["score_hype"] = urgency
                payload["score_impact"] = float(score.get("impact_score") or 0)
                payload["score_confidence"] = confidence
                payload["score_total"] = round((relevance + urgency) / 2, 4)
                payload["score_weighted"] = round(relevance * confidence, 4)

            response = self.client.table("signals").update(payload).eq("id", record_id).execute()
            if not response.data:
                logger.error("Update returned no data for id=%s — possible RLS block or missing row", record_id)
        except Exception as e:
            logger.error("Failed to write result for id=%s: %s", record_id, e)


def run(batch_size: int = 50, delay_between: float = 0.5):
    tm = TaskManager()
    task_id = tm.create_task("scoring_pipeline", metadata={"batch_size": batch_size})
    tm.update_task(task_id, status=TaskStatus.PROCESSING, message="Fetching unscored signals")
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
            pct = int((i / len(signals)) * 100)
            tm.update_task(task_id, progress=pct, message=f"Scored {i}/{len(signals)} signals")
            logger.info("Written id=%s  provider=%s",
                        sid, (result.get("score") or {}).get("_provider", "?"))
        except Exception as e:
            failed += 1
            logger.error("Failed on id=%s: %s", sid, e)
            tm.update_task(task_id, message=f"Error on signal {i}/{len(signals)}: {e}")

        time.sleep(delay_between)

    logger.info(
        "=== Pipeline done: %d succeeded, %d failed ===",
        success, failed,
    )
    tm.complete_task(task_id, result={"success": success, "failed": failed, "total": len(signals)})
    router.log_budget()


if __name__ == "__main__":
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(batch_size=batch)