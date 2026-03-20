import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.pocketbase_client import get_auth_token
import requests
import os
from dotenv import load_dotenv

load_dotenv()
POCKETBASE_URL = os.getenv("POCKETBASE_URL")

token = get_auth_token()
headers = {"Authorization": f"Bearer {token}"}

# Get total count
response = requests.get(f"{POCKETBASE_URL}/api/collections/signals/records", 
    headers=headers, params={"perPage": 1})
data = response.json()
total = data.get("totalItems", 0)
print(f"Total signals in database: {total}")
print()

# Count by source
for source in ["hacker_news", "arxiv", "github_trending"]:
    response = requests.get(f"{POCKETBASE_URL}/api/collections/signals/records",
        headers=headers, 
        params={"filter": f'source="{source}"', "perPage": 1})
    data = response.json()
    count = data.get("totalItems", 0)
    print(f"  {source}: {count} signals")
