import os
import sys
import uuid
import hashlib
import requests
import html
from bs4 import BeautifulSoup
from datetime import datetime

# Ensure the root project directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from utils.retry import retry_with_backoff
from db.supabase_client import supabase

logger = get_logger("zerodha_crawler")

PULSE_URL = "https://pulse.zerodha.com"

@retry_with_backoff(max_retries=3, initial_delay=2.0)
def _fetch_page(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def fetch_zerodha_articles():
    logger.info("Fetching Zerodha Pulse articles...")
    signals = []
    
    try:
        html_content = _fetch_page(PULSE_URL)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        items = soup.find_all('li', class_='item')
        
        for item in items:
            # Find title
            title_tag = item.find(['h2', 'h3'])
            title = title_tag.get_text(strip=True) if title_tag else ""
            
            # Find url
            url = ""
            for a_tag in item.find_all('a', href=True):
                href = a_tag['href']
                if "zerodha.com" not in href and href.startswith("http"):
                    url = href
                    break
            
            # Find raw_content
            raw_content = ""
            desc_tag = item.find(['div', 'p'], class_=lambda c: c and any(sub in c.lower() for sub in ['desc', 'sum']))
            if not desc_tag:
                # If no specific class, just find the first paragraph that has some length
                p_tags = item.find_all('p')
                for p in p_tags:
                    text_p = p.get_text(strip=True)
                    if len(text_p) > 20:
                        raw_content = text_p
                        break
                        
            if desc_tag and not raw_content:
                raw_content = desc_tag.get_text(strip=True)
                
            if not raw_content:
                raw_content = title
                
            # Clean html entities
            title = html.unescape(title) if title else title
            raw_content = html.unescape(raw_content) if raw_content else raw_content
            
            if not title or not url:
                continue

            # Keyword relevance filter
            SKIP_KEYWORDS = [
                "ipl", "cricket", "bollywood", "movie", "film", "trailer", "song",
                "actor", "actress", "match", "wicket", "goal", "football", "sports",
                "arrested", "murder", "crime", "accident", "stolen", "army", "military",
                "missile", "drone", "war live", "iran war", "houthi", "israel",
                "election", "vote", "candidate", "constituency", "party win",
                "exam result", "rrb", "ssc", "neet", "jee",
            ]
            
            if any(kw in title.lower() for kw in SKIP_KEYWORDS):
                continue
                
            signals.append({
                "title": title,
                "url": url,
                "raw_content": raw_content,
                "source": "zerodha_pulse"
            })
            
    except Exception as e:
        logger.warning(f"Error fetching/parsing Zerodha Pulse: {e}")
            
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
    logger.info("Starting Zerodha Pulse crawler")
    signals = fetch_zerodha_articles()
    
    saved_count = 0
    for signal in signals:
        if save_stock_signal(signal):
            saved_count += 1
            
    logger.info(f"Zerodha Pulse crawler: {saved_count} new signals saved")
    return saved_count

if __name__ == "__main__":
    run()
