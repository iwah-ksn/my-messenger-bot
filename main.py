import os
import time
from flask import Flask, request
import requests
from google import genai

app = Flask(__name__)

# --- Configuration ---
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

paused_conversations = {}

AKARI_INSTRUCTION = """
မင်းရဲ့အမည်က 'Akari - ဧကရီ' (Akari Life Wear) Online Store ရဲ့ အမျိုးသမီးအရောင်းဝန်ထမ်း ဖြစ်ပါတယ်။
1. Customer က 'နေကောင်းလား' လို့မေးရင် 'နေကောင်းပါတယ်ရှင်။ Akari - ဧကရီ ကူညီပေးပါရစေရှင်' လို့ပဲ ဖြေပါ။
2. စကားလုံးတိုင်းမှာ 'ရှင်/ရှင့်' ကို မပျက်မကွက် ထည့်သုံးပါ။
3. ညဝတ်အင်္ကျီ၊ စက်ပန်းထိုးထည်နှင့် ချိတ်ထဘီများ ရောင်းသည်။
"""

@app.route("/", methods=['GET'])
def verify():
    if request.args.get("hub.verify_token") == FB_VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403

@app.route("/", methods=['POST'])
def webhook():
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                recipient_id = messaging_event["recipient"]["id"]
                
                if messaging_event.get("message"):
                    message = messaging_event["message"]
                    user_text = message.get("text")
                    
                    is_admin = sender_id == recipient_id or "is_echo" in message
                    if is_admin:
                        actual_customer_id = messaging_event.get("recipient", {}).get("id")
                        if actual_customer_id:
                            paused_conversations[actual_customer_id] = time.time()
                        continue

                    if user_text:
                        last_admin_time = paused_conversations.get(sender_id)
                        if last_admin_time and (time.time() - last_admin_time < 86400):
                            continue

                        try:
                            # ဤနေရာတွင် Model နာမည်ကို အမှားအယွင်းမရှိစေရန် ပြင်ဆင်ထားသည်
                            response = client.models.generate_content(
                                model="gemini-1.5-flash", 
                                config={"system_instruction": AKARI_INSTRUCTION},
                                contents=user_text
                            )
                            reply_text = response.text
                        except Exception as e:
                            # Error တက်ပါက Log တွင် ပြပေးမည်
                            print(f"Gemini API Error: {e}")
                            reply_text = "တောင်းပန်ပါတယ်ရှင်။ ခဏလေး စောင့်ပေးပါဦးနော် မမရှင့်။"

                        send_message(sender_id, reply_text)
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"FB Send Error: {e}")

# Render Port Binding အတွက် အရေးကြီးသောအပိုင်း
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
