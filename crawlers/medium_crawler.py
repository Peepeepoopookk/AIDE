from utils.logger import get_logger
from db.supabase_client import save_signal, load_title_cache
import hashlib, requests
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

logger = get_logger("medium_crawler")

def crawl_medium():
    load_title_cache()
    
    tags = ["artificial-intelligence", "machine-learning", "python", "programming"]
    headers = {"User-Agent": "AIDE-crawler/1.0"}
    
    for tag in tags:
        try:
            feed_url = f"https://medium.com/feed/tag/{tag}"
            response = requests.get(feed_url, headers=headers)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            
            inserted_count = 0
            
            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                url = item.findtext("link", "").strip()
                raw_content = item.findtext("description", "")
                
                if raw_content is not None:
                    while "<" in raw_content and ">" in raw_content:
                        start = raw_content.find("<")
                        end = raw_content.find(">", start)
                        if end != -1:
                            raw_content = raw_content.replace(raw_content[start:end+1], " ")
                        else:
                            break
                    raw_content = raw_content[:500]
                
                if not url:
                    continue
                if not title:
                    continue
                
                url_hash = hashlib.md5(url.encode()).hexdigest()
                
                signal = {
                    "title": title,
                    "url": url,
                    "url_hash": url_hash,
                    "source": "medium",
                    "raw_content": raw_content if raw_content else title,
                    "scored": False,
                    "crawled_at": datetime.now(timezone.utc).isoformat()
                }
                
                saved = save_signal(signal)
                if saved is True:
                    inserted_count += 1
            
            logger.info(f"Inserted {inserted_count} new signals for tag {tag}")
            
        except Exception as e:
            logger.error(f"Error crawling Medium tag {tag}: {e}")

if __name__ == "__main__":
    crawl_medium()
