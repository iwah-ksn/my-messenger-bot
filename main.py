import os
import time
from flask import Flask, request
import requests
import google.generativeai as genai

app = Flask(__name__)

# --- Configuration ---
# Render Environment Variables ထဲမှာ ဒီ Key တွေကို သေချာထည့်ပေးထားပါရှင်
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token" # Facebook Webhook မှာ ရိုက်ထည့်ရမည့် Token
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)

# --- AI Model သတ်မှတ်ခြင်း (Gemini 3 Flash Preview ကို သုံးထားပါတယ်) ---
model = genai.GenerativeModel(
    model_name="models/gemini-3-flash-preview", 
    system_instruction="""
မင်းရဲ့အမည်က 'Akari - ဧကရီ' (Akari Life Wear) Online Store ရဲ့ အမျိုးသမီးအရောင်းဝန်ထမ်း ဖြစ်ပါတယ်။
1. စကားလုံးတိုင်းမှာ 'ရှင်/ရှင့်' ကို မပျက်မကွက် ထည့်သုံးပါ။
2. ညဝတ်အင်္ကျီ၊ စက်ပန်းထိုးထည်နှင့် ချိတ်ထဘီများ ရောင်းသည်။ ယဉ်ကျေးပျူငှာစွာ ဖြေကြားပေးပါ။
3. မန္တလေးအခြေစိုက် Online Shop ဖြစ်သည်။
4. ဝယ်ယူသူကို 'မမ/ညီမလေး' ဟု ရင်းနှီးစွာ ခေါ်ဝေါ်ပြီး ဝယ်ယူသူ စိတ်ချမ်းသာအောင် ပြောဆိုပါ။
"""
)

# Admin ဝင်ဖြေထားလျှင် AI ခေတ္တရပ်ရန် Memory
paused_conversations = {}

# --- 1. Webhook Verification (Facebook နှင့် ချိတ်ဆက်သည့်အပိုင်း) ---
@app.route("/", methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == FB_VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED: Gemini 3 is now active!")
        return challenge, 200
    
    return "Verification failed", 403

# --- 2. Message Handling (စာများ လက်ခံပြီး AI နှင့် ပြန်ဖြေသည့်အပိုင်း) ---
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
                    
                    # Admin ဝင်ဖြေနေခြင်း (is_echo) ရှိမရှိ စစ်ဆေးခြင်း
                    if "is_echo" in message:
                        # Admin ဝင်ဖြေလျှင် AI ကို ခေတ္တရပ်ထားမည် (ဥပမာ- ၂၄ နာရီ)
                        paused_conversations[recipient_id] = time.time()
                        continue

                    user_text = message.get("text")
                    if user_text:
                        # Admin ဝင်ဖြေထားလျှင် AI ကျော်သွားရန်
                        last_admin_time = paused_conversations.get(sender_id)
                        if last_admin_time and (time.time() - last_admin_time < 86400):
                            print(f"Skipping AI: Admin is handling {sender_id}")
                            continue

                        try:
                            # Gemini 3 AI ထံမှ အဖြေတောင်းခြင်း
                            response = model.generate_content(user_text)
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini 3 API Error: {e}")
                            reply_text = "တောင်းပန်ပါတယ်ရှင်။ စနစ်အနည်းငယ် ကြန့်ကြာနေလို့ ခဏလေး စောင့်ပေးပါဦးနော် မမရှင့်။"

                        # Facebook သို့ အဖြေပြန်ပို့ခြင်း
                        send_message(sender_id, reply_text)

    return "ok", 200

# --- 3. Messenger သို့ စာပြန်ပို့သည့် Function ---
def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print(f"FB Send Error Detail: {r.text}")
    except Exception as e:
        print(f"FB Request Error: {e}")

# --- Render Port Binding ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
