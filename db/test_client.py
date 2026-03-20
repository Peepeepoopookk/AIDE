import sys
sys.path.append('.')

from db.pocketbase_client import save_signal, check_duplicate, get_top_signals
import hashlib

# Test 1: Save a fake signal
print("--- Test 1: Saving a signal ---")
test_signal = {
    "title": "Test Signal - AIDE is working",
    "url": "https://example.com/test",
    "source": "test",
    "raw_content": "This is a test signal to verify PocketBase is working.",
    "url_hash": hashlib.md5("https://example.com/test".encode()).hexdigest(),
    "score_novelty": 7.0,
    "score_hype": 5.0,
    "score_impact": 8.0,
    "score_total": 6.7,
    "tags": ["test"],
    "gemini_summary": "This is a test.",
    "crawled_at": "2026-03-20T00:00:00Z"
}
result = save_signal(test_signal)
print(f"Result: {result}")

# Test 2: Check duplicate
print("\n--- Test 2: Checking duplicate ---")
is_dup = check_duplicate(test_signal["url_hash"])
print(f"Is duplicate: {is_dup}")

# Test 3: Get top signals
print("\n--- Test 3: Getting top signals ---")
top = get_top_signals(limit=5)
print(f"Top signals count: {len(top)}")
for s in top:
    print(f"  - {s.get('title')} | score: {s.get('score_total')}")
