import os
import sys
import uuid
import hashlib
import requests
import xml.etree.ElementTree as ET
import html
from datetime import datetime

# Ensure the root project directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from utils.retry import retry_with_backoff
from db.supabase_client import supabase

logger = get_logger("nse_crawler")

RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rss.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.moneycontrol.com/rss/buzzingstocks.xml",
    "https://feeds.feedburner.com/ndtvprofit-latest"
]

@retry_with_backoff(max_retries=3, initial_delay=2.0)
def _fetch_rss(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    # Handle possible encoding issues or weird characters
    return response.text

def fetch_nse_announcements():
    logger.info("Fetching NSE/BSE corporate announcements from RSS feeds...")
    signals = []
    
    for feed_url in RSS_FEEDS:
        try:
            logger.info(f"Fetching {feed_url}")
            xml_data = _fetch_rss(feed_url)
            root = ET.fromstring(xml_data)
            
            for item in root.findall('.//item'):
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                raw_content = item.findtext('description', '').strip()
                pub_date = item.findtext('pubDate', '').strip()

                title = html.unescape(title) if title else title
                raw_content = html.unescape(raw_content) if raw_content else raw_content
                
                if not title or not link:
                    continue
                    
                signals.append({
                    "title": title,
                    "url": link,
                    "raw_content": raw_content,
                    "source": "nse_bse"
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
    logger.info("Starting NSE/BSE crawler")
    signals = fetch_nse_announcements()
    
    saved_count = 0
    for signal in signals:
        if save_stock_signal(signal):
            saved_count += 1
            
    logger.info(f"NSE/BSE crawler: {saved_count} new signals saved")
    return saved_count

if __name__ == "__main__":
    run()
