import os
import sys
from typing import List, Dict
from datetime import datetime
import json
from collections import defaultdict

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# 初始化 MCP 服务器
mcp = FastMCP("WeatherServer")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
city_url = "https://api.openweathermap.org/geo/1.0/direct"
query_url = "https://api.openweathermap.org/data/2.5"


def get_city_id(city_name: str) -> Dict:
    """根据中文城市名获取城市信息"""
    try:
        print(f"[天气服务器] 开始查询城市ID: {city_name}")
        city_param = {
            "q": city_name + ",CN",
            "appid": OPENWEATHER_API_KEY,
        }
        print(f"[天气服务器] 发送城市查询请求...")
        response = requests.get(city_url, params=city_param, timeout=3)  # 减少超时时间
        print(f"[天气服务器] 城市查询响应状态: {response.status_code}")
        
        data = response.json()
        if data and len(data) > 0:
            print(f"[天气服务器] 城市查询成功: {data[0].get('name')}")
            return data[0]
        else:
            raise ValueError(f"找不到城市: {city_name}")
    except requests.exceptions.Timeout:
        raise ValueError(f"城市查询超时: {city_name}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"城市查询网络错误: {str(e)}")
    except Exception as e:
        raise ValueError(f"城市查询失败: {str(e)}")


def process_weather_forecast(weather_list: List[Dict]) -> List[Dict]:
    """处理天气预报数据"""
    try:
        # 分组容器
        grouped = defaultdict(list)

        # 1. 按天分组
        for item in weather_list:
            dt = item['dt']
            date_str = datetime.fromtimestamp(dt).strftime("%Y-%m-%d")
            grouped[date_str].append(item)

        # 2. 计算每组的统计值
        result = []
        for date, items in grouped.items():
            if not items:
                continue
                
            temp_max = max(i['main']['temp_max'] for i in items)
            temp_min = min(i['main']['temp_min'] for i in items)
            # 其它字段取平均
            avg_feels_like = int(sum(i['main']['feels_like'] for i in items) / len(items))
            avg_humidity = int(sum(i['main']['humidity'] for i in items) / len(items))
            wind_speed = int(sum(i['wind']['speed'] for i in items) / len(items))
            visibility = int(sum(i['visibility'] for i in items) / len(items)) if 'visibility' in items[0] else 0
            
            # 获取天气描述
            descriptions = set()
            for i in items:
                for w in i['weather']:
                    descriptions.add(w['description'])
            weather = ', '.join(descriptions)
            
            result.append({
                'date': date,
                'temp_max': int(temp_max),
                'temp_min': int(temp_min),
                'feels_like': avg_feels_like,
                'humidity': avg_humidity,
                'wind_speed': wind_speed,
                "visibility": visibility,
                'condition': weather
            })
        
        return result
        
    except Exception as e:
        return f"天气数据处理失败: {str(e)}"


def get_weather(city_name: str) -> List[Dict]:
    """根据城市中文名返回天气json参数"""
    try:
        print(f"[天气服务器] 开始查询城市: {city_name}")
        
        if not OPENWEATHER_API_KEY:
            return "错误: 未设置 OPENWEATHER_API_KEY 环境变量"
        
        # 获取城市信息
        city_data = get_city_id(city_name)
        print(f"[天气服务器] 找到城市: {city_data.get('name', city_name)}")
        
        # 查询天气
        params = {
            "q": city_data["name"],
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",  # 使用摄氏度
            "lang": "zh_cn"  # 使用中文
        }
        
        print(f"[天气服务器] 调用天气API...")
        import time
        api_start = time.time()
        
        response = requests.get(query_url + "/forecast", params=params, timeout=2)  # 减少超时时间
        
        api_end = time.time()
        print(f"[天气服务器] API调用耗时: {api_end - api_start:.2f}秒")
        print(f"[天气服务器] API响应状态: {response.status_code}")
        
        data = response.json()
        
        if data.get("cod") != "200":
            error_msg = f"天气查询失败：{data.get('message', '未知错误')}"
            print(f"[天气服务器] {error_msg}")
            return error_msg
        
        weather_list = data["list"]
        print(f"[天气服务器] 获取到 {len(weather_list)} 条天气数据")
        
        # 处理天气数据
        processing_start = time.time()
        result = process_weather_forecast(weather_list)
        processing_end = time.time()
        
        print(f"[天气服务器] 数据处理耗时: {processing_end - processing_start:.2f}秒")
        print(f"[天气服务器] 天气查询成功完成")
        return result
        
    except requests.exceptions.Timeout:
        error_msg = f"天气API调用超时：{city_name}"
        print(f"[天气服务器] {error_msg}")
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"天气API网络错误：{str(e)}"
        print(f"[天气服务器] {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"查询出错：{str(e)}"
        print(f"[天气服务器] {error_msg}")
        return error_msg


@mcp.tool('query_weather', '查询城市天气')
def query_weather(city: str) -> List[Dict]:
    """
    输入指定城市的中文名称，返回当前天气查询结果。
    :param city: 城市名称
    :return: 格式化后的天气信息
    """
    import time
    tool_start = time.time()
    print(f"[天气工具] 收到查询请求: {city}", file=sys.stderr)
    
    try:
        result = get_weather(city)
        tool_end = time.time()
        
        result_length = len(str(result))
        print(f"[天气工具] 工具处理耗时: {tool_end - tool_start:.2f}秒", file=sys.stderr)
        print(f"[天气工具] 返回结果长度: {result_length} 字符", file=sys.stderr)
        
        sys.stderr.flush()
        return result
        
    except Exception as e:
        tool_end = time.time()
        print(f"[天气工具] 工具执行失败，耗时: {tool_end - tool_start:.2f}秒", file=sys.stderr)
        print(f"[天气工具] 错误: {str(e)}", file=sys.stderr)
        sys.stderr.flush()
        return f"天气查询失败: {str(e)}"


if __name__ == "__main__":
    print("[天气服务器] 启动天气MCP服务器...")
    # 以标准 I/O 方式运行 MCP 服务器
    mcp.run(transport='stdio')
