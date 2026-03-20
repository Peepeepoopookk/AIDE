import os
import requests
from dotenv import load_dotenv
from rapidfuzz import fuzz

# Load environment variables from .env file
load_dotenv()

POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_ADMIN_EMAIL = os.getenv("POCKETBASE_ADMIN_EMAIL")
POCKETBASE_ADMIN_PASSWORD = os.getenv("POCKETBASE_ADMIN_PASSWORD")

# In-memory cache of existing signal titles for fuzzy matching
# This is populated once per pipeline run to avoid repeated API calls
_title_cache = []

def load_title_cache():
    """
    Loads all existing signal titles from PocketBase into memory.
    Call this once at the start of each crawler run.
    This avoids making a separate API call for every single signal.
    """
    global _title_cache
    
    token = get_auth_token()
    if not token:
        print("Failed to load title cache: Authentication failed.")
        return
        
    url = f"{POCKETBASE_URL}/api/collections/signals/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "perPage": 500,
        "sort": "-created"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        
        # Extract just the title field
        _title_cache = [item.get("title", "") for item in items if item.get("title")]
        print(f"Title cache loaded: {len(_title_cache)} titles")
    except requests.exceptions.RequestException as e:
        print(f"Error loading title cache: {e}")

def get_auth_token():
    """
    Authenticates as an admin user using the admin email and password from env variables.
    Returns the auth token string if successful, or None on failure.
    """
    if not POCKETBASE_URL or not POCKETBASE_ADMIN_EMAIL or not POCKETBASE_ADMIN_PASSWORD:
        print("Error: PocketBase credentials are not fully set in environment variables.")
        return None

    auth_url = f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password"
    data = {
        "identity": POCKETBASE_ADMIN_EMAIL,
        "password": POCKETBASE_ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(auth_url, json=data)
        response.raise_for_status()
        return response.json().get("token")
    except requests.exceptions.RequestException as e:
        print(f"Error authenticating with PocketBase: {e}")
        return None

def save_signal(data: dict):
    """
    Saves a record to the 'signals' collection via PocketBase REST API.
    
    Args:
        data (dict): The dictionary containing the signal data to be saved.
        
    Returns:
        dict: The created record dictionary if successful.
        None: On failure.
    """
    token = get_auth_token()
    if not token:
        print("Failed to save signal: Authentication failed.")
        return None
        
    # Check fuzzy duplicate by title
    title = data.get("title", "")
    if title and check_fuzzy_duplicate(title):
        print(f"Fuzzy duplicate skipped: {title[:60]}")
        return None
        
    url = f"{POCKETBASE_URL}/api/collections/signals/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        created_record = response.json()
        print(f"Successfully saved signal record with ID: {created_record.get('id')}")
        return created_record
    except requests.exceptions.RequestException as e:
        print(f"Error saving signal record: {e}")
        if e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def check_duplicate(url_hash: str) -> bool:
    """
    Checks if a signal with the given url_hash already exists in the 'signals' collection.
    
    Args:
        url_hash (str): The url_hash to check for duplicates.
        
    Returns:
        bool: True if a duplicate exists, False if not.
    """
    token = get_auth_token()
    if not token:
        print("Failed to check duplicate: Authentication failed.")
        return False
        
    url = f"{POCKETBASE_URL}/api/collections/signals/records"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "filter": f"url_hash='{url_hash}'",
        # We only need to know if at least one exists, so setting perPage to 1
        "perPage": 1 
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("totalItems", 0) > 0
    except requests.exceptions.RequestException as e:
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

def get_top_signals(limit: int = 5):
    """
    Returns the top signals ordered by score_total descending.
    
    Args:
        limit (int): The maximum number of signals to return (default is 5).
        
    Returns:
        list: A list of signal record dictionaries.
    """
    token = get_auth_token()
    if not token:
        print("Failed to get top signals: Authentication failed.")
        return []
        
    url = f"{POCKETBASE_URL}/api/collections/signals/records"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "sort": "-score_total",
        "perPage": limit
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving top signals: {e}")
        return []
