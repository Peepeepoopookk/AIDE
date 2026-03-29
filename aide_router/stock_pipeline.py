import json
import logging
import os
import sys
import time
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.config_validator import require_config; require_config(require_llm=True)

import aide_router.llm.scorer

# 4. Scorer system prompt specifically for Stock Market Scoring
aide_router.llm.scorer.BASE_SYSTEM = (
    "You are an expert Indian stock market analyst. Score signals based on their "
    "relevance and impact to NSE/BSE listed stocks and Indian financial markets. "
    "Focus on signals that mention specific companies, earnings, regulatory changes, "
    "FII/DII activity, or macroeconomic factors affecting Indian equities."
)

from .llm.scorer import SignalScorer
from .llm.router import LLMRouter

from utils.logger import get_logger
logger = get_logger('aide.stock_pipeline')
from utils.task_manager import TaskManager, TaskStatus
from db.supabase_client import supabase

class SupabaseClient:
    def __init__(self):
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        self.client = create_client(url, key)

    def fetch_unscored(self, limit: int = 100) -> list:
        try:
            response = (self.client.table("stock_signals")
                .select("*")
                .eq("scored", False)
                .order("crawled_at", desc=False)
                .limit(limit)
                .execute())
            return response.data
        except Exception as e:
            logger.error("Failed to fetch unscored stock signals: %s", e)
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

            # 5. Use LLM-provided sentiment first, fall back to score threshold
            sentiment = score.get("sentiment", None)
            if not sentiment:
                sw = payload.get("score_weighted", 0.0)
                if sw >= 7:
                    sentiment = "bullish"
                elif sw <= 3:
                    sentiment = "bearish"
                else:
                    sentiment = "neutral"
            
            payload["sentiment"] = sentiment
            payload["tickers"] = None

            response = self.client.table("stock_signals").update(payload).eq("id", record_id).execute()
            if not response.data:
                logger.error("Update returned no data for id=%s — possible RLS block or missing row", record_id)
        except Exception as e:
            logger.error("Failed to write result for id=%s: %s", record_id, e)

def run(batch_size: int = 100, delay_between: float = 0.5):
    tm = TaskManager()
    task_id = tm.create_task("stock_scoring_pipeline", metadata={"batch_size": batch_size})
    tm.update_task(task_id, status=TaskStatus.PROCESSING, message="Fetching unscored stock signals")
    logger.info("=== AIDE stock scoring pipeline starting ===")

    pb      = SupabaseClient()
    scorer  = SignalScorer()
    router  = scorer.router

    signals = pb.fetch_unscored(limit=batch_size)
    logger.info("Fetched %d unscored stock signals", len(signals))

    if not signals:
        logger.info("Nothing to score. Exiting cleanly.")
        router.log_budget()
        push_budget_to_supabase(router.budget._state, 0)
        return

    success = 0
    failed  = 0

    for i, signal in enumerate(signals, 1):
        sid = signal["id"]
        logger.info("--- Stock Signal %d/%d  id=%s ---", i, len(signals), sid)

        try:
            result = scorer.process_signal(signal)
            pb.write_result(sid, result)
            success += 1
            pct = int((i / len(signals)) * 100)
            tm.update_task(task_id, progress=pct, message=f"Scored {i}/{len(signals)} stock signals")
            logger.info("Written id=%s  provider=%s",
                        sid, (result.get("score") or {}).get("_provider", "?"))
        except Exception as e:
            failed += 1
            logger.error("Failed on id=%s: %s", sid, e)
            tm.update_task(task_id, message=f"Error on stock signal {i}/{len(signals)}: {e}")

        time.sleep(delay_between)

    logger.info(
        "=== Stock Pipeline done: %d succeeded, %d failed ===",
        success, failed,
    )
    tm.complete_task(task_id, result={"success": success, "failed": failed, "total": len(signals)})
    router.log_budget()
    push_budget_to_supabase(router.budget._state, len(signals))

def push_budget_to_supabase(budget_state, signals_processed):
    if not supabase or not budget_state:
        return
        
    usage_dict = budget_state.get("usage", {})
    if not usage_dict:
        return
        
    pushed = 0
    for provider, tokens in usage_dict.items():
        try:
            payload = {
                "provider": provider,
                "tokens_used": tokens,
                "signals_processed": signals_processed,
                "errors": 0,
                "cost_usd": 0.0
            }
            supabase.table("budget_runs").insert(payload).execute()
            pushed += 1
        except Exception as e:
            logger.warning("Failed to push budget for %s: %s", provider, e)
            
    if pushed > 0:
        logger.info("Budget pushed to Supabase: %d provider rows", pushed)

if __name__ == "__main__":
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    run(batch_size=batch)
