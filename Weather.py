import math, json, time, requests
from geopy.distance import geodesic

#============================================================================================
# 爬取中央氣象局的地震資料
def earth_quake():
    result = []
    # 氣象局 api code
    code = 'CWA-EAC9F0DE-E706-4B6B-8CB5-9D502C52392C'
    try:
        # 抓取 "小區域地震" 和 "顯著有感地震"
        # 小區域 https://opendata.cwa.gov.tw/dataset/earthquake/E-A0016-001
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0016-001?Authorization={code}'
        req1 = requests.get(url) # 使用 requests 模組爬取資料
        data1 = req1.json() # 轉換成 JSON
        eq1 = data1['records']['Earthquake'][0] # 取得第一筆地震資訊
        t1 = data1['records']['Earthquake'][0]['EarthquakeInfo']['OriginTime'] # 發生時間
        # -----------------------------------------------------------------------------------------
        # 顯著有感 https://opendata.cwa.gov.tw/dataset/all/E-A0015-001
        url2 = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization={code}'
        req2 = requests.get(url2) # 使用 requests 模組爬取資料
        data2 = req2.json() # 轉換成 JSON
        eq2 = data2['records']['Earthquake'][0] # 取得第一筆地震資訊
        t2 = data2['records']['Earthquake'][0]['EarthquakeInfo']['OriginTime'] # 發生時間
        # -----------------------------------------------------------------------------------------
        # 回傳地震報告之內容和圖片 URI
        if t2>t1:
            result = [eq2['ReportContent'], eq2['ReportImageURI']] # 如果有感地震時間較近，就用顯著有感地震
        else:
            result = [eq1['ReportContent'], eq1['ReportImageURI']] # 使用小區域地震
    except Exception as e:
        print(e)
        result = ['抓取失敗...','']
    return result
#============================================================================================

# 計算兩個地理坐標之間的球面距離，即兩點間的最短距離

# 計算兩個座標的距離
# google api中 lat 表示 latitude 緯度，lng 表示 longitude 經度
def calculate_distance(lat1, lng1, lat2, lng2):
    return int(geodesic((lat1, lng1), (lat2, lng2)).meters)

#============================================================================================

