from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import requests
import math, json, time, random, os
from geopy.distance import geodesic

#======這裡是呼叫的檔案內容=====
from Restaurant import *
from Weather import *
#======這裡是呼叫的檔案內容=====


# app = Flask(__name__)
# static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# # Channel Access Token
# line_bot_api = LineBotApi('Bo1/FCGom0mnMcLP4YvxYAJNZ4aED58ETfCT9/lkRzD+QaKbc8tdWez14/ipM6QSlVhXxNdXc4bWeJ33PqHbAjt7eP2+WWGCTqI/TKbrgOlxeojGTKL2efkTF5MgBlhfMrCvhKY5Q1zpa2nNza9wIQdB04t89/1O/w1cDnyilFU=')
# # Channel Secret
# handler = WebhookHandler('f4f6aa5a119f79a1ab9f99ed73a5c007')
app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

#===========定義變數========================
user_filter_sequence = {} # 儲存用戶篩選標準的順序
user_detailed_filter = {} # 儲存用戶的詳細篩選標準
filter_options = ["價格", "距離", "評論數", "星數"] # 定義可供選擇的篩選標準
price_criteria = None
# 用一個字典暫時儲存用戶的經緯度，key 是用戶ID，value 是經緯度的字典 ex:{'lat': 25.0330, 'lng': 121.5654}
locations = {}
user_keywords = {}  # 儲存用戶的關鍵字
waiting_for_keyword = set()  # 用來儲存等待使用者輸入關鍵字的用戶 ID
user_food_choice = {}  # 用戶選擇的食物類別

