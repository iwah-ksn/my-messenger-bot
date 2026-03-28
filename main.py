import os
import time
from flask import Flask, request
import requests
import google.generativeai as genai

app = Flask(__name__)

# --- Configuration ---
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)

# --- AI Model (Memory သက်သာစေရန် Lite version ကို ပြောင်းသုံးထားပါတယ်) ---
model = genai.GenerativeModel(
    model_name="models/gemini-2.5-flash-lite", # Flash Lite က Memory အစားနည်းပါတယ်
    system_instruction="""
မင်းရဲ့အမည်က 'Akari - ဧကရီ' (Akari Life Wear) Online Shop ဝန်ထမ်း ဖြစ်ပါတယ်။
1. စကားလုံးတိုင်းမှာ 'ရှင်/ရှင့်' ကို ထည့်သုံးပါ။
2. ညဝတ်အင်္ကျီ၊ စက်ပန်းထိုးထည်နှင့် ချိတ်ထဘီများ ရောင်းသည်။
3. ဝယ်ယူသူကို 'မမ/ညီမလေး' ဟု ရင်းနှီးစွာ ခေါ်ဝေါ်ပါ။
"""
)

paused_conversations = {}

@app.route("/", methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == FB_VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.route("/", methods=['POST'])
def webhook():
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if "is_echo" in messaging_event.get("message", {}):
                    paused_conversations[messaging_event["recipient"]["id"]] = time.time()
                    continue

                user_text = messaging_event.get("message", {}).get("text")
                if user_text:
                    last_admin_time = paused_conversations.get(sender_id)
                    if last_admin_time and (time.time() - last_admin_time < 86400):
                        continue

                    try:
                        # AI Response
                        response = model.generate_content(user_text)
                        reply_text = response.text
                        send_message(sender_id, reply_text)
                    except Exception as e:
                        print(f"Error: {e}")
                        
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