# 爬取即時天氣、氣象預報和空氣品質的資料
# 參數為輸入地址 address
def weather(address, lat, lng):
    result = {}
    # 氣象局 api code
    code = 'CWA-EAC9F0DE-E706-4B6B-8CB5-9D502C52392C'
    # -----------------------------------------------------------------------------------------
    # 即時天氣
    try:
        # 使用兩個 API URL 獲取即時天氣資料
        # 自動氣象站資料-無人自動站氣象資料
        # 現在天氣觀測報告-有人氣象站資料
        url = [f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization={code}',
            f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={code}']

        for item in url:
            req = requests.get(item) # 爬取目前天氣網址的資料
            data = req.json() # 轉JSON
            station = data['records']['Station'] # 觀測站的資訊
            for i in station:
                city = i['GeoInfo']['CountyName'] # 抓取城市名稱
                area = i['GeoInfo']['TownName'] # 鄉鎮名稱
                if not f'{city}{area}' in result: # 爬取還沒記錄過的觀測站資訊
                    weather = i['WeatherElement']['Weather'] # 天氣狀況
                    temp = i['WeatherElement']['AirTemperature'] # 氣溫
                    humid = i['WeatherElement']['RelativeHumidity'] # 相對溼度
                    result[f'{city}{area}'] = f'目前天氣狀況「{weather}」，氣溫 {temp} 度，相對濕度 {humid}%！'
    except:
        pass
    # -----------------------------------------------------------------------------------------
    # 未來兩天的天氣預報
    # 定義一個字典，包含各縣市對應的 API ID
    # 縣市 API ID 請參考: https://opendata.cwa.gov.tw/dist/opendata-swagger.html#/
    api_list = {"宜蘭縣":"F-D0047-001","桃園市":"F-D0047-005","新竹縣":"F-D0047-009","苗栗縣":"F-D0047-013",
        "彰化縣":"F-D0047-017","南投縣":"F-D0047-021","雲林縣":"F-D0047-025","嘉義縣":"F-D0047-029",
        "屏東縣":"F-D0047-033","臺東縣":"F-D0047-037","花蓮縣":"F-D0047-041","澎湖縣":"F-D0047-045",
        "基隆市":"F-D0047-049","新竹市":"F-D0047-053","嘉義市":"F-D0047-057","臺北市":"F-D0047-061",
        "高雄市":"F-D0047-065","新北市":"F-D0047-069","臺中市":"F-D0047-073","臺南市":"F-D0047-077",
        "連江縣":"F-D0047-081","金門縣":"F-D0047-085"}
    for name in api_list:
        if name in address: # 地址對應到時抓取 ID
            city_id = api_list[name]
            break
    # 計算當前時間和三小時後的時間，最後要格式化為 API 所需的格式
    t = time.time() # 返回自 1970 年 1 月 1 日 00:00:00 以來的秒數
    t1 = time.gmtime(t+28800) # 轉換為 UTC 時間，轉化成台灣時區要加八小時等於 28800 秒。struct_time包含年、月、日、時、分、秒、一周的第幾天、一年的第幾天、是否是夏天
    t2 = time.gmtime(t+28800+10800) # 加三小時，三小時等於 10800 秒
    # 轉化為格式「yyyy-MM-ddThh:mm:ss」
    now = time.strftime('%Y-%m-%dT%H:%M:%S',t1)
    now2 = time.strftime('%Y-%m-%dT%H:%M:%S',t2)
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/{city_id}?Authorization={code}&elementName=WeatherDescription&timeFrom={now}&timeTo={now2}'
    req = requests.get(url) # 取得預報資料
    data = req.json() # JSON格式
    city = data['records']['locations'][0]['locationsName'] # 縣市名稱
    location = data['records']['locations'][0]['location'] # 鄉鎮的資訊
    for item in location:
        try:
            area = item['locationName'] # 鄉鎮名稱
            # 天氣資訊中的數值
            # EX: 多雲。降雨機率 10%。溫度攝氏27度。舒適。東南風 平均風速1-2級(每秒2公尺)。相對濕度94%。
            note = item['weatherElement'][0]['time'][0]['elementValue'][0]['value']
            if not f'{city}{area}' in result:
                # 初始化為空字串，為了追加資訊做準備
                result[f'{city}{area}'] = ''
            else:
                # 未來三小時的資訊用空兩行區隔
                result[f'{city}{area}'] = result[f'{city}{area}'] + '\n\n'
            result[f'{city}{area}'] = result[f'{city}{area}'] + '未來三小時' + note
        except:
            pass
    # -----------------------------------------------------------------------------------------

    output = '找不到氣象資訊'
    for i in result:
        if i in address: # 如果輸入的地址有對應到的就輸出
            output = f'「{address}」{result[i]}'
            break

    # -----------------------------------------------------------------------------------------
    # 空氣品質（有特定檢測地點，並非全台都有）
    try:
        # 使用環保署的 API 獲取空氣品質資料
        url = 'https://data.moenv.gov.tw/api/v2/aqx_p_432?api_key=e8dd42e6-9b8b-43f8-991e-b3dee723a52d&limit=1000&sort=ImportDate%20desc&format=JSON'
        req = requests.get(url) # 取得資料
        data = req.json() # 轉成 JSON
        records = data['records']
        nearest_station = None # 先給定最近的觀測站為 None
        min_distance = float('inf') # 最短距離先設為無限大
        for item in records: # 對每個觀測站進行距離的計算，並紀錄最短距離的觀測站
            county = item['county'] # 縣市名稱
            sitename = item['sitename'] # 測站名稱
            station_lng = float(item['longitude']) # 觀測站經度
            station_lat = float(item['latitude']) # 觀測站緯度
            distance = calculate_distance(lat, lng, station_lat, station_lng) # 代入計算距離之函式
            if distance < min_distance: # 如果小於最短距離，更新最近的觀測站的資料
                min_distance = distance
                nearest_station = item
        if nearest_station:
            county = nearest_station['county'] # 縣市名稱
            sitename = nearest_station['sitename'] # 測站名稱
            aqi = int(nearest_station['aqi']) # AQI 數值
            aqi_status = nearest_station['status'] # 空氣狀態
            # 新增到輸出的最後
            output = output + f'\n\n最近空氣檢測站：{county}{sitename}，AQI：{aqi}，空氣品質{aqi_status}。'
    except:
        pass

    return output
#============================================================================================

from linebot.models import *

# 給用戶一個選擇功能選項
def service_choice_confirm():
    buttons_template_message = TemplateSendMessage(
        alt_text='選擇服務',
        template=ButtonsTemplate(
            title='已經想好要吃什麼了嗎？',
            text='請選擇以下服務',
            actions=[
                MessageAction(
                    label='選擇障礙救星',
                    text='選擇障礙救星'
                ),
                MessageAction(
                    label='已決定要吃什麼',
                    text='已決定要吃什麼'
                ),
                MessageAction(
                    label='其他:查看地震資訊',
                    text='地震'
                )
            ]
        )
    )
    return buttons_template_message


