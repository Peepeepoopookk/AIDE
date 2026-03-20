"""
AIDE PocketBase Schema Migration
Adds scoring fields to the signals collection.

Run once: python setup_pb_schema.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

PB_URL   = os.environ.get("POCKETBASE_URL", "http://127.0.0.1:8090")
EMAIL    = os.environ.get("POCKETBASE_ADMIN_EMAIL", "admin@aide.local")
PASSWORD = os.environ.get("POCKETBASE_ADMIN_PASSWORD", "changeme123")

def get_token():
    r = requests.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": EMAIL, "password": PASSWORD},
    )
    r.raise_for_status()
    data = r.json()
    return data.get("token") or data.get("superuser", {}).get("token") or data["record"]["token"]

def get_collection_id(token, name="signals"):
    r = requests.get(
        f"{PB_URL}/api/collections/{name}",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()["id"]

def patch_collection(token, coll_id, extra_fields):
    r = requests.get(
        f"{PB_URL}/api/collections/{coll_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    current = r.json()
    existing_names = {f["name"] for f in current.get("fields", [])}
    new_fields = [f for f in extra_fields if f["name"] not in existing_names]

    if not new_fields:
        print("All fields already exist. Nothing to do.")
        return

    current["fields"].extend(new_fields)
    r2 = requests.patch(
        f"{PB_URL}/api/collections/{coll_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=current,
    )
    r2.raise_for_status()
    print(f"Added {len(new_fields)} fields: {[f['name'] for f in new_fields]}")

SCORING_FIELDS = [
    {"name": "scored",          "type": "bool",   "required": False},
    {"name": "skip_reason",     "type": "text",   "required": False},
    {"name": "classification",  "type": "json",   "required": False},
    {"name": "score_data",      "type": "json",   "required": False},
    {"name": "summary_data",    "type": "json",   "required": False},
    {"name": "analysis_data",   "type": "json",   "required": False},
]

if __name__ == "__main__":
    token   = get_token()
    coll_id = get_collection_id(token)
    patch_collection(token, coll_id, SCORING_FIELDS)
    print("Schema migration complete.")
