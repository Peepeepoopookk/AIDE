import os
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def send_telegram_message(text: str, token: str, chat_id: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Handle message too long error by splitting into chunks of 4000 chars
    for i in range(0, len(text), 4000):
        chunk = text[i:i+4000]
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Warning: Failed to send chunk to Telegram: {e}")

def format_signal(s: dict) -> str:
    title = s.get('title', 'Unknown Title')
    category = s.get('category', 'research')
    score = s.get('score_weighted', 0.0)
    
    summary = "No summary available."
    sd = s.get('summary_data')
    if isinstance(sd, dict) and 'summary' in sd:
        summary = sd['summary']
    elif isinstance(sd, str):
        try:
            sd_dict = json.loads(sd)
            if 'summary' in sd_dict:
                summary = sd_dict['summary']
        except json.JSONDecodeError:
            pass
            
    url = s.get('url', '')
    
    # Using the exact format specified
    return f"🔹 *{title}*\n📌 Category: {category} | Score: {score}\n📝 {summary}\n🔗 {url}\n"

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
        return

    try:
        command = os.environ.get("COMMAND")
        
        url_supabase = os.environ.get("SUPABASE_URL")
        key_supabase = os.environ.get("SUPABASE_KEY")
        if not url_supabase or not key_supabase:
            raise ValueError("Missing Supabase credentials in environment variables (SUPABASE_URL or SUPABASE_KEY).")
        
        supabase: Client = create_client(url_supabase, key_supabase)
        twenty_four_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        if command == "top":
            # Command 1: top
            response = supabase.table('signals').select('*')\
                .eq('scored', True)\
                .gte('crawled_at', twenty_four_hours_ago)\
                .not_.is_('score_weighted', 'null')\
                .order('score_weighted', desc=True)\
                .limit(10).execute()
            
            data = response.data
            
            if not data:
                send_telegram_message("No scored signals in the last 24 hours yet.", token, chat_id)
            else:
                messages = []
                for s in data:
                    messages.append(format_signal(s))
                send_telegram_message("\n".join(messages), token, chat_id)

        elif command == "summary":
            # Command 2: summary
            response = supabase.table('signals').select('*')\
                .eq('scored', True)\
                .gte('crawled_at', twenty_four_hours_ago)\
                .not_.is_('score_weighted', 'null')\
                .order('score_weighted', desc=True)\
                .limit(15).execute()
            
            data = response.data
            
            if not data:
                send_telegram_message("No scored signals in the last 24 hours to summarize.", token, chat_id)
                return

            groq_key = os.environ.get("GROQ_API_KEY")
            if not groq_key:
                raise ValueError("Missing GROQ_API_KEY for summary LLM call.")

            content_lines = []
            for s in data:
                title = s.get('title', 'Unknown')
                summary = "No summary available"
                sd = s.get('summary_data')
                if isinstance(sd, dict) and 'summary' in sd:
                    summary = sd['summary']
                elif isinstance(sd, str):
                    try:
                        sd_dict = json.loads(sd)
                        if 'summary' in sd_dict:
                            summary = sd_dict['summary']
                    except json.JSONDecodeError:
                        pass
                content_lines.append(f"- {title}: {summary}")
            
            user_content = "\n".join(content_lines)

            url_groq = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are AIDE, an AI intelligence analyst. Write a concise 3-4 sentence briefing on what is trending in AI and technology today based on the signals provided. Write in a professional newsletter tone."
                    },
                    {
                        "role": "user", 
                        "content": user_content
                    }
                ]
            }
            
            resp = requests.post(url_groq, headers=headers, json=payload)
            resp.raise_for_status()
            
            generated_summary = resp.json()['choices'][0]['message']['content']
            send_telegram_message(generated_summary, token, chat_id)

        elif command == "search":
            # Command 3: search
            query = os.environ.get("SEARCH_QUERY", "")
            if not query:
                send_telegram_message("No search query provided. Set SEARCH_QUERY env variable.", token, chat_id)
                return
            
            # ILIKE equivalent with PostgREST: ilike
            # Filtering for either title ILIKE %query% or description ILIKE %query%
            response = supabase.table('signals').select('*')\
                .eq('scored', True)\
                .or_(f"title.ilike.%{query}%,description.ilike.%{query}%")\
                .order('score_weighted', desc=True)\
                .limit(5).execute()
            
            data = response.data
            
            if not data:
                send_telegram_message(f"No signals found for: {query}", token, chat_id)
            else:
                messages = []
                for s in data:
                    messages.append(format_signal(s))
                send_telegram_message("\n".join(messages), token, chat_id)
                
        else:
            print("Unknown command")
            
    except Exception as e:
        error_msg = f"Bot Error: {str(e)}"
        print(error_msg)
        if token and chat_id:
            try:
                # Fallback to pure requests without using the wrapper if we want to be safe, 
                # but our wrapper handles chunking and won't throw up completely.
                send_telegram_message(error_msg, token, chat_id)
            except Exception as nested_e:
                print(f"Could not send error message to Telegram: {nested_e}")

if __name__ == "__main__":
    main()
