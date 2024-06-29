from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *


#======這裡是呼叫的檔案內容=====
from Map import *
from Restaurant import *
from Restaurant import getRestaurant
from Weather import *
#======這裡是呼叫的檔案內容=====

#======python的函數庫==========
import tempfile, os
import datetime
import time
#======python的函數庫==========

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




# 處理訊息
user_state = {}
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id
    if user_id not in user_state:
        user_state[user_id] = {'action': None, 'filter': [], "keyword":""}
    elif 'ccclub' in msg:
        message = Confirm_Template()
        line_bot_api.reply_message(event.reply_token, message)
    elif '地震' in msg:
        reply = earth_quake()
        text_message = TextSendMessage(text=reply[0])  # 建立文字訊息
        line_bot_api.reply_message(event.reply_token, text_message)  # 回覆地震資訊的文字訊息
        line_bot_api.push_message(event.source.user_id, ImageSendMessage(original_content_url=reply[1], preview_image_url=reply[1]))  # 地震資訊的圖片訊息
    elif '選擇障礙救星' in msg:
        choice = choose()
        user_state[user_id]["keyword"] = choice
        message = choice + "\n您要使用評分還是距離篩選"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        user_state[user_id]['action'] = 'choose_filter'
    elif '已決定要吃甚麼' in msg:
        message = "請輸入關鍵字"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        user_state[user_id]['action'] = 'get_keyword'
    elif user_state[user_id].get('action') == 'get_keyword':
        user_state[user_id]['keyword'] = msg
        message = "您要使用評分、距離還是評論數篩選"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        user_state[user_id]['action'] = 'choose_filter'
    elif '評分' in msg or '距離' in msg:
        if user_state[user_id].get('action') == 'choose_filter':
            if "評分" in msg:
                user_state[user_id]["filter"].append("rate")
            if "距離" in msg:
                user_state[user_id]["filter"].append("distance")
            if "評論數" in msg:
                user_state[user_id]["filter"].append("ratingsNum")
            keyword = user_state[user_id].get('keyword')
            if user_id in locations:
                longitude = locations[user_id]["longitude"]
                latitude = locations[user_id]["latitude"]
            message = getRestaurant(f"{latitude},{longitude}", keyword, user_state[user_id]["filter"])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
            user_state[user_id]['action'] = None  # 重置用户状态
    elif '測試用' in msg: # 測試
        message = getRestaurant()
        line_bot_api.reply_message(event.reply_token, message)


    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)
    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)
    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)
    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)
    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)
    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)
    # elif '使用者輸入的訊息' in msg:
    #     message = 要呼叫的function名稱()
    #     line_bot_api.reply_message(event.reply_token, message)


# 用一個字典暫時儲存用戶的經緯度，key 是用戶ID，value 是經緯度的字典
locations = {}

# 處理位置訊息
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    reply_token = event.reply_token
    address = event.message.address.replace('台', '臺') # 取出地址資訊，並將「台」換成「臺」
    longitude = event.message.longitude # 取出經度
    latitude = event.message.latitude # 取出緯度
    user_id = event.source.user_id # 使用者 ID
    locations[user_id] = {'longitude': longitude, 'latitude': latitude} # 儲存經緯度到字典
    reply = weather(address, longitude, latitude)
    text_message = TextSendMessage(text=reply) # 建立文字訊息
    # -----------------------------------------------------------------------------------------
    # 建立雷達回波圖
    img_url = f'https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Observation/O-A0058-001.png?{time.time_ns()}'
    img_message = ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)
    # -----------------------------------------------------------------------------------------
    # 獲得服務選擇確認模板
    service_selection_message = service_choice_confirm() # 獲得服務選擇確認模板
    line_bot_api.reply_message(reply_token, [img_message, text_message, service_selection_message]) # 同時回覆雷達回波圖、天氣預報、服務選擇確認

##################################################
# 從資料庫獲取最新位置
# 範例：
# user_id = event.source.user_id
# if user_id in locations:
#     longitude = locations[user_id]['longitude']
#     latitude = locations[user_id]['latitude']
#     print(f'定位位置：經度 {longitude}, 緯度 {latitude}')
# else:
#     print('此用戶未提供定位')
##################################################



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


##################################################

#以下是返回地圖功能
#篩選功能好像無法運作，如要測試地圖功能可先使用codetest的資料測試(註解的地方要換成codetest)

codetest = [
    {
        "name": "餐廳A",
        "address": "台北市中正區忠孝東路一段1號",
        "rate": 4.5,
        "distance": 1.25,
        "location": "25.045158,121.515739" 
    },
    {
        "name": "餐廳B",
        "address": "台北市大安區復興南路一段1號",
        "rate": 4.2,
        "distance": 2.5,
        "location": "25.033963,121.543303"  
    },
    {
        "name": "餐廳C",
        "address": "台北市信義區松高路12號",
        "rate": 4.7,
        "distance": 3.1,
        "location": "25.034413,121.566504" 
    }
]

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == "輸出篩選結果":
        columns = []
        for restaurant in stores: #測試:如要測試地圖功能，stores要換成codetest
            column = CarouselColumn(
                title=restaurant['name'],
                text=f"地址: {restaurant['address']}\n評分: {restaurant['rate']}顆星\n距離: {restaurant['distance']}公里",
                actions=[
                    MessageAction(label='地圖搜尋', text=f"{restaurant['name']}位置")
                ]
            )
            columns.append(column)
        
        carousel_template = CarouselTemplate(columns=columns)
        template_message = TemplateSendMessage(
            alt_text='店家資訊',
            template=carousel_template
        )
        
        line_bot_api.reply_message(event.reply_token, template_message)
    else:
        handle_location_request(event)

def handle_location_request(event):
    for restaurant in stores:     #測試:如要測試地圖功能，stores要換成codetest
        if event.message.text == f"{restaurant['name']}位置":
            location_message = LocationSendMessage(
                title=restaurant['name'],
                address=restaurant['address'],
                latitude=float(restaurant['location'].split(',')[0]),
                longitude=float(restaurant['location'].split(',')[1])
            )
            line_bot_api.reply_message(event.reply_token, location_message)
            break

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
