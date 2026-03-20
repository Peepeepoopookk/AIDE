import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

POCKETBASE_URL = os.getenv("POCKETBASE_URL")
POCKETBASE_ADMIN_EMAIL = os.getenv("POCKETBASE_ADMIN_EMAIL")
POCKETBASE_ADMIN_PASSWORD = os.getenv("POCKETBASE_ADMIN_PASSWORD")

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
