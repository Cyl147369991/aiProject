from qwenRagQuery import retrieve_documents,build_context
from API.weatherService import WeatherService
import time
from typing import Dict
import json
from datetime import datetime
from intent.intentRecognizer import IntentRecognizer
from config import config
from modelClient.qwenOnmi import QwenOnmi
import os
from dotenv import load_dotenv

load_dotenv()

class ProcessIntent:
    def __init__(self,type) -> None:
        self.type = type

    def process_intent(self,intent_result: dict, question: str, his: list, top_k: int = 5):
        if self.type == "image":
            """
            根据图片意图结果处理并生成答案
            """
            intent = intent_result.get("intent", "knowledge_base")
            ocr_text = intent_result.get("ocr_text", "")
            suggested_action = intent_result.get("suggested_action", {})
            
            # 构建综合信息用于生成回答
            combined_info = f"用户描述：{question}\n图片内容：{suggested_action}"
            
            if intent == "take_leave":
                # 请假相关处理
                prompt = his + [{
                    "role": "user", 
                    "content": f"{combined_info}\n\n这是一个请假相关的请求。请根据图片信息和用户描述，提供相应的帮助和建议。如果需要跳转到请假页面，请在回答中明确说明。"
                }]
                
            elif intent == "reimbursement":
                # 报销相关处理
                prompt = his + [{
                    "role": "user", 
                    "content": f"{combined_info}\n\n这是一个报销相关的请求。请根据图片中的发票或收据信息，提供报销建议和帮助。"
                }]
                
            elif intent == "system_navigation":
                # 系统导航处理
                prompt = his + [{
                    "role": "user", 
                    "content": f"{combined_info}\n\n用户需要系统功能导航帮助。请提供相应的操作指导。"
                }]
                
            else:
                # 默认知识库查询
                prompt = his + [{
                    "role": "user", 
                    "content": combined_info
                }]
                handleAnswer = HandleAnswer()
                return handleAnswer.generate_answer(prompt, intent), suggested_action
        else:
            """
            根据意图结果处理问题并生成答案
            这个函数可以被音频处理和文本处理共同使用
            """
            if intent_result["intent"] == "knowledge_base":
                # 查询知识库
                docs = retrieve_documents(question, top_k)
                print("检索到的文档:", docs)
                prompt = build_context(docs, his)
                handleAnswer = HandleAnswer()
                return handleAnswer.generate_answer(prompt, intent_result["intent"])
            elif intent_result["intent"] == "weather":
                start_time = time.time()
                # 处理天气查询
                weather_service = WeatherService()
                location = ""
                dtime = ""
                if isinstance(intent_result["entities"], list):
                    for item in intent_result["entities"]:
                        if item["type"] == "location":
                            location = item["value"]
                        if item["type"] == "time":
                            if item["value"] == "现在":
                                dtime = "now"
                            else:
                                dtime = "forecast"
                else:
                    location = intent_result["entities"].get("location", "")
                    time_value = intent_result["entities"].get("time", "")
                    if time_value == "现在":
                        dtime = "now"
                    elif time_value == "今天":
                        dtime = "today"
                    else:
                        dtime = "forecast"
                print("调用天气api接口：", location, dtime)
                weather_info = weather_service.get_weather(location, dtime)
                end_time = time.time()
                print("天气api接口查询耗时：", end_time - start_time)
                print("天气信息:", weather_info)
                # 构建天气查询的prompt
                prompt = his + [{"role": "user", "content": question}]
                handleAnswer = HandleAnswer()
                return handleAnswer.generate_answer(prompt, intent_result["intent"], weather_info)
            elif intent_result["intent"] == "history":
                # 处理历史对话相关的问题
                prompt = his
                handleAnswer = HandleAnswer()
                return handleAnswer.generate_answer(prompt, intent_result["intent"])
            else:
                # 其他类型的问题，默认查询知识库
                docs = retrieve_documents(question, top_k)
                prompt = build_context(docs, his)
                handleAnswer = HandleAnswer()
                return handleAnswer.generate_answer(prompt, intent_result["intent"])
            

class HandleAnswer:
    def __init__(self) -> None:
        pass

    def generate_answer(self,prompt, intent: str = "knowledge_base", weather_info: Dict = None) -> str:
        start_time = time.time()
       

        # 根据意图选择系统提示
        if intent == "knowledge_base":
            system_prompt = "你是一个知识库助手，根据提供的上下文回答用户问题。如果上下文找不到相关问题的答案，请明确告知用户。"
        elif intent == "weather":
            system_prompt = """你是一个天气助手，根据天气信息上下文回答用户问题。
            天气信息包括：
            - 地点
            - 温度（当前温度/体感温度）
            - 天气状况
            - 湿度
            - 风速
            - 气压
            - 云量
            - 能见度
            请用自然语言组织这些信息，让回答更加友好和易读。如果是预报信息，请按时间顺序组织信息。"""
        elif intent == "news":
            system_prompt = "你是一个新闻助手，根据新闻信息回答用户问题。"
        else:
            system_prompt = "你是一个智能助手，根据上下文回答用户问题。"

        messages = [
            {"role": "user", "content": system_prompt},
            {"role": "assistant", "content": "好的，我记住了你的设定。"}
        ]
        
        # 如果是天气查询，添加天气信息
        if intent == "weather" and weather_info and not weather_info.get("error"):
            datetime_str = datetime.now().strftime("%Y-%m-%d")
            weather_context = f"今天是{datetime_str}，未来5天天气信息：{json.dumps(weather_info, ensure_ascii=False)}"
            messages.append({"role": "user", "content": weather_context})

        messages = messages + prompt
        print("最终发送给模型的消息:", messages)
        qwenOnmi = QwenOnmi(os.getenv("QWEN-ONMI-TURBO_API_KEY"),config["base_url"],config["model"])
        completion = qwenOnmi.chat_stream(messages)
        end_time = time.time()
        print("生成答案耗时：", end_time - start_time)
        return completion
    
    # 执行问答 - 更新以支持新的音频意图处理
    def answer_question(self,question: str, his: list, top_k: int = 5) -> str:
        """
        处理问题并返回答案
        支持传统的文本问题处理流程
        """
        start_time = time.time()
        # 1. 意图识别
        intent_recognizer = IntentRecognizer()
        intent_result = intent_recognizer.recognize(question)
        print("意图识别结果:", intent_result)
        end_time = time.time()
        print("意图识别耗时：", end_time - start_time)
        processIntent = ProcessIntent("text")
        # 2. 根据意图获取信息
        return processIntent.process_intent(intent_result, question, his, top_k)