import sys
import os
from datetime import datetime

# Ensure the root project directory is in the path to import all modules correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
logger = get_logger('aide.stock_pipeline')

# Add the root project directory to the path so modules can be found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import stock crawler run functions
from crawlers.nse_crawler import run as run_nse_crawler
from crawlers.moneycontrol_crawler import run as run_moneycontrol
from crawlers.zerodha_crawler import run as run_zerodha
from crawlers.reddit_india_crawler import run as run_reddit_india

# --- ADD NEW STOCK CRAWLER IMPORTS HERE ---

def run_stock_pipeline():
    """
    Master pipeline runner that executes all stock-related crawlers in sequence.
    """
    start_time = datetime.now()
    logger.info(f"Stock Pipeline starting at {start_time}")
    logger.info("=" * 50)
    
    total_new_signals = 0
    
    # 1. NSE/BSE Crawler
    try:
        logger.info("Running NSE/BSE Crawler...")
        # nse_crawler.run() returns the count of new signals saved
        new_signals = run_nse_crawler()
        logger.info(f"nse_crawler: {new_signals} new signals")
        total_new_signals += (new_signals if isinstance(new_signals, int) else 0)
    except Exception as e:
        logger.error(f"Error in NSE/BSE Crawler: {e}")
    
    logger.info("-" * 50)
    
    # 2. Moneycontrol Crawler
    logger.info("Running Moneycontrol Crawler...")
    try:
        count = run_moneycontrol()
        total_new_signals += (count if isinstance(count, int) else 0)
        logger.info(f"moneycontrol_crawler: {count} new signals")
    except Exception as e:
        logger.warning(f"moneycontrol_crawler failed: {e}")
    
    logger.info("-" * 50)
    
    # 3. Zerodha Pulse Crawler
    logger.info("Running Zerodha Pulse Crawler...")
    try:
        count = run_zerodha()
        total_new_signals += (count if isinstance(count, int) else 0)
        logger.info(f"zerodha_crawler: {count} new signals")
    except Exception as e:
        logger.warning(f"zerodha_crawler failed: {e}")
    
    logger.info("-" * 50)
    
    # 4. Reddit India Crawler
    logger.info("Running Reddit India Crawler...")
    try:
        count = run_reddit_india()
        total_new_signals += (count if isinstance(count, int) else 0)
        logger.info(f"reddit_india_crawler: {count} new signals")
    except Exception as e:
        logger.warning(f"reddit_india_crawler failed: {e}")
    
    logger.info("-" * 50)
    
    # --- ADD NEW STOCK CRAWLERS HERE ---
    
    end_time = datetime.now()
    logger.info(f"Stock pipeline done: {total_new_signals} total new signals")
    logger.info(f"Total duration: {end_time - start_time}")

if __name__ == "__main__":
    run_stock_pipeline()
