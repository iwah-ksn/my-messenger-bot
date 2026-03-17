import os
import time
from flask import Flask, request
import requests
from google import genai

app = Flask(__name__)

# --- Configuration ---
# Render Environment Variables ထဲတွင် ဖြည့်သွင်းထားသော အချက်အလက်များ
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client ကို Gemini 1.5 Flash အတွက် သတ်မှတ်ခြင်း
client = genai.Client(api_key=GEMINI_API_KEY)

# Admin ဝင်ဖြေထားသော conversation များကို မှတ်ထားရန် ယာယီမှတ်ဉာဏ်
# { sender_id: timestamp_of_last_admin_message }
paused_conversations = {}

# အကာရီ ဧကရီ အတွက် အရောင်းဝန်ထမ်း Instruction
AKARI_INSTRUCTION = """
မင်းရဲ့အမည်က 'Akari - ဧကရီ' (Akari Life Wear) Online Store ရဲ့ အမျိုးသမီးအရောင်းဝန်ထမ်း ဖြစ်ပါတယ်။

လိုက်နာရမည့် စည်းကမ်းများ:
1. ဘာသာပြန်ဆရာ သို့မဟုတ် AI Assistant တစ်ယောက်လို မဖြေပါနှင့်။
2. Customer က 'နေကောင်းလား' လို့မေးရင် 'နေကောင်းပါတယ်ရှင်။ Akari - ဧကရီ ကူညီပေးပါရစေရှင်' လို့ပဲ တိုတိုရှင်းရှင်း ယဉ်ယဉ်ကျေးကျေး ဖြေပါ။
3. စကားလုံးတိုင်းကို 'မမ/ညီမ' လို့ သုံးနှုန်းပြီး ဝါကျတိုင်းမှာ 'ရှင်/ရှင့်' ကို မပျက်မကွက် ထည့်သုံးပါ။
4. Online Shop နှင့် မဆိုင်သော ဗဟုသုတများ၊ ဘာသာပြန်ချက်များကို လုံးဝ မဖြေရ။
5. ဆိုင်သည် မန္တလေးအခြေစိုက်ဖြစ်ပြီး Online Store သီးသန့်ဖြစ်သည်။ ညဝတ်အင်္ကျီ၊ စက်ပန်းထိုးထည်နှင့် ချိတ်ထဘီများ ရောင်းသည်။
6. အဖြေပေးပြီးတိုင်း 'ဘာလေးကြည့်ချင်လဲရှင်?' သို့မဟုတ် 'မှာယူလိုရင် အမည်၊ ဖုန်း၊ လိပ်စာ ပေးလို့ရပါတယ်ရှင်' ဆိုပြီး အရောင်းပိတ်ပါ။
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
                    
                    # Admin (ကိုယ်တိုင်) က Inbox ထဲကနေ စာပြန်နေခြင်း ရှိမရှိ စစ်ဆေးခြင်း
                    is_admin = sender_id == recipient_id or "is_echo" in message

                    if is_admin:
                        # Admin ဝင်ဖြေလျှင် AI ကို ခေတ္တရပ်ရန် မှတ်သားသည်
                        actual_customer_id = messaging_event.get("recipient", {}).get("id")
                        if actual_customer_id:
                            paused_conversations[actual_customer_id] = time.time()
                        continue

                    if user_text:
                        # AI ကို ပြန်ဖွင့်ရန် Keyword
                        if user_text.lower() == "ai resume":
                            if sender_id in paused_conversations:
                                del paused_conversations[sender_id]
                                send_message(sender_id, "AI စနစ် ပြန်လည်အသက်ဝင်သွားပါပြီရှင်။")
                                continue

                        # Admin ဝင်ဖြေထားလျှင် ၂၄ နာရီအတွင်း AI က ကျော်သွားမည်
                        last_admin_time = paused_conversations.get(sender_id)
                        if last_admin_time and (time.time() - last_admin_time < 86400):
                            continue

                        try:
                            # ပိုမိုတည်ငြိမ်သော Gemini 1.5 Flash ကို အသုံးပြုခြင်း
                            response = client.models.generate_content(
                                model="gemini-1.5-flash",
                                config={"system_instruction": AKARI_INSTRUCTION},
                                contents=user_text
                            )
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}")
                            # Error တက်ပါက သင်ခိုင်းထားသော အချိန်ဆွဲသည့်စာသား
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
    # Render ၏ Port Error ကို ဖြေရှင်းရန်
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
