import os
import sys
from dotenv import load_dotenv

def require_config(require_llm: bool = True):
    load_dotenv()
    errors = []

    if not os.environ.get("SUPABASE_URL"):
        errors.append("SUPABASE_URL is not set")
    if not os.environ.get("SUPABASE_KEY"):
        errors.append("SUPABASE_KEY is not set")

    if require_llm:
        llm_keys = ["CEREBRAS_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "OPENROUTER_API_KEY"]
        if not any(os.environ.get(k) for k in llm_keys):
            errors.append("At least one LLM API key must be set: " + ", ".join(llm_keys))

    if errors:
        print("AIDE Configuration Error — cannot start:")
        for e in errors:
            print(f"  x {e}")
        print("\nCheck your .env file or GitHub Secrets.")
        sys.exit(1)
