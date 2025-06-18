import os
import requests
from typing import Dict, Any,List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class WeatherService:
    """天气服务"""

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")  # 需要在.env中配置OpenWeather API的key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.city_url = "https://api.openweathermap.org/geo/1.0/direct"

    def get_weather(self, location: str, time: str = "forecast"):
        """
        获取天气信息
        :param location: 地点
        :param time: 时间（now/today/tomorrow/具体日期）
        :return: 天气信息
        """
        try:
            # 处理时间参数
            if time == "now":
                endpoint = "/weather"
            else:
                endpoint = "/forecast"
            city_param = {
                "q": location + ",CN",
                "appid": self.api_key,
            }
            city_response = requests.get(f"{self.city_url}", params=city_param)
            city_response.raise_for_status()
            data = city_response.json()
            
            # 构建请求参数
            params = {
                "q": data[0]["name"],
                "appid": self.api_key,
                "units": "metric",  # 使用摄氏度
                "lang": "zh_cn"  # 使用中文
            }
            # 发送请求
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            data = response.json()
            # 处理响应数据
            if time == "now":
                return self._process_current_weather(data)
            else:
                return self._process_forecast_weather(data, time)

        except Exception as e:
            print(f"获取天气信息失败: {e}")
            return {
                "error": True,
                "message": f"获取{location}的天气信息失败"
            }

    def _process_current_weather(self, data: Dict) -> Dict[str, Any]:
        """处理当前天气数据"""
        try:
            return {
                "error": False,
                "location": data["name"],
                "time": datetime.fromtimestamp(data["dt"]).strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "condition": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "pressure": data["main"]["pressure"],
                "clouds": data["clouds"]["all"],
                "visibility": data.get("visibility", "未知")
            }
        except Exception as e:
            print(f"处理当前天气数据失败: {e}")
            return {"error": True, "message": "处理天气数据失败"}

    def _process_forecast_weather(self, data: Dict, time: str) -> Dict[str, Any]:
        """处理天气预报数据"""
        try:
            location = data["city"]["name"]
            forecast_list = data["list"]
            # if time == "today":
            #     # 获取今天的天气预报（每3小时一次）
            #     today_forecast = [
            #         {
            #             "time": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
            #             "temperature": item["main"]["temp"],
            #             "feels_like": item["main"]["feels_like"],
            #             "condition": item["weather"][0]["description"],
            #             "humidity": item["main"]["humidity"],
            #             "wind_speed": item["wind"]["speed"],
            #             "visibility": item.get("visibility", "未知")
            #         }
            #         for item in forecast_list[:8]  # 获取24小时内的预报
            #     ]

            #     return {
            #         "error": False,
            #         "location": location,
            #         "date": datetime.fromtimestamp(forecast_list[0]["dt"]).strftime("%Y-%m-%d"),
            #         "forecast": today_forecast
            #     }
            # else:
            #     # 获取未来5天的天气预报（每天一次）
            #     daily_forecast = process_weather_forecast(forecast_list)
            #     print("daily_forecast:", daily_forecast)
            #     return {
            #         "error": False,
            #         "location": location,
            #         "forecast": daily_forecast
            #     }
            # 获取未来5天的天气预报（每天一次）
            daily_forecast = process_weather_forecast(forecast_list)
            print("daily_forecast:", daily_forecast)
            return {
                "error": False,
                "location": location,
                "forecast": daily_forecast
            }
        except Exception as e:
            print(f"处理天气预报数据失败: {e}")
            return {"error": True, "message": "处理天气数据失败"}
        
def process_weather_forecast(weather_list: List[Dict]) -> List[Dict]:
    """处理天气预报数据"""
    # 分组容器
    from collections import defaultdict
    grouped = defaultdict(list)

    # 1. 按天分组
    for item in weather_list:
        dt = item['dt']
        date_str = datetime.fromtimestamp(dt).strftime("%Y-%m-%d")
        grouped[date_str].append(item)

    # 2. 计算每组的统计值
    result = []
    for date, items in grouped.items():
        temp_max = max(i['main']['temp_max'] for i in items)
        temp_min = min(i['main']['temp_min'] for i in items)
        # 其它字段取平均
        avg_feels_like = int(sum(i['main']['feels_like'] for i in items) / len(items))
        avg_humidity = int(sum(i['main']['humidity'] for i in items) / len(items))
        wind_speed = int(sum(i['wind']['speed'] for i in items) / len(items))
        visibility = int(sum(i['visibility'] for i in items) / len(items))
        descriptions = set()
        for i in items:
            for w in i['weather']:
                s = w['description']
                ds = s.split("，")
                for item in ds:
                    descriptions.add(item)
        weather = '，'.join(descriptions)
        #根据items[0]['weather'][0]['description']，如果包含雨，则weather为雨，如果包含雪，则weather为雪，如果包含晴，则weather为晴，如果包含多云，则weather为多云，如果包含阴，则weather为阴，如果包含雾，则weather为雾，如果包含霾，则weather为霾，如果包含沙尘，则weather为沙尘，如果包含尘土，则weather为尘土，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，则weather为雾霾，如果包含雾霾，
        
        # 可按需添加其它字段
        result.append({
            'date': date,
            'temp_max': temp_max,
            'temp_min': temp_min,
            'feels_like': avg_feels_like,
            'humidity': avg_humidity,
            'wind_speed': wind_speed,
            "visibility":visibility,
            'condition': weather
        })
    return result