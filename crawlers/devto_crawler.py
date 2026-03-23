from utils.logger import get_logger
from db.supabase_client import save_signal, load_title_cache
import hashlib, requests
from datetime import datetime, timezone

logger = get_logger("devto_crawler")

def crawl_devto():
    load_title_cache()
    tags = ["ai", "machinelearning", "python", "webdev"]
    
    for tag in tags:
        try:
            url_str = f"https://dev.to/api/articles?tag={tag}&per_page=30"
            headers = {"User-Agent": "AIDE-crawler/1.0"}
            response = requests.get(url_str, headers=headers)
            response.raise_for_status()
            
            articles = response.json()
            inserted_count = 0
            
            for article in articles:
                title = article["title"]
                url = article["url"]
                raw_content = article.get("description", "")[:500]
                
                if not url:
                    continue
                if not title:
                    continue
                    
                url_hash = hashlib.md5(url.encode()).hexdigest()
                
                signal = {
                    "title": title,
                    "url": url,
                    "url_hash": url_hash,
                    "source": "devto",
                    "raw_content": raw_content if raw_content else title,
                    "scored": False,
                    "crawled_at": datetime.now(timezone.utc).isoformat()
                }
                
                saved = save_signal(signal)
                if saved:
                    inserted_count += 1
                
            logger.info(f"Inserted {inserted_count} new signals for tag {tag}")
            
        except Exception as e:
            logger.error(f"Error crawling tag {tag}: {e}")
            continue

if __name__ == "__main__":
    crawl_devto()
