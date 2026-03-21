import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from rapidfuzz import fuzz
from utils.logger import get_logger

logger = get_logger('aide.db')

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Warning: SUPABASE_URL or SUPABASE_KEY is not set.")
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# In-memory cache of existing signal titles for fuzzy matching
_title_cache = []

def _fetch_paginated(table: str, columns: list, page_size: int = 500, filters: dict = None) -> list:
    """Fetch all rows from a Supabase table using range-based pagination."""
    if not supabase:
        return []
    all_rows = []
    start = 0
    while True:
        try:
            query = supabase.table(table).select(", ".join(columns))
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            batch = query.range(start, start + page_size - 1).execute().data
            if not batch:
                break
            all_rows.extend(batch)
            if len(batch) < page_size:
                break
            start += page_size
        except Exception as e:
            logger.error("Paginated fetch error on table=%s at offset=%d: %s", table, start, e)
            break
    return all_rows

def load_title_cache() -> list:
    """
    Loads all existing signal titles from Supabase into memory.
    Call this once at the start of each crawler run.
    This avoids making a separate API call for every single signal.
    """
    global _title_cache
    if not supabase:
        logger.warning("Cannot load title cache: Supabase client not initialized")
        return []
    rows = _fetch_paginated("signals", ["title"])
    _title_cache = [r.get("title", "") for r in rows if r.get("title")]
    logger.info("Title cache loaded: %d titles", len(_title_cache))
    return _title_cache

def save_signal(signal: dict) -> bool:
    """
    Saves a record to the 'signals' table.
    
    Args:
        signal (dict): The dictionary containing the signal data to be saved.
        
    Returns:
        bool: True if created, False if duplicate or failure.
    """
    if not supabase:
        print("Failed to save signal: Supabase client not initialized.")
        return False
        
    # Check duplicate by exact URL
    url = signal.get("url", "")
    if url and check_duplicate(url):
        print(f"Duplicate skipped (URL exists): {url}")
        return False

    # Check fuzzy duplicate by title
    title = signal.get("title", "")
    if title and check_fuzzy_duplicate(title):
        print(f"Fuzzy duplicate skipped: {title[:60]}")
        return False

    # Prepare data for insertion
    data = signal.copy()
    
    # Ensure ID
    if "id" not in data or not data["id"]:
        data["id"] = str(uuid.uuid4())
        
    # Ensure created timestamp
    if "created" not in data or not data["created"]:
        # Supabase prefers ISO format timestamps
        data["created"] = datetime.now(timezone.utc).isoformat()
        
    try:
        response = supabase.table("signals").insert(data).execute()
        print(f"Successfully saved signal record with ID: {data['id']}")
        return True
    except Exception as e:
        print(f"Error saving signal record: {e}")
        return False

def check_duplicate(url: str) -> bool:
    """
    Checks if a signal with the given url already exists in the 'signals' table.
    
    Args:
        url (str): The url to check for duplicates.
        
    Returns:
        bool: True if a duplicate exists, False if not.
    """
    if not supabase:
        return False
        
    try:
        response = supabase.table("signals").select("id").eq("url", url).limit(1).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking for duplicate signal: {e}")
        return False

def check_fuzzy_duplicate(title: str, threshold: int = 90) -> bool:
    """
    Checks if a signal with a similar title already exists in the database.
    Uses fuzzy string matching to catch near-duplicate titles even if URLs differ.
    
    Args:
        title: The title of the new signal to check
        threshold: Similarity percentage required to consider it a duplicate (default 90%)
    
    Returns:
        bool: True if a similar title exists, False if not
    """
    if not _title_cache:
        return False
        
    for existing_title in _title_cache:
        similarity = fuzz.ratio(title.lower(), existing_title.lower())
        if similarity >= threshold:
            print(f"Fuzzy duplicate found ({similarity}% match): {existing_title[:60]}")
            return True
            
    return False

def get_top_signals(limit: int = 20, min_score: int = 7) -> list:
    if not supabase:
        print("Failed to get top signals: Supabase client not initialized.")
        return []
    try:
        response = (supabase.table("signals")
            .select("*")
            .not_.is_("score_data", "null")
            .order("created", desc=True)
            .limit(limit * 3)
            .execute())
        # Filter by relevance_score in Python after fetching
        results = []
        for s in response.data:
            try:
                score = s.get("score_data", {}).get("relevance_score", 0)
                if int(score) >= min_score:
                    results.append(s)
            except:
                continue
        return results[:limit]
    except Exception as e:
        print(f"Error retrieving top signals: {e}")
        return []
