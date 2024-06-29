from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *
import requests
import json
from datetime import datetime,timedelta
import googlemaps
import numpy as np
import random
from linebot.models import (
    TemplateSendMessage, CarouselTemplate, CarouselColumn,
    URITemplateAction, MessageTemplateAction, LocationSendMessage
)


'''
location = "緯度,經度" 格式:str
keyword = "餐廳種類" 格式:str
filter = "篩選因素"
'''
def choose():
    food_types = {
    "中式料理": ["小籠包", "燒賣", "雞肉飯", "北京烤鴨", "炒麵"],
    "日式料理": ["壽司", "拉麵", "天婦羅", "丼飯", "烤串"],
    "韓式料理": ["石鍋拌飯", "韓式炸雞", "泡菜鍋", "烤肉", "辣炒年糕"],
    "西式料理": ["披薩", "漢堡", "義大利麵", "牛排", "沙拉"],
    "泰式料理": ["冬蔭功", "綠咖哩", "泰式炒河粉", "紅咖哩雞", "檸檬魚"],
    "印度料理": ["咖哩雞", "羊肉手抓飯", "印度烤餅（Naan）", "黃豆咖哩", "辣椒雞"],
    "越南料理": ["越南河粉", "春捲", "越式法國麵包", "魚露炒牛肉", "越南煎餅"],
    "速食/快餐": ["炸雞", "薯條", "熱狗", "三明治", "捲餅"],
    "台灣小吃": ["滷肉飯", "蚵仔煎", "鹽酥雞", "大腸包小腸", "牛肉麵", "豆花", "鹽水雞", "雞排", "臭豆腐", "車輪餅"]
    }
    randomKey = random.choice(list(food_types.keys()))
    randomValue = random.choice(food_types[randomKey])
    return randomValue

def getRestaurant(location, keyword="", filter=["rate"]):
    response = sendRequest(location, keyword)
    if response.status_code == 200:
        results = response.json().get("results", [])  # 將json改為dict，get("result"，[])為提取Key為result的值，若無符合則設為空列表
        global stores # 全域變數
        stores = []
        detailUrl = "https://maps.googleapis.com/maps/api/place/details/json"
        detailParam = {
                       "key" : "AIzaSyB4zpkvW7_RYWWv-glU9EWl5uueCWBFHxA"
                    }
        for i in results:
            if i.get("opening_hours",{}).get("open_now",False):
                storeLocation = i.get("geometry",{}).get("location",{})
                storeLocation = f"{storeLocation['lat']},{storeLocation['lng']}"
                placeId = i.get("place_id")
                detailParam["place_id"] = placeId
                detail = requests.get(detailUrl,params=detailParam)
                detail = detail.json().get("result")
                store = {
                    "name": i.get("name"),
                    "address": i.get("vicinity"),
                    "location" : storeLocation,
                    "rate": i.get("rating", "N/A"),
                    "distance" : distance(location,storeLocation),
                    "ratingsNum" : detail.get("user_ratings_total", 0)
                }
                try:
                    float(store["rate"])
                except ValueError:
                    print("",end="")
                stores.append(store)
            else:
                continue
        for i in filter:
            stores.sort(key=lambda x: x[i],reverse=(i == "rate" or i == "ratingsNum"))
            if filter.index(i) == 0:
                stores = stores[:10]
            elif filter.index(i) == 1:
                stores = stores[:5]
            elif filter.index(i) == 2:
                pass
        return stores
    else:
        return f"request fail:{response.status_code}"

def sendRequest(location, keyword):
    params = {
        "key": "AIzaSyB4zpkvW7_RYWWv-glU9EWl5uueCWBFHxA",
        "location": location,
        "radius": 5000,
        "type": "restaurant",
        "keyword": keyword,
        "language": "zh-TW"
    }
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    response = requests.get(url, params=params)
    return response

def distance(location1,location2):
    gmaps = googlemaps.Client(key='AIzaSyB4zpkvW7_RYWWv-glU9EWl5uueCWBFHxA')
    # 設定距離矩陣參數
    distances = gmaps.distance_matrix(
        origins=[location1],
        destinations=[location2],
        mode='driving',  # 可以根據需要選擇 'driving'、'walking'、'bicycling' 或 'transit'
        language='zh-TW',  # 語言設置，可根據需要更改
    )
    # 解析距離矩陣結果
    distance_meters = distances['rows'][0]['elements'][0]['distance']['value']
    distance_kilometers = distance_meters / 1000.0
    return distance_kilometers
# 測試程式碼
#print(getRestaurant('25.0330,121.5654',"牛排","distance"))
