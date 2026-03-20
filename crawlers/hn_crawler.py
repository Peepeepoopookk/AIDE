import sys
import os
import time
import hashlib
import httpx
from datetime import datetime, timezone

# Ensure the root project directory is in the path to import db modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import save_signal, check_duplicate

def run_hn_crawler():
    """
    Main function to crawl the top stories from Hacker News.
    """
    print("Starting Hacker News crawler...")
    
    # Endpoint for retrieving top story IDs
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    
    try:
        # Fetch the top stories list
        response = httpx.get(top_stories_url)
        response.raise_for_status()
        top_ids = response.json()
    except httpx.RequestError as e:
        print(f"Error fetching top stories: {e}")
        return

    # Limit to the top 30 story IDs as requested
    top_30_ids = top_ids[:30]
    
    # Keep track of how many new signals we successfully save
    saved_count = 0
    
    # Iterate through each story ID
    for story_id in top_30_ids:
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        
        try:
            # Fetch individual story details
            story_res = httpx.get(story_url)
            story_res.raise_for_status()
            story = story_res.json()
        except httpx.RequestError as e:
            print(f"Error fetching story {story_id}: {e}")
            time.sleep(0.5)
            continue
            
        # Skip text-only posts which don't have a 'url' field
        if not story or "url" not in story:
            time.sleep(0.5) # Still wait before fetching the next one
            continue
            
        url = story.get("url")
        title = story.get("title", "")
        
        # Generate an MD5 hash of the URL to check for duplicates
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Check if this signal already exists in the database
        if check_duplicate(url_hash):
            print(f"Duplicate skipped: {title}")
            time.sleep(0.5)
            continue
            
        # Extract metadata for raw_content
        score = story.get("score", 0)
        comments = story.get("descendants", 0) # HN API uses 'descendants' for comments count
        author = story.get("by", "unknown")
        
        # Build the exact signal dictionary required
        signal = {
            "title": title,
            "url": url,
            "source": "hacker_news",
            "raw_content": f"HN Score: {score} | Comments: {comments} | By: {author}",
            "url_hash": url_hash,
            "score_novelty": 0.0,
            "score_hype": 0.0,
            "score_impact": 0.0,
            "score_total": 0.0,
            "tags": ["hacker_news"],
            "gemini_summary": "",
            "crawled_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Save the signal to PocketBase
        saved_record = save_signal(signal)
        if saved_record:
            print(f"Saved: {title}")
            saved_count += 1
            
        # Add a 0.5 second delay before fetching the next story
        time.sleep(0.5)
        
    print(f"HN crawler done. Saved {saved_count} new signals.")


if __name__ == "__main__":
    run_hn_crawler()
