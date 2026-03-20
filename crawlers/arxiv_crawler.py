import sys
import os
import time
import hashlib
import re
import httpx
import feedparser
from datetime import datetime, timezone

# Allow importing from db module securely
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import save_signal, check_duplicate

def clean_html(text):
    """
    Remove HTML tags and newlines from a text string.
    """
    if not text:
        return ""
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', '', text).strip()
    # Remove newlines
    cleaned = cleaned.replace('\n', ' ').replace('\r', '')
    # Replace multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def run_arxiv_crawler():
    """
    Main function to crawl arXiv RSS feeds and save them as signals.
    """
    print("Starting arXiv crawler...")
    
    # List of arXiv RSS feeds to crawl
    rss_feeds = [
        "https://rss.arxiv.org/rss/cs.AI",
        "https://rss.arxiv.org/rss/cs.LG",
        "https://rss.arxiv.org/rss/cs.CL"
    ]
    
    saved_count = 0
    
    for feed_url in rss_feeds:
        print(f"Crawling arXiv feed: {feed_url}")
        
        try:
            # Fetch RSS feed using httpx
            response = httpx.get(feed_url, timeout=10.0)
            response.raise_for_status()
            
            # Parse the RSS feed with feedparser
            feed = feedparser.parse(response.text)
        except httpx.RequestError as e:
            print(f"Error fetching feed {feed_url}: {e}")
            continue
            
        # Get up to 15 entries from the feed
        entries = feed.entries[:15]
        
        for entry in entries:
            # 1. Clean the title
            raw_title = entry.get("title", "")
            title = clean_html(raw_title)
            
            # 2. Get the URL
            url = entry.get("link", "")
            if not url:
                time.sleep(0.3)
                continue
                
            # 3. Extract authors (max 3)
            # feedparser usually parses authors into a list of dictionaries with a 'name' key
            authors_list = entry.get("authors", [])
            author_names = []
            for a in authors_list:
                if isinstance(a, dict) and "name" in a:
                    author_names.append(a["name"])
                else:
                    author_names.append(str(a))
            
            # Fallback to the 'author' field if authors list is empty
            if not author_names and entry.get("author"):
                author_names.append(entry.get("author"))
                
            author_str = ", ".join(author_names[:3])
            
            # 4. Clean summary and limit to 500 characters
            raw_summary = entry.get("summary", "")
            cleaned_summary = clean_html(raw_summary)
            summary_preview = cleaned_summary[:500]
            
            # Generate MD5 hash of the URL to check for duplicates
            url_hash = hashlib.md5(url.encode()).hexdigest()
            
            # Check for duplicates before saving
            if check_duplicate(url_hash):
                print(f"Duplicate skipped: {title}")
                time.sleep(0.3)
                continue
                
            # Build the exact signal dictionary required
            signal = {
                "title": title,
                "url": url,
                "source": "arxiv",
                "raw_content": summary_preview,
                "url_hash": url_hash,
                "score_novelty": 0.0,
                "score_hype": 0.0,
                "score_impact": 0.0,
                "score_total": 0.0,
                "tags": ["arxiv", "research"],
                "gemini_summary": "",
                "crawled_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Save the signal to PocketBase
            saved_record = save_signal(signal)
            if saved_record:
                print(f"Saved: {title}")
                saved_count += 1
                
            # Delay 0.3 seconds between each paper
            time.sleep(0.3)
            
    print(f"arXiv crawler done. Saved {saved_count} new signals.")

if __name__ == "__main__":
    run_arxiv_crawler()
