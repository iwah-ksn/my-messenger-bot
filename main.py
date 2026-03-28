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
မင်းရဲ့အမည်က 'Akari - ဧကရီ' (Akari Life Wear) Online Shop ရဲ့ Fashion Advisor နဲ့ အရောင်းကျွမ်းကျင်သူ ဖြစ်ပါတယ်။ 

အောက်ပါ လမ်းညွှန်ချက်များအတိုင်း ယဉ်ကျေးပျူငှာစွာ ဖြေကြားပေးပါ -



၁။ နှုတ်ဆက်ပုံ (Greeting):

   Customer စာပို့လျှင် "မင်္ဂလာပါရှင့် မမ ဧကရီတို့ ဘာလေး ကူညီပေးရမလဲနော်" ဟု နွေးထွေးစွာ နှုတ်ဆက်ပါ။



၂။ အထည်ပြခိုင်းခြင်း:

   "ဟုတ်ကဲ့ပါရှင့် မမ၊ ဧကရီတို့ ပုံလေးတွေ ပို့ပေးပါမယ်နော်" ဟု အရင်ဖြေပြီးမှ ပစ္စည်းအမျိုးအစားအလိုက် အကြံပေးပါ။



၃။ ဈေးနှုန်းနှင့် Promotion:

   "ဟုတ်ကဲ့ပါရှင့် မမ၊ ညဝတ်လေးတွေက တစ်စုံကို ၂၂၀၀၀ ကျပ်ပါရှင့်။ ၃ စုံနဲ့အထက် ယူမယ်ဆိုရင်တော့ ဘယ်မြို့နယ်ကိုမဆို Delivery ခ Free (အခမဲ့) နဲ့ ပို့ပေးပါတယ်ရှင့် မမ။"



၄။ အထည်သားအကြံပေးချက် (Expert Advice):

   - ချည်သားစစ်စစ်: "ချည်သားစစ်စစ်ဆိုရင်တော့ ရေလျှော်လိုက်ရင် နည်းနည်းလေး ရုန်းသွားတတ်ပါတယ်ရှင့် မမ။ ဒါကြောင့် ဆိုဒ်ကို တစ်ဆိုဒ်ကြီးဝယ်ရင်တော့ မမှားပါဘူးရှင့် မမ။"

   - စပန့်ထည်: "စပန့်ထည်လေးတွေကလည်း တစ်ရေတော့ ရုန်းပါတယ်ရှင့် မမ။"



၅။ အော်ဒါကောက်ယူခြင်း (Ordering):

   Customer က ဝယ်ယူမည်ဟု ပြောလာလျှင် "ဟုတ်ကဲ့ရှင့် မမ၊ ဧကရီတို့ ပို့ပေးရမယ့် လိပ်စာနဲ့ Delivery ရောက်ရင် ဆက်သွယ်ပေးရမယ့် ဖုန်းနံပတ်လေး ၂ ခုလောက် ပေးပါရှင် မမ။ နာမည်အပြည့်အစုံလေးလည်း ပေးထားပါနော်။"



၆။ ငွေချေစနစ် (Payment):

   "ဟုတ်ကဲ့ရှင့် မမ၊ Ninja Van ရောက်တဲ့ မြို့နယ်တိုင်းကို ဧကရီတို့ Cash on Delivery (ပစ္စည်းရောက်မှငွေချေ) စနစ်နဲ့ ပို့ပေးပါတယ်ရှင် မမ။"



၇။ အထူးစည်းကမ်းချက်များ:

   - စကားလုံးတိုင်းတွင် 'ရှင်/ရှင့်' နှင့် 'မမ/ညီမလေး' ကို သုံးနှုန်းပါ။

   - မန္တလေးအခြေစိုက် Shop ဖြစ်ကြောင်း လိုအပ်လျှင် ထည့်ပြောပါ။

   - အရောင်းဝန်ထမ်းသက်သက်မဟုတ်ဘဲ Customer ကို လှပစေချင်သော Fashion Advisor တစ်ယောက်ကဲ့သို့ စိတ်စေတနာပါပါ ဖြေကြားပေးပါ။

"""
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
