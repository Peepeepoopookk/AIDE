"""
AIDE Router — Local Test
Run this before pushing to verify your API keys work.

Usage:
    python test_router.py
"""

import os
from dotenv import load_dotenv
load_dotenv()
import sys

# Manually set env vars for testing — replace with your real keys
# (or export them in your terminal before running)
TEST_KEYS = {
    "CEREBRAS_API_KEY":   os.environ.get("CEREBRAS_API_KEY", ""),
    "GROQ_API_KEY":       os.environ.get("GROQ_API_KEY", ""),
    "MISTRAL_API_KEY":    os.environ.get("MISTRAL_API_KEY", ""),
    "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
}

missing = [k for k, v in TEST_KEYS.items() if not v]
if missing:
    print(f"[warn] Missing keys (will skip those providers): {missing}")

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

sys.path.insert(0, ".")
from aide_router.llm.scorer import SignalScorer

TEST_SIGNAL = {
    "id":      "test-001",
    "content": "Apple reports record Q1 earnings, beats analyst expectations by 12%. CEO Tim Cook hints at major product announcement at WWDC.",
    "source":  "reuters",
    "asset":   "AAPL",
}

def main():
    scorer = SignalScorer()

    print("\n=== Testing classify ===")
    classification = scorer.classify(TEST_SIGNAL["content"], TEST_SIGNAL["source"])
    print(classification)

    print("\n=== Testing score ===")
    scoring = scorer.score(TEST_SIGNAL["content"], TEST_SIGNAL["asset"])
    print(scoring)

    print("\n=== Testing summarize ===")
    summary = scorer.summarize(TEST_SIGNAL["content"])
    print(summary)

    print("\n=== Testing full pipeline ===")
    result = scorer.process_signal(TEST_SIGNAL)
    print(f"Category:   {result['classification'].get('category')}")
    print(f"Relevance:  {result['score'].get('relevance_score') if result['score'] else 'N/A'}")
    print(f"Sentiment:  {result['score'].get('sentiment') if result['score'] else 'N/A'}")
    print(f"Headline:   {result['summary'].get('headline') if result['summary'] else 'N/A'}")
    print(f"Analysis:   {'yes' if result['analysis'] else 'no (relevance < 7)'}")

    print("\n=== Budget state ===")
    scorer.router.log_budget()

if __name__ == "__main__":
    main()
