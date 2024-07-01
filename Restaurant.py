from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import requests
import math, json, time, random, os
from geopy.distance import geodesic

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# Google Maps API Key
GOOGLE_MAPS_API_KEY = 'AIzaSyDCM_Xvw4Jd2ytCRwWcqxhzMERJwFQjvBw'



# 選擇障礙救星
def choose_food(food_type):
    types = {
        "正餐": [
            "牛肉麵", "火鍋", "燒烤", "日式定食", "粵菜餐廳", "泰式料理", "義大利麵",
            "韓式燒肉", "印度咖哩", "台式便當", "排骨飯", "三杯雞", "滷肉飯", "雞腿飯",
            "便當店", "焢肉飯", "烤鴨", "蚵仔煎", "炒飯", "炒麵", "魯肉飯", "雞肉飯",
            "蒸餃", "水餃", "牛排館", "燒臘飯", "雞排飯", "鱔魚意麵", "豬腳飯", "魚湯",
            "炒青菜", "蔥爆牛肉", "砂鍋粥", "紅燒魚", "烤魚", "香酥鴨", "豆腐煲", "熱炒"
        ],
        "小吃": [
            "雞排", "滷味", "鹽酥雞", "蚵仔煎", "車輪餅", "臭豆腐", "章魚小丸子", "春捲",
            "水煎包", "煎餃", "雞蛋仔", "燒賣", "豆花", "燒仙草", "炸湯圓", "肉圓", "紅豆餅",
            "胡椒餅", "蛋餅", "麻糬", "肉鬆餅", "花生捲冰淇淋", "涼麵", "刨冰",
            "米糕", "四神湯", "魚丸湯", "甜不辣", "大腸包小腸", "雞肉飯", "鴨血糕", "魷魚羹",
            "黑輪", "燒餅油條", "鹽水雞", "炸豆腐", "關東煮"
        ],
        "飲料": [
            "珍珠奶茶", "紅茶拿鐵", "咖啡", "果汁", "冰沙", "奶昔", "椰子水", "檸檬紅茶", "綠豆沙"
        ],
        "點心": [
            "蛋糕店", "餅乾", "巧克力", "糖果", "果凍", "甜甜圈", "冰淇淋", "馬卡龍",
            "鬆餅", "泡芙", "奶酥", "芝士蛋糕", "布朗尼", "水果塔", "千層蛋糕"
        ]
    }
    randomValue = random.choice(types[food_type])
    return randomValue

# 建立LINE中發送快速回覆的函數
def send_quick_reply(reply_token, text, options, additional_messages=None):
    quick_reply_buttons = [QuickReplyButton(action=MessageAction(label=opt, text=opt)) for opt in options] # 根據參數options建立回覆按鈕
    quick_reply = QuickReply(items=quick_reply_buttons) # 將回覆按鈕封裝成 QuickReply 物件
    messages = []
    if additional_messages:
        messages.extend(additional_messages) # 先添加 additional_messages(卡片訊息)
    messages.append(TextSendMessage(text=text, quick_reply=quick_reply))
    line_bot_api.reply_message(reply_token, messages)

# 回傳餐廳
def getRestaurants(reply_token, user_location, keyword, criteria, price_criteria, basic_filter=True, radius=10000): # 將搜尋範圍預設為10公里

    nearby_restaurants = nearby_search(user_location, keyword, radius) # 執行附近餐廳的搜尋
    if basic_filter:
        restaurants = sort_restaurants(nearby_restaurants, criteria, user_location, price_criteria)
    else:
        restaurants = sort_restaurants(nearby_restaurants, criteria, user_location, price_criteria, basic_filter=False)

    restaurants_details = []
    for x in restaurants[:5]: # 從篩選出的餐廳中取前五間
        details = get_place_details(x['place_id'])
        location = details.get('geometry', {}).get('location', {})
        distance = calculate_distance(user_location['lat'], user_location['lng'], location.get('lat'), location.get('lng'))
        restaurants_details.append({
            "name": details["name"],
            "image_url": details["image_url"],
            "rating": details["rating"],
            "distance": distance,
            "reviews": details["user_ratings_total"],
            "price_level": str(details.get('price_level', 'N/A')),
            "google_maps_url": details["url"],
        })
    if not restaurants_details: # 如果 restaurants_details 為空字串，表示沒有符合的餐廳
        line_bot_api.reply_message(reply_token, TextSendMessage(text="目前沒有符合條件的餐廳。"))
        return
    flex_contents = create_flex_message_contents(restaurants_details)
    flex_message = FlexSendMessage(
        alt_text='推薦的餐廳',
        contents={
            "type": "carousel",
            "contents": flex_contents
        }
    )
    send_quick_reply(reply_token, "您對這些結果滿意嗎？", ["滿意", "不滿意"], additional_messages=[flex_message])


