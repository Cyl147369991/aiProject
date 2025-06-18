import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from config import config
from modelClient.qwenOnmi import QwenOnmi
import time
load_dotenv()


class AudioIntentProcessor:
    """直接处理音频并识别意图的处理器"""
    
    def __init__(self):
        self.api_key = os.getenv("QWEN-ONMI-TURBO_API_KEY")
        self.base_url = config["base_url"]
    
    def process_audio_with_intent(self, audio_data: str) -> Dict[str, Any]:
        """
        直接处理音频并识别意图
        :param audio_data: base64编码的音频数据
        :return: 包含意图、转录和实体的字典
        """
        try:
            # 确保音频数据格式正确
            if not audio_data.startswith('data:audio/wav;base64,'):
                audio_data = f'data:audio/wav;base64,{audio_data}'
            qwenOnmi = QwenOnmi(self.api_key,self.base_url,"qwen-omni-turbo")
            messages=[]
            messages.append({
                        "role": "user", 
                        "content": """你是一个智能语音助手。请分析用户的语音输入，识别意图并按以下JSON格式返回：
                        {
                        "intent": "knowledge_base|weather|news|conversation|history|take leave",
                        "transcription": "用户说的原始文字",
                        "entities": {
                            "location": "地点（如果有）",
                            "time": "时间（如果有）",
                            "topic": "主题（如果有）"
                        },
                        "confidence": 0.95
                        }

                        意图说明：
                        - knowledge_base: 需要查询知识库的问题
                        - weather: 天气相关查询
                        - news: 新闻相关查询  
                        - conversation: 普通对话
                        - history: 历史对话查询
                        - take leave:请假
                        请确保返回格式严格按照JSON格式，返回结果能够进行json解析，不要返回其他回答"""
                    })
            messages.append({
                "role":"assistant", 
                "content": "好的，我记住了你的设定。"})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": "wav",
                        },
                    },
                    {"type": "text", "text": "请分析这段语音的意图并返回JSON格式结果"}
                ]
            })
            stime = time.time()
            # 直接让AI处理音频并识别意图
            completion = qwenOnmi.chat_stream(messages,["text"])
            endtime = time.time()
            print("音频意图识别用时：", endtime - stime)
            
            # 优化：使用列表收集结果，减少字符串拼接开销
            result_chunks = []
            
            # 解析结果 - 优化版本
            for chunk in completion:
                # 提前检查 chunk.choices 存在且非空
                if not (chunk.choices and chunk.choices[0].delta):
                    continue
                    
                delta = chunk.choices[0].delta
                # 直接检查 audio 属性并获取 transcript
                if hasattr(delta, "audio") and delta.audio:
                    transcript = delta.audio.get("transcript")
                    if transcript:  # 只添加非空的transcript
                        result_chunks.append(transcript)
            
            # 一次性拼接所有结果
            result_text = "".join(result_chunks)
           
            # 尝试解析JSON
            try:
                print("原始AI回复:", result_text.replace("\\", ""))
                result = json.loads(result_text.replace("\\", ""))
                print("解析后的结果:", result)
                return result
            except json.JSONDecodeError:
                # 如果解析失败，尝试提取JSON部分
                import re
                json_match = re.search(r'\{[^}]*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
                else:
                    # 如果完全解析失败，返回默认结果
                    return {
                        "intent": "knowledge_base",
                        "transcription": result_text,  # 将整个回复作为转录
                        "entities": {},
                        "confidence": 0.5
                    }
                    
        except Exception as e:
            print(f"音频意图处理失败: {e}")
            return {
                "intent": "knowledge_base",
                "transcription": "",
                "entities": {},
                "confidence": 0.0,
                "error": str(e)
            }