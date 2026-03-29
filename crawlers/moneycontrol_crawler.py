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

logger = get_logger("moneycontrol_crawler")

RSS_FEEDS = [
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.moneycontrol.com/rss/buzzingstocks.xml",
    "https://www.moneycontrol.com/rss/latestnews.xml",
    "https://www.moneycontrol.com/rss/results.xml"
]

@retry_with_backoff(max_retries=3, initial_delay=2.0)
def _fetch_rss(url):
    return feedparser.parse(url)

def fetch_mc_articles():
    logger.info("Fetching Moneycontrol articles from RSS feeds...")
    signals = []
    
    for feed_url in RSS_FEEDS:
        try:
            logger.info(f"Fetching {feed_url}")
            feed = _fetch_rss(feed_url)
            
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                
                raw_content = entry.get("summary", "")
                if not raw_content:
                    raw_content = entry.get("description", "")
                
                # Strip all HTML tags
                raw_content = re.sub(r'<[^>]+>', '', raw_content)
                # Strip URLs
                raw_content = re.sub(r'http\S+', '', raw_content)
                # Strip extra whitespace
                raw_content = ' '.join(raw_content.split())
                # Unescape HTML entities
                raw_content = html.unescape(raw_content)
                # Trim to 2000 chars
                raw_content = raw_content[:2000]

                # If raw_content is empty or too short after cleaning, use title instead
                if not raw_content or len(raw_content) < 30:
                    raw_content = title

                # Clean html entities for title
                title = html.unescape(title) if title else title
                
                if not title or not url:
                    continue
                    
                signals.append({
                    "title": title,
                    "url": url,
                    "raw_content": raw_content,
                    "source": "moneycontrol"
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
    logger.info("Starting Moneycontrol crawler")
    signals = fetch_mc_articles()
    
    saved_count = 0
    for signal in signals:
        if save_stock_signal(signal):
            saved_count += 1
            
    logger.info(f"Moneycontrol crawler: {saved_count} new signals saved")
    return saved_count

if __name__ == "__main__":
    run()
