import os
import json
import gzip
import tempfile
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from db.supabase_client import supabase
from utils.logger import get_logger

load_dotenv()
logger = get_logger("cold_storage")

def run_cold_storage():
    folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if folder_id is None:
        logger.error("GDRIVE_FOLDER_ID not found in environment")
        return

    sa_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gdrive_service_account.json")
    if os.path.exists(sa_path):
        with open(sa_path, "r") as f:
            sa_info = json.load(f)
    else:
        sa_json = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
        if not sa_json:
            logger.error("No service account found: gdrive_service_account.json missing and GDRIVE_SERVICE_ACCOUNT_JSON not set")
            return
        sa_info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

    service = build("drive", "v3", credentials=creds)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()

    result = supabase.table("signals").select("*").lt("crawled_at", cutoff).execute()
    signals = result.data
    if len(signals) == 0:
        logger.info("No signals to archive")
        return

    logger.info(f"Archiving {len(signals)} signals older than 30 days")

    archive_name = f"aide_archive_{datetime.now(timezone.utc).strftime('%Y_%m')}.json.gz"

    with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as tmp:
        tmp_path = tmp.name
    with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, default=str)

    file_metadata = {"name": archive_name, "parents": [folder_id]}
    media = MediaFileUpload(tmp_path, mimetype="application/gzip")
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    logger.info(f"Uploaded {archive_name} to Google Drive (id={uploaded.get('id')})")

    os.unlink(tmp_path)

    ids = [s["id"] for s in signals]
    supabase.table("signals").delete().lt("crawled_at", cutoff).execute()
    logger.info(f"Deleted {len(ids)} signals from Supabase")

if __name__ == "__main__":
    run_cold_storage()
