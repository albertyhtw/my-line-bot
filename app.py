import os
import json
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

DB_FILE = 'groups.json'

def load_groups():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_groups(groups):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False, indent=4)

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
    msg = event.message.text.strip()
    user_id = event.source.user_id
    
    # Automatically get the current group/room ID to prevent cross-group confusion
    group_id = getattr(event.source, 'group_id', None) or getattr(event.source, 'room_id', None) or user_id
    
    # === FEATURE 1: Anti-@all Warning (English & Tagalog) ===
    if "@all" in msg.lower():
        reply_text = (
            "⚠️ System Notice: Please reserve the @all tag for major announcements and emergencies only. "
            "If everything is marked as @all, the significance of this alert will be lost.\n\n"
            "⚠️ Paunawa ng Sistema: Mangyaring gamitin lamang ang @all tag para sa mahahalagang anunsyo at emergency. "
            "Kapag ang lahat ng mensahe ay naka-@all, mawawalan na ito ng kahalagahan."
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # === FEATURE 2: Custom #Tag System (English & Tagalog) ===
    if msg.startswith("#"):
        all_data = load_groups()
        
        if group_id not in all_data:
            all_data[group_id] = {}
        groups = all_data[group_id]
        
        parts = msg.split(maxsplit=1)
        command_part = parts[0].lower()
        
        # 指令: #list (查詢可用標籤)
        if command_part == "#list":
            if not groups:
                reply = (
                    "📁 No custom tags available in this group.\n"
                    "📁 Walang magagamit na tag sa grupong ito."
                )
            else:
                reply = (
                    "📁 Available tags in this group:\n"
                    "📁 Mga magagamit na tag sa grupong ito:\n\n" + "\n".join([f"#{g}" for g in groups.keys()])
                )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return
            
        # 指令: #create xx 或 #delete xx (建立/刪除標籤)
        if command_part in ["#create", "#delete"]:
            if len(parts) < 2:
                reply = (
                    "❌ Please provide a tag name. Example: #create NS\n"
                    "❌ Mangyaring magbigay ng pangalan ng tag. Halimbawa: #create NS"
                )
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return
            group_name = parts[1].strip()
            
            if command_part == "#create":
                if group_name in groups:
                    reply = (
                        f"⚠️ Tag #{group_name} already exists in this group.\n"
                        f"⚠️ Ang tag na #{group_name} ay umiiral na sa grupong ito."
                    )
                else:
                    groups[group_name] = []
                    all_data[group_id] = groups
                    save_groups(all_data)
                    reply = (
                        f"✅ Tag #{group_name} created successfully!\n"
                        f"✅ Matagumpay na nailikha ang tag na #{group_name}!"
                    )
            else:
                if group_name in groups:
                    del groups[group_name]
                    all_data[group_id] = groups
                    save_groups(all_data)
                    reply = (
                        f"🗑️ Tag #{group_name} deleted successfully.\n"
                        f"🗑️ Matagumpay na nabura ang tag na #{group_name}."
                    )
                else:
                    reply = (
                        f"❌ Tag #{group_name} not found.\n"
                        f"❌ Hindi mahanap ang tag na #{group_name}."
                    )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        # 指令: #join xx 或 #leave xx (加入/離開標籤成員)
        if command_part in ["#join", "#leave"]:
            if len(parts) < 2:
                reply = (
                    "❌ Please specify a tag. Example: #join NS\n"
                    "❌ Mangyaring tukuyin ang tag. Halimbawa: #join NS"
                )
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return
            group_name = parts[1].strip()
            if group_name not in groups:
                reply = (
                    f"❌ Tag #{group_name} not found. Please create it first.\n"
                    f"❌ Hindi mahanap ang tag na #{group_name}. Mangyaring likhain muna ito."
                )
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return
                
            if command_part == "#join":
                if user_id not in groups[group_name]:
                    groups[group_name].append(user_id)
                    all_data[group_id] = groups
                    save_groups(all_data)
                    reply = (
                        f"👍 You have successfully joined #{group_name}!\n"
                        f"👍 Matagumpay kang sumali sa #{group_name}!"
                    )
                else:
                    reply = (
                        f"⚠️ You are already a member of #{group_name}.\n"
                        f"⚠️ Miyembro ka na ng #{group_name}."
                    )
            else:
                if user_id in groups[group_name]:
                    groups[group_name].remove(user_id)
                    all_data[group_id] = groups
                    save_groups(all_data)
                    reply = (
                        f"🚪 You have left #{group_name}.\n"
                        f"🚪 Umalis ka na sa #{group_name}."
                    )
                else:
                    reply = (
                        f"⚠️ You are not a member of #{group_name}.\n"
                        f"⚠️ Hindi ka miyembro ng #{group_name}."
                    )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        # 觸發標註特定人士: #xx [訊息內容]
        target_group = command_part[1:] 
        if target_group in groups:
            member_ids = groups[target_group]
            if not member_ids:
                reply = (
                    f"⚠️ No members in #{target_group} yet. Use #join {target_group} to join.\n"
                    f"⚠️ Walang miyembro sa #{target_group}. Gamitin ang #join {target_group} para sumali."
                )
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return
                
            custom_msg = parts[1].strip() if len(parts) == 2 else ""
            
            mentionee_list = []
            text_prefix = "🔔 "
            
            for i, m_id in enumerate(member_ids):
                text_prefix += f"@{i} "
                mentionee_list.append({"index": text_prefix.index(f"@{i}"), "length": 4, "userId": m_id})
                
            final_text = (
                f"{text_prefix}\n"
                f"📢 Notification for #{target_group} / Abiso para sa #{target_group}:\n"
                f"{custom_msg}"
            )
            
            payload = {
                "type": "text",
                "text": final_text,
                "mention": {
                    "mentionees": mentionee_list
                }
            }
            line_bot_api.reply_message(event.reply_token, TextSendMessage.new_from_json_dict(payload))
            return

if __name__ == "__main__":
    app.run()
