import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from config import config

load_dotenv()

class ImageIntentProcessor:
    """处理图片+文本描述的意图识别和OCR处理器"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("QWEN-VL-PLUS_KEY"),
            base_url=config["base_url"]
        )
    
    def process_image_with_intent(self, image_data: str, description: str = "") -> Dict[str, Any]:
        """
        处理图片和文本描述，进行OCR和意图识别
        :param image_data: base64编码的图片数据
        :param description: 用户的文本描述
        :return: 包含意图、OCR结果、实体和建议操作的字典
        """
        try:
            # 确保图片数据格式正确
            if not image_data.startswith('data:image/'):
                # 默认假设是PNG格式
                image_data = f'data:image/png;base64,{image_data}'
            
            # 构建消息内容
            content_parts = [
                {
                    "type": "text",
                    "text": f"""你是一个智能助手，需要分析用户上传的图片和描述文字，识别意图并提供相应的系统功能建议。

                        用户描述：{description}

                        请分析图片内容，提取文字信息，识别用户意图，并按以下JSON格式返回：
                        {{
                            "intent": "take_leave|reimbursement|attendance|document_review|system_navigation|knowledge_base",
                            "ocr_text": "从图片中识别的所有文字内容",
                            "extracted_info": {{
                                "date": "日期信息（如果有）",
                                "amount": "金额信息（如果有）",
                                "reason": "原因说明（如果有）",
                                "person": "人员信息（如果有）",
                                "location": "地点信息（如果有）"
                            }},
                            "suggested_action": {{
                                "action_type": "navigate_to_page|auto_fill_form|process_document",
                                "target_page": "页面名称（如leave_application, reimbursement_form等）",
                                "auto_fill_data": {{
                                    "field_name": "field_value"
                                }}
                            }},
                            "confidence": 0.95
                        }}

                        意图说明：
                        - take_leave: 请假相关（病假条、请假申请等）
                        - reimbursement: 报销相关（发票、收据等）
                        - attendance: 考勤相关（打卡记录等）
                        - document_review: 文档审查
                        - system_navigation: 系统功能导航
                        - knowledge_base: 查询知识库

                        请确保返回格式严格按照JSON格式，不要返回其他内容。"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data
                    }
                }
            ]
            
            completion = self.client.chat.completions.create(
                model="qwen-vl-plus",  # 使用支持视觉的模型
                messages=[
                    {
                        "role": "user",
                        "content": content_parts
                    }
                ],
                max_tokens=1000
            )
            
            result_text = completion.choices[0].message.content
            print("图片意图识别原始回复:", result_text)
            
            # 尝试解析JSON
            try:
                import re
                # 提取JSON部分
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    print("解析后的图片意图结果:", result)
                    return result
                else:
                    raise json.JSONDecodeError("No JSON found", result_text, 0)
                    
            except json.JSONDecodeError:
                print("JSON解析失败，返回默认结果")
                return {
                    "intent": "knowledge_base",
                    "ocr_text": result_text,
                    "extracted_info": {},
                    "suggested_action": {
                        "action_type": "process_document",
                        "target_page": "",
                        "auto_fill_data": {}
                    },
                    "confidence": 0.5
                }
                
        except Exception as e:
            print(f"图片意图处理失败: {e}")
            return {
                "intent": "knowledge_base",
                "ocr_text": "",
                "extracted_info": {},
                "suggested_action": {
                    "action_type": "error",
                    "target_page": "",
                    "auto_fill_data": {}
                },
                "confidence": 0.0,
                "error": str(e)
            }