import os
import sys
import uuid
import hashlib
import re
import html
import feedparser
from datetime import datetime

# Ensure the root project directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from utils.retry import retry_with_backoff
from db.supabase_client import supabase

logger = get_logger("reddit_india_crawler")

RSS_FEEDS = [
    "https://www.reddit.com/r/IndiaInvestments/hot/.rss",
    "https://www.reddit.com/r/DalalStreetTalks/hot/.rss"
]

@retry_with_backoff(max_retries=3, initial_delay=2.0)
def _fetch_rss(url):
    # feedparser.parse can take a URL directly
    return feedparser.parse(url)

def fetch_reddit_posts():
    logger.info("Fetching Indian investment subreddit posts...")
    signals = []
    
    SKIP_KEYWORDS = [
        "ipl", "cricket", "bollywood", "movie", "film", "meme",
        "joke", "funny", "rant", "marriage", "wedding", "career advice",
        "which college", "which course", "salary", "job offer",
    ]
    
    for feed_url in RSS_FEEDS:
        try:
            logger.info(f"Fetching {feed_url}")
            feed = _fetch_rss(feed_url)
            
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                
                # Filter by keyword
                if any(kw in title.lower() for kw in SKIP_KEYWORDS):
                    continue
                
                raw_content = entry.get("summary", "")
                # Strip HTML tags
                raw_content = re.sub(r'<[^>]+>', '', raw_content).strip()
                
                if not raw_content:
                    raw_content = title
                
                # Clean html entities
                title = html.unescape(title) if title else title
                raw_content = html.unescape(raw_content) if raw_content else raw_content
                
                if not title or not url:
                    continue
                    
                signals.append({
                    "title": title,
                    "url": url,
                    "raw_content": raw_content,
                    "source": "reddit_india"
                })
        except Exception as e:
            logger.warning(f"Error fetching/parsing feed {feed_url}: {e}")
            
    return signals

def save_stock_signal(signal):
    if not supabase:
        logger.warning("Supabase client not initialized")
        return False
        
    url_hash = hashlib.md5(signal['url'].encode()).hexdigest()
    
    # Deduplication check
    try:
        response = supabase.table("stock_signals").select("id").eq("url_hash", url_hash).limit(1).execute()
        if response.data and len(response.data) > 0:
            logger.info(f"Duplicate skipped: {signal['title']}")
            return False
    except Exception as e:
        logger.warning(f"Error checking duplicate for {signal['url']}: {e}")
        return False
        
    # Prepare data for insertion
    raw_content = signal['raw_content'] if signal['raw_content'] else signal['title']
    raw_content = raw_content[:2000]
    
    data = {
        "id": str(uuid.uuid4()),
        "title": signal['title'][:255] if signal['title'] else "",
        "url": signal['url'],
        "source": signal['source'],
        "raw_content": raw_content,
        "crawled_at": datetime.utcnow().isoformat(),
        "url_hash": url_hash,
        "scored": False,
        "sentiment": None,
        "tickers": None
    }
    
    try:
        supabase.table("stock_signals").insert(data).execute()
        logger.info(f"Saved: {signal['title']}")
        return True
    except Exception as e:
        logger.warning(f"Error saving signal {signal['url']}: {e}")
        return False

def run():
    logger.info("Starting Reddit India crawler")
    signals = fetch_reddit_posts()
    
    saved_count = 0
    for signal in signals:
        if save_stock_signal(signal):
            saved_count += 1
            
    logger.info(f"Reddit India crawler: {saved_count} new signals saved")
    return saved_count

if __name__ == "__main__":
    run()
