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

# Gemini Setup - API Version ကို တိုက်ရိုက်သတ်မှတ်သည်
genai.configure(api_key=GEMINI_API_KEY)

# Error 404 ကို ကျော်လွှားရန် model name ကို တိကျစွာ ရေးသားခြင်း
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="သင်သည် Akari - ဧကရီ အဝတ်အထည်ဆိုင်၏ ယဉ်ကျေးပျူငှာသော အရောင်းဝန်ထမ်းဖြစ်ပါသည်။ ရှင်/ရှင့် သုံးနှုန်းပြီး ဖြေပေးပါ။"
)

paused_conversations = {}

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
                            # ဤနေရာတွင် Generation လုပ်ဆောင်ပုံ ပြောင်းထားသည်
                            response = model.generate_content(user_text)
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini API Error: {e}")
                            # Error ဆက်တက်နေပါက Log ထဲတွင် အသေးစိတ်ကြည့်နိုင်ရန် print ထုတ်ထားသည်
                            reply_text = "တောင်းပန်ပါတယ်ရှင်။ စနစ်အနည်းငယ် ကြန့်ကြာနေလို့ ခဏလေး စောင့်ပေးပါဦးနော်။"

                        send_message(sender_id, reply_text)
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
