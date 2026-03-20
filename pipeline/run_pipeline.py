import sys
import os
from datetime import datetime

# Add the root project directory to the path so modules can be found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import crawler run functions
from crawlers.hn_crawler import run_hn_crawler
from crawlers.arxiv_crawler import run_arxiv_crawler
from crawlers.github_crawler import run_github_crawler
from db.supabase_client import load_title_cache

def run_full_pipeline():
    """
    Master pipeline runner that executes all AIDE crawlers in sequence.
    """
    start_time = datetime.now()
    print(f"AIDE Pipeline starting at {start_time}")
    print("=" * 50)
    
    print("Loading title cache...")
    load_title_cache()
    
    # 1. Run Hacker News Crawler
    print("Running Hacker News Crawler...")
    run_hn_crawler()
    print("-" * 50)
    
    # 2. Run arXiv Crawler
    print("Running arXiv Crawler...")
    run_arxiv_crawler()
    print("-" * 50)
    
    # 3. Run GitHub Trending Crawler
    print("Running GitHub Trending Crawler...")
    run_github_crawler()
    print("=" * 50)
    
    end_time = datetime.now()
    print(f"AIDE Pipeline complete at {end_time}")
    print(f"Total duration: {end_time - start_time}")

if __name__ == "__main__":
    run_full_pipeline()
