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

client = genai.Client(api_key=GEMINI_API_KEY)

# Admin ဝင်ဖြေထားသော conversation များကို မှတ်ထားရန် (Temporary Memory)
# { sender_id: timestamp_of_last_admin_message }
paused_conversations = {}

AKARI_INSTRUCTION = """
သင်သည် မန္တလေးအခြေစိုက် 'Akari - ဧကရီ' (Akari Life Wear) Online Store ၏ ဖော်ရွေပြီး တက်ကြွသော အမျိုးသမီး အရောင်းဝန်ထမ်းတစ်ဦးဖြစ်သည်။
- Customer ကို 'မမ/ညီမ' ဟု သုံးနှုန်းပြီး ဝါကျတိုင်း၏ အဆုံးတွင် 'ရှင်/ရှင့်' ကို ထည့်သုံးပါ။
- Brand: Akari - ဧကရီ (အကာရီ - ဧကရီ)
- Products: ညဝတ်အင်္ကျီ (Pajama)၊ စက်ပန်းထိုးထည်များ၊ ချိတ်ထဘီ၊ လုံချည်နှင့် ထဘီ၊ စပန့်ထည်များ။
- Wholesale: ၅ ထည်မှ စတင်၍ လက်ကားဈေး ရရှိနိုင်သည်။
- Delivery: Ninja Van (COD ရသည်)။
- FAQ: ဆိုင်ခွဲမရှိပါ (Online Shop သာဖြစ်သည်)။ ၂၄ နာရီအတွင်း ပစ္စည်းလဲလှယ်/ငွေပြန်အမ်းနိုင်သည်။
- Sales Closing: မေးခွန်းဖြေပြီးတိုင်း အရောင်းပိတ်ရန် ထပ်မေးပါ။
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
                    
                    # ၁။ Admin က စာပို့တာလား (သို့မဟုတ်) Customer က စာပို့တာလား စစ်ဆေးခြင်း
                    # Facebook တွင် sender_id က Page ID ဖြစ်နေလျှင် ၎င်းမှာ Admin ဖြစ်သည်
                    is_admin = sender_id == recipient_id or "is_echo" in message

                    if is_admin:
                        # Admin က စာပို့လိုက်ပြီဆိုလျှင် AI ကို ခေတ္တရပ်ရန် မှတ်သားလိုက်သည်
                        actual_customer_id = messaging_event.get("recipient", {}).get("id")
                        if actual_customer_id:
                            paused_conversations[actual_customer_id] = time.time()
                            print(f"AI paused for customer: {actual_customer_id}")
                        continue

                    # ၂။ Customer ဆီမှ စာသားရောက်လာလျှင်
                    if user_text:
                        # AI ကို ပြန်ဖွင့်ခိုင်းသော Keyword ပါသလား စစ်ဆေးခြင်း
                        if user_text.lower() == "ai resume":
                            if sender_id in paused_conversations:
                                del paused_conversations[sender_id]
                                send_message(sender_id, "AI စနစ် ပြန်လည်အသက်ဝင်သွားပါပြီရှင်။")
                                continue

                        # Admin ဝင်ဖြေနေဆဲလား စစ်ဆေးခြင်း (၂၄ နာရီအတွင်း)
                        last_admin_time = paused_conversations.get(sender_id)
                        if last_admin_time and (time.time() - last_admin_time < 86400):
                            print(f"AI is skipping for customer {sender_id} because Admin is active.")
                            continue

                        try:
                            # Gemini 2.0 Flash ဖြင့် အဖြေတောင်းခြင်း
                            response = client.models.generate_content(
                                model="gemini-2.0-flash",
                                config={"system_instruction": AKARI_INSTRUCTION},
                                contents=user_text
                            )
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}")
                            # သင်ခိုင်းထားသော အင်တာနက် အခက်အခဲ ဖြေကြားချက်
                            reply_text = "အင်တာနက် အခက်အခဲလေးကြောင့် ခဏလေး စောင့်ပေးပါဦးနော် မမရှင့်။ အရောင်းဝန်ထမ်းမှ မကြာမီ ပြန်လည်ဖြေကြားပေးပါ့မယ်ရှင်။"

                        send_message(sender_id, reply_text)
                        
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"FB Send Error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