#===========定義變數========================
# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global price_criteria

    msg = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    if msg in ["選擇障礙救星", "返回食物類別設定"]:
        send_quick_reply(reply_token, "請選擇您想吃的食物類別：", ["正餐", "小吃", "飲料", "點心"])
    elif msg in ["正餐", "小吃", "飲料", "點心"]:
        user_food_choice[user_id] = msg
        food = choose_food(msg)
        user_keywords[user_id] = food
        send_quick_reply(reply_token, f"建議您嘗試：{food}", ["返回食物類別設定", "不接受", "接受"])
    elif (msg == "接受") and (user_id in user_food_choice):
        del user_food_choice[user_id]
        user_filter_sequence[user_id] = [] # 初始化篩選標準順序
        user_detailed_filter[user_id] = {"sequence": [], "step": 0, "criteria": {}} # 初始化詳細篩選標準
        send_quick_reply(reply_token, "關鍵字確認完成，請選擇第一個篩選標準：", filter_options) # 發送篩選標準的選項

    elif (msg == "不接受") and (user_id in user_food_choice):
        food = choose_food(user_food_choice[user_id])
        user_keywords[user_id] = food
        send_quick_reply(reply_token, f"再試一次，建議您嘗試：{food}", ["返回食物類別設定", "不接受", "接受"])

    elif msg == "已決定要吃什麼":
        waiting_for_keyword.add(user_id)
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請輸入關鍵字："))
    elif user_id in waiting_for_keyword:
        keyword = msg.strip()
        user_keywords[user_id] = keyword
        waiting_for_keyword.remove(user_id)
        user_filter_sequence[user_id] = [] # 初始化篩選標準順序
        user_detailed_filter[user_id] = {"sequence": [], "step": 0, "criteria": {}} # 初始化詳細篩選標準
        send_quick_reply(reply_token, "關鍵字確認完成，請選擇第一個篩選標準：", filter_options) # 發送篩選標準的選項

    elif msg == "關鍵字確認完成，開始篩選！": # 如果用戶訊息為 "關鍵字確認完成，開始篩選！"
        user_filter_sequence[user_id] = [] # 初始化篩選標準順序
        user_detailed_filter[user_id] = {"sequence": [], "step": 0, "criteria": {}} # 初始化詳細篩選標準
        send_quick_reply(reply_token, "請選擇第一個篩選標準：", filter_options) # 發送篩選標準的選項
    elif (msg in filter_options) and (user_id in user_filter_sequence): # 如果用戶輸出的訊息在篩選標準中，且ID存在於字典中
        user_filter_sequence[user_id].append(msg) # 添加用戶選擇的篩選標準
        user_detailed_filter[user_id]["sequence"].append(msg)  # 同步詳細篩選標準
        remaining_options = [x for x in filter_options if x not in user_filter_sequence[user_id]] # 更新剩餘可供篩選標準的選擇
        if msg == "價格":
            send_quick_reply(reply_token, "請選擇價格範圍：", ["$", "$$", "$$$", "$$$$"])
        elif remaining_options: # 如還有剩餘篩選選項，詢問是否繼續篩選
            send_quick_reply(reply_token, f"您已選擇：{', '.join(user_filter_sequence[user_id])}\n是否需要選擇下一個篩選標準？", remaining_options + ["結束篩選"]) # 添加結束篩選的選項
        else: # 如果沒有剩餘篩選的標準，輸出篩選結果
            getRestaurants(reply_token, locations[user_id], user_keywords[user_id], user_filter_sequence[user_id], price_criteria)
    elif (msg in ["$", "$$", "$$$", "$$$$"]) and (price_criteria == None):
        price_dict = {"$":'1', "$$":'2', "$$$":'3', "$$$$":'4'}
        price_criteria = price_dict[msg]
        remaining_options = [x for x in filter_options if x not in user_filter_sequence[user_id]]
        if remaining_options:
            send_quick_reply(reply_token, f"您已選擇：{', '.join(user_filter_sequence[user_id])}\n是否需要選擇下一個篩選標準？", remaining_options + ["結束篩選"]) # 添加結束篩選的選項
        else:
            getRestaurants(reply_token, locations[user_id], user_keywords[user_id], user_filter_sequence[user_id], price_criteria)
    # 這邊續必須注意順序
    elif (msg == "結束篩選") and (user_id in user_filter_sequence): # 當用戶選擇結束篩選時，進行篩選並輸出結果
        getRestaurants(reply_token, locations[user_id], user_keywords[user_id], user_filter_sequence[user_id], price_criteria)
    elif msg == "滿意":
        line_bot_api.reply_message(reply_token, TextSendMessage(text="祝用餐愉快囉！😋"))
        del user_filter_sequence[user_id]
        del user_detailed_filter[user_id]
    elif msg == "不滿意": # 最後會詢問是否滿意，將根據用戶所選擇的篩選標準提供更詳細的範圍選項，直到用戶滿意為止
        user_detailed_filter[user_id]["step"] = 0  # 重置步驟數
        send_filter(reply_token, user_detailed_filter[user_id]) # 發送篩選範圍的選項
    elif user_id in user_detailed_filter: # 接著根據篩選範圍的文字進行篩選
        process_filter(reply_token, locations[user_id], user_keywords[user_id], user_detailed_filter[user_id], msg, price_criteria)
    elif '地震！' in msg:
        reply = earth_quake()
        text_message = TextSendMessage(text=reply[0])  # 建立文字訊息
        line_bot_api.reply_message(event.reply_token, text_message)  # 回覆地震資訊的文字訊息
        line_bot_api.push_message(event.source.user_id, ImageSendMessage(original_content_url=reply[1], preview_image_url=reply[1]))  # 地震資訊的圖片訊息
    else:
        message = "嗨～記得先點選下方選單的定位唷！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))

# 處理位置訊息
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    reply_token = event.reply_token
    address = event.message.address.replace('台', '臺') # 取出地址資訊，並將「台」換成「臺」
    lng = event.message.longitude # 取出經度
    lat = event.message.latitude # 取出緯度
    user_id = event.source.user_id # 使用者 ID
    locations[user_id] = {'lat': lat, 'lng': lng} # 儲存經緯度到字典
    reply = weather(address, lat, lng)
    text_message = TextSendMessage(text=reply) # 建立文字訊息
    # -----------------------------------------------------------------------------------------
    # 建立雷達回波圖
    img_url = f'https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-001.png?{time.time_ns()}'
    img_message = ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)
    # -----------------------------------------------------------------------------------------
    # 獲得服務選擇確認模板
    service_selection_message = service_choice_confirm() # 獲得服務選擇確認模板
    line_bot_api.reply_message(reply_token, [img_message, text_message, service_selection_message]) # 同時回覆雷達回波圖、天氣預報、服務選擇確認





@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)


import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
