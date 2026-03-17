import os
from flask import Flask, request
import requests
from google import genai

app = Flask(__name__)

# --- Configuration (Render Environment Variables မှ ဆွဲယူပါသည်) ---
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = "my_secret_bot_token"  # Facebook Webhook တွင် ဖြည့်ခဲ့သော token ဖြစ်ရပါမည်
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini Client ကို နောက်ဆုံးပေါ် Version ဖြင့် တည်ဆောက်ခြင်း
client = genai.Client(api_key=GEMINI_API_KEY)

# --- System Instruction (AI Persona & Knowledge Base) ---
# သင်ပေးထားသော Business Info များကို ဤနေရာတွင် စုစည်းထားပါသည်
AKARI_INSTRUCTION = """
သင်သည် မန္တလေးအခြေစိုက် 'Akari Life Wear' Online Store ၏ ဖော်ရွေပြီး တက်ကြွသော အမျိုးသမီး အရောင်းဝန်ထမ်းတစ်ဦးဖြစ်သည်။

စရိုက်လက္ခဏာ (Persona):
- ယဉ်ကျေးပျူငှာစွာ ပြောဆိုရမည်။ 
- Customer ကို 'မမ/ညီမ' ဟု ရင်းနှီးစွာ သုံးနှုန်းရမည်။ 
- ဝါကျတိုင်း၏ အဆုံးတွင် 'ရှင်/ရှင့်' ကို အမြဲထည့်သုံးပါ။

လုပ်ငန်းအချက်အလက်များ (Business Profile):
- Brand Name: Akari (အကာရီ)
- Location: မန္တလေးမြို့ (Online Store သီးသန့်ဖြစ်ပြီး ဆိုင်ခွဲမရှိပါ)
- Products: ညဝတ်အင်္ကျီ (Pajama)၊ စက်ပန်းထိုးထည်များ၊ ချိတ်ထဘီ၊ လုံချည်နှင့် ထဘီ၊ စပန့်ထည်များ။
- Wholesale: အနည်းဆုံး (၅) ထည်မှ စတင်၍ လက်ကားဈေး ရရှိနိုင်သည်။

မကြာခဏမေးလေ့ရှိသော မေးခွန်းများ (FAQs):
- ဆိုင်တည်နေရာ: မန္တလေးအခြေစိုက် Online Shop ဖြစ်၍ ဆိုင်ခွဲမရှိကြောင်း၊ Online မှ စိတ်ကြိုက်မှာယူနိုင်ကြောင်း ဖြေပါ။
- ပို့ဆောင်ရေး: Ninja Van ရှိသည့် မြို့တိုင်းကို အိမ်ရောက်ငွေချေ (COD) စနစ်ဖြင့် ပို့ပေးသည်။
- လဲလှယ်ခြင်း: ဆိုဒ်မတော်ပါက သို့မဟုတ် ပစ္စည်းမကြိုက်ပါက ၂၄ နာရီအတွင်း Delivery နှင့် ပြန်အပ်ပါက လဲပေးသည်။
- ငွေပြန်အမ်းခြင်း: ၂၄ နာရီအတွင်း အကြောင်းကြားပါက ငွေပြန်အမ်းပေးသည်။ (Deli ခကို Customer မှ ကျခံရမည်)
- မှာယူပုံ: မှာယူလိုပါက အထည်အမျိုးအစား၊ အရေအတွက်၊ အမည်၊ ဖုန်း၊ လိပ်စာ ပေးရန် တောင်းဆိုပါ။

အရောင်းပိတ်ခြင်း (Sales Closing):
- မေးခွန်းများကို ဖြေကြားပြီးတိုင်း Customer အမှာစာတင်လာစေရန် နောက်ထပ် မေးခွန်းတစ်ခု (Follow-up question) ကို အမြဲပြန်မေးပါ။ 
- ဥပမာ - "မမက ပုံစံလေးတွေ ကြည့်ချင်တာလားရှင့်?" သို့မဟုတ် "ဘယ်နှစ်ထည်လောက် ယူမလဲရှင့်?" စသဖြင့် အရောင်းပိတ်ရန် ကြိုးစားပါ။
"""

@app.route("/", methods=['GET'])
def verify():
    # Facebook Webhook Verification
    if request.args.get("hub.verify_token") == FB_VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403

@app.route("/", methods=['POST'])
def webhook():
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                # စာသား (Text) ပါသော message ကို စစ်ဆေးခြင်း
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    user_text = messaging_event.get("message").get("text")
                    
                    if user_text:
                        try:
                            # Gemini 2.0 Flash ဖြင့် အဖြေထုတ်လုပ်ခြင်း
                            response = client.models.generate_content(
                                model="gemini-2.0-flash",
                                config={
                                    "system_instruction": AKARI_INSTRUCTION
                                },
                                contents=user_text
                            )
                            reply_text = response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}")
                            reply_text = "တောင်းပန်ပါတယ်ရှင်။ စနစ်အနည်းငယ် ကြန့်ကြာနေလို့ ခဏနေမှ ပြန်မေးပေးပါနော် မမရှင့်။"

                        # Facebook သို့ အဖြေပြန်ပို့ခြင်း
                        send_message(sender_id, reply_text)
    return "ok", 200

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"FB Send Error: {e}")

if __name__ == "__main__":
    # Render ၏ port 10000 တွင် run ခြင်း
    app.run(host="0.0.0.0", port=10000)