# 排序餐廳
def sort_restaurants(restaurants, criteria, user_location, price_criteria, basic_filter=True):
    open_restaurants = [x for x in restaurants if x.get('opening_hours', {}).get('open_now', False)] # JSON檔中的營業與否會顯示在 opening_hours 中的 open_now
    def sort_key(restaurant, criteria, user_location):
        distance = calculate_distance(user_location['lat'], user_location['lng'], restaurant['geometry']['location']['lat'], restaurant['geometry']['location']['lng'])
        rating = restaurant.get('rating', 0)
        reviews = restaurant.get('user_ratings_total', 0)
        key = []
        for x in criteria:
            if x == '距離':
                key.append(distance)
            elif x == '星數':
                key.append(-rating) # 加負號表示越高越好
            elif x == '評論數':
                key.append(-reviews) # 加負號表示越高越好
        return tuple(key) # 轉成 tuple

    if basic_filter:
        if "價格" in criteria: # 如果criteria中包含價格範圍，先進行價格篩選
            open_restaurants = [x for x in open_restaurants if str(x.get('price_level')) == price_criteria]
        sorted_restaurants = sorted(open_restaurants, key=lambda x: sort_key(x, criteria, user_location)) # 使用 sort_key 取得篩選標準的 tuple(有順序之分) 進行排序
        return sorted_restaurants
    else:
        if "價格" in criteria['sequence']: # 如果criteria中包含價格範圍，先進行價格篩選
            open_restaurants = [x for x in open_restaurants if str(x.get('price_level')) == price_criteria]
        criteria = criteria["criteria"]
       # 設定篩選標準
        if "distance" in criteria:
            distance_range = criteria.get("distance", "0~10000公尺")
            min_distance, max_distance = map(int, distance_range.replace("公尺", "").split('~'))
        if "rating" in criteria:
            min_rating, max_rating = criteria["rating"]
        if "reviews" in criteria:
            min_reviews, max_reviews = criteria["reviews"]

        restaurants = []
        for x in open_restaurants:
            location = x.get('geometry', {}).get('location', {})
            distance = calculate_distance(user_location['lat'], user_location['lng'], location.get('lat'), location.get('lng'))
            # 篩選符合基本條件的地點
            if "distance" in criteria and not (min_distance <= distance <= max_distance):
                continue
            if "rating" in criteria and not (min_rating <= x.get('rating', 0) <= max_rating):
                continue
            if "reviews" in criteria and not (min_reviews <= x.get('user_ratings_total', 0) <= max_reviews):
                continue
            restaurants.append(x)
        # 排序
        sorted_restaurants = sorted(restaurants, key=lambda x: sort_key(x, criteria, user_location))
        return sorted_restaurants


# 發送詳細篩選訊息
def send_filter(reply_token, user_detailed_filter):
    step = user_detailed_filter["step"] # 取得當前的步驟數
    sequence = user_detailed_filter["sequence"] # 取得篩選的序列
    if step < len(sequence): # 如果當前步驟小於篩選序列長度
        criteria = sequence[step]
        if criteria == "距離":
            send_quick_reply(reply_token, "請選擇距離範圍：", ["0~600公尺", "601~1800公尺", "1801~3000公尺", "3001~6000公尺", "6001~10000公尺"])
        elif criteria == "星數":
            send_quick_reply(reply_token, "請選擇星數範圍：", ["3.0~3.5", "3.6~4.0", "4.1~4.5", "4.6~5.0"])
        elif criteria == "評論數":
            send_quick_reply(reply_token, "請選擇評論數範圍：", ["0~150條", "151~300條", "301~450條", "451~600條", "600條以上"])
        elif criteria == "價格":
            send_quick_reply(reply_token, "請選擇價格範圍：", ["$", "$$", "$$$", "$$$$"])


