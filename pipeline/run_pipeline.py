import sys
import os
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config_validator import require_config; require_config(require_llm=False)
from utils.logger import get_logger
logger = get_logger('aide.pipeline')

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
    logger.info(f"AIDE Pipeline starting at {start_time}")
    logger.info("=" * 50)
    
    logger.info("Loading title cache...")
    load_title_cache()
    
    # 1. Run Hacker News Crawler
    logger.info("Running Hacker News Crawler...")
    run_hn_crawler()
    logger.info("-" * 50)
    
    # 2. Run arXiv Crawler
    logger.info("Running arXiv Crawler...")
    run_arxiv_crawler()
    logger.info("-" * 50)
    
    # 3. Run GitHub Trending Crawler
    logger.info("Running GitHub Trending Crawler...")
    run_github_crawler()
    logger.info("=" * 50)
    
    end_time = datetime.now()
    logger.info(f"AIDE Pipeline complete at {end_time}")
    logger.info(f"Total duration: {end_time - start_time}")

if __name__ == "__main__":
    run_full_pipeline()
