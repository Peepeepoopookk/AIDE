import os
from dotenv import load_dotenv
load_dotenv()

class AIDEConfig:
    # Database
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

    # LLM Keys
    CEREBRAS_API_KEY   = os.environ.get("CEREBRAS_API_KEY", "")
    GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
    MISTRAL_API_KEY    = os.environ.get("MISTRAL_API_KEY", "")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

    # Pipeline settings
    CRAWLER_BATCH_DELAY = float(os.environ.get("CRAWLER_BATCH_DELAY", "0.5"))
    SCORE_BATCH_SIZE    = int(os.environ.get("SCORE_BATCH_SIZE", "50"))
