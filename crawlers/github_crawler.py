import sys
import os
import time
import hashlib
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# Add the root project directory to the path so db module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import save_signal, check_duplicate

def run_github_crawler():
    """
    Main function to crawl GitHub Trending pages and save repositories as signals.
    """
    print("Starting GitHub Trending crawler...")
    
    # URLs to scrape
    urls = [
        "https://github.com/trending?since=daily",
        "https://github.com/trending?since=weekly"
    ]
    
    # Exact User-Agent header required to avoid being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    saved_count = 0
    
    for i, url in enumerate(urls):
        print(f"Crawling GitHub Trending: {url}")
        
        try:
            # Fetch the GitHub Trending page
            response = httpx.get(url, headers=headers, timeout=15.0)
            response.raise_for_status()
        except httpx.RequestError as e:
            print(f"Error fetching URL {url}: {e}")
            continue
            
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all trending repository articles
        articles = soup.find_all("article", class_="Box-row")
        
        for article in articles:
            # 1. Extract repo path from h2 > a
            h2 = article.find("h2")
            if not h2:
                continue
                
            a_tag = h2.find("a")
            if not a_tag or not a_tag.get("href"):
                continue
                
            repo_path = a_tag["href"]
            
            # 2. Construct full URL and repo name
            full_url = "https://github.com" + repo_path
            repo_name = repo_path.strip("/").replace("/", " / ")
            
            # 3. Extract description
            p_tag = article.find("p")
            description = p_tag.get_text(strip=True) if p_tag else ""
            
            # 4. Extract language
            lang_span = article.find("span", itemprop="programmingLanguage")
            language = lang_span.get_text(strip=True) if lang_span else "Unknown"
            
            # 5. Extract stars
            stars = "0"
            stargazers_a = article.find("a", href=lambda h: h and h.endswith("/stargazers"))
            if stargazers_a:
                stars_text = stargazers_a.get_text(strip=True)
                stars = stars_text.replace(",", "")
                
            # 6. Generate MD5 hash of the URL
            url_hash = hashlib.md5(full_url.encode()).hexdigest()
            
            # 7. Check for duplicates
            if check_duplicate(url_hash):
                print(f"Duplicate skipped: {repo_name}")
                time.sleep(1) # 1 second delay between repos
                continue
                
            # 8. Build the exact signal dictionary required
            signal = {
                "title": repo_name,
                "url": full_url,
                "source": "github_trending",
                "raw_content": f"Description: {description} | Language: {language} | Stars: {stars}",
                "url_hash": url_hash,
                "score_novelty": 0.0,
                "score_hype": 0.0,
                "score_impact": 0.0,
                "score_total": 0.0,
                "tags": ["github", "open-source", language.lower()],
                "gemini_summary": "",
                "crawled_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 9. Save the signal
            saved_record = save_signal(signal)
            if saved_record:
                print(f"Saved: {repo_name}")
                saved_count += 1
                
            # 10. Add a 1 second delay between each repo
            time.sleep(1)
            
        # Add a 3 second delay between the two pages (if not the last page)
        if i < len(urls) - 1:
            time.sleep(3)
            
    print(f"GitHub crawler done. Saved {saved_count} new signals.")

if __name__ == "__main__":
    run_github_crawler()
