from utils.logger import get_logger
from db.supabase_client import save_signal, load_title_cache
import hashlib, requests, os
from datetime import datetime, timezone
import feedparser
from bs4 import BeautifulSoup

logger = get_logger("reddit_crawler")

def fetch_subreddit(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/.rss"
    headers = {"User-Agent": "AIDE-bot/1.0 (RSS reader)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return feedparser.parse(response.content)

def crawl_reddit():
    load_title_cache()
    subreddits = ["MachineLearning", "LocalLLaMA", "programming", "artificial"]
    # Using the shared supabase client imported above
    
    for subreddit in subreddits:
        try:
            data = fetch_subreddit(subreddit)
            inserted_count = 0
            
            for entry in data.get("entries", []):
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                summary = entry.get("summary", "")
                if summary:
                    soup = BeautifulSoup(summary, "html.parser")
                    description = soup.get_text().strip()
                else:
                    description = ""
                
                author = entry.get("author", "").strip()
                
                if not url:
                    continue
                if not title:
                    continue
                    
                url_hash = hashlib.md5(url.encode()).hexdigest()
                
                signal = {
                    "title": title,
                    "url": url,
                    "url_hash": url_hash,
                    "source": "reddit",
                    "raw_content": description[:500] if description else title,
                    "scored": False,
                    "crawled_at": datetime.now(timezone.utc).isoformat()
                }
                
                saved = save_signal(signal)
                if saved:
                    inserted_count += 1
                
            logger.info(f"Inserted {inserted_count} new signals for r/{subreddit}")
            
        except Exception as e:
            logger.error(f"Error crawling subreddit {subreddit}: {e}")
            continue

if __name__ == "__main__":
    crawl_reddit()
