import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from config import config

load_dotenv()

class IntentRecognizer:
    """意图识别器"""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("QWEN3-8B_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def recognize(self, question: str) -> Dict[str, Any]:
        """
        识别问题意图
        返回: {
            "intent": "knowledge_base|weather|news|conversation|history|take leave",
            "entities": {
                "location": "北京",
                "time": "今天",
                "topic": "天气"
            },
            "confidence": 0.95
        }
        """
        messages=[]
        messages.append({
            "role": "system",
            "content": """你是一个意图识别助手。你需要分析用户的问题，识别意图和实体。
            意图类型包括：
            1. knowledge_base: 需要查询知识库的问题
            2. weather: 天气相关查询
            3. news: 新闻相关查询
            4. conversation: 普通对话
            5. history: 历史对话查询
            6. take leave:请假
            实体类型包括：
            - location: 地点
            - time: 时间
            - topic: 主题
            - person: 人物
            - organization: 组织
            请以JSON格式返回，包含以下字段：
            - intent: 意图类型
            - entities: 识别到的实体
            - confidence: 置信度(0-1)

            """
        })
        messages.append({
            "role": "user",
            "content": question
        })
        try:
            response = self.client.chat.completions.create(
                model="qwen3-8b",
                messages=messages,
                # Qwen3模型通过enable_thinking参数控制思考过程（开源版默认True，商业版默认False）
                # 使用Qwen3开源版模型时，若未启用流式输出，请将下行取消注释，否则会报错
                extra_body={"enable_thinking": False}
            )
            
            # 获取AI回复内容
            ai_content = response.choices[0].message.content
            print("意图识别AI原始结果：", ai_content)
            
            # 尝试解析JSON，如果失败则进行清理后再解析
            try:
                result = json.loads(ai_content)
            except json.JSONDecodeError:
                # 如果不是标准JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    print("提取的JSON字符串：", json_str)
                    result = json.loads(json_str)
                else:
                    # 如果完全无法解析，返回默认值
                    print("无法解析AI返回的JSON，使用默认值")
                    result = {
                        "intent": "knowledge_base",
                        "entities": {},
                        "confidence": 0.5
                    }
            
            print("解析后的意图结果：", result)
            return result
            
        except Exception as e:
            print(f"意图识别失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "intent": "knowledge_base",
                "entities": {},
                "confidence": 0.5
            }