# 處理詳細篩選訊息
def process_filter(reply_token, user_location, keyword, user_detailed_filter, msg, price_criteria):
    step = user_detailed_filter["step"]
    sequence = user_detailed_filter["sequence"]
    if step < len(sequence):
        criteria = sequence[step]
        if criteria == "距離":
            user_detailed_filter["criteria"]["distance"] = msg
        elif criteria == "星數":
            min_rating, max_rating = map(float, msg.split('~'))
            user_detailed_filter["criteria"]["rating"] = (min_rating, max_rating)
        elif criteria == "評論數":
            if msg == "600條以上":
                user_detailed_filter["criteria"]["reviews"] = (600, float('inf'))
            else:
                min_reviews, max_reviews = map(int, msg.replace("條", "").split('~'))
                user_detailed_filter["criteria"]["reviews"] = (min_reviews, max_reviews)
        elif criteria == "價格":
            price_dict = {"$":'1', "$$":'2', "$$$":'3', "$$$$":'4'}
            price_criteria = price_dict[msg]
        user_detailed_filter["step"] += 1
        if user_detailed_filter["step"] < len(sequence):
            send_filter(reply_token, user_detailed_filter)
        else:
            getRestaurants(reply_token, user_location, keyword, user_detailed_filter, price_criteria, basic_filter=False)

# 使用 Google Place API 爬取附近餐廳的 JSON 檔
def nearby_search(location, keyword, radius):
    params = {
        "key": GOOGLE_MAPS_API_KEY,
        "location": f"{location['lat']},{location['lng']}",
        "radius": radius,
        "type": "restaurant",
        "keyword": keyword,
        "language": "zh-TW"
    }
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    response = requests.get(url, params=params)
    result = response.json().get('results', {})
    return result

# 使用 Google Place Details API 餐廳的 JSON 檔 (Google map)
def get_place_details(place_id):
    params = {
        "key": GOOGLE_MAPS_API_KEY,
        "place_id": place_id,
        "fields": "name,rating,user_ratings_total,geometry,url,opening_hours,photos,price_level", # 取得餐廳名稱、星等、評論總數、經緯度、Google map連結、營業狀態、相片、價格
        "language": "zh-TW"
    }
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    response = requests.get(url, params=params)
    result = response.json().get('result', {})
    if 'photos' in result:
        photo_reference = result['photos'][0]['photo_reference']
        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
    else:
        image_url = ""
    result['image_url'] = image_url

    return result

# 計算兩個座標的距離
def calculate_distance(lat1, lng1, lat2, lng2):
    return int(geodesic((lat1, lng1), (lat2, lng2)).meters)

# 建立卡片訊息
def create_flex_message_contents(restaurants):
    price_dict = {"1": "$", "2": "$$", "3": "$$$", "4": "$$$$"}
    contents = []
    for restaurant in restaurants:
        bubble = {
            "type": "bubble",
            "size": "deca",
            "hero": {
                "type": "image",
                "url": restaurant["image_url"],
                "size": "full",
                "aspectMode": "cover",
                "aspectRatio": "320:213"
            },  
            "body": {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                   {
                        "type": "text",
                        "text": restaurant["name"],
                        "weight": "bold",
                        "size": "xl",
                        "maxLines":2,
                        "wrap": True
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "icon",
                                "size": "sm",
                                "url": "https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png"
                            },
                            {
                                "type": "text",
                                "text": str(restaurant['rating']),
                                "wrap": True,
                                "weight": "bold",
                                "size": "md",
                                "flex": 0
                            },
                            {
                                "type": "text",
                                "text": "／5 (Google 評分)",
                                "wrap": True,
                                "weight": "regular",
                                "size": "xxs",
                                "flex": 0
                            }
                        ],
                        "margin": "md",
                        "spacing": "none"
                    },
                    {
                        "type": "text",
                        "text": f"距離: {restaurant['distance']} 公尺",
                        "size": "xs",
                        "color": "#8c8c8c",
                        "margin": "md",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"評論數: {restaurant['reviews']}",
                        "size": "xs",
                        "color": "#8c8c8c",
                        "margin": "md",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"價格: {price_dict.get(str(restaurant['price_level']), 'N/A')}",
                        "size": "xs",
                        "color": "#8c8c8c",
                        "margin": "md",
                        "wrap": True
                    }
                ],
                "spacing": "sm",
                "paddingAll": "13px",
                "height":"180px"
            }, 
                "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                        "type": "uri",
                        "label": "查看地圖",
                        "uri": restaurant["google_maps_url"]
                    },
                    "style": "primary",
                    "color": "#A35E47"
                    }
                ],
                "flex": 0,
                "paddingBottom": "15px",
                "paddingTop": "8px"
            }
        }           
        contents.append(bubble)
    return contents