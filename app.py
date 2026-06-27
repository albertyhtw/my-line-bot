import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 改由環境變數讀取，保護金鑰不外洩
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    
    # 偵測是否包含 @all (不分大小寫)
    if "@all" in msg.lower():
       # 英文與 Tagalog 雙語警告訊息 (非緊急勿用)
        # 英文與 Tagalog 雙語版
reply_text = (
    "⚠️ System Notice: Please reserve the @all tag for major announcements and emergencies only. "
    "If everything is marked as @all, the significance of this alert will be lost.\n\n"
    "⚠️ Paunawa ng Sistema: Mangyaring gamitin lamang ang @all tag para sa mahahalagang anunsyo at emergency. "
    "Kapag ang lahat ng mensahe ay naka-@all, mawawalan na ito ng kahalagahan."
)
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

if __name__ == "__main__":
    app.run(port=5000)
