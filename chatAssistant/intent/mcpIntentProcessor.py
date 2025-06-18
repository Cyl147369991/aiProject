import datetime
import json
import logging
from typing import Dict, Any, List
from mcpclient.mcp_client_manager import mcp_manager

logger = logging.getLogger(__name__)


class MCPIntentProcessor:
    """MCP意图处理器，负责将意图路由到相应的MCP服务器"""
    
    def __init__(self):
        self.intent_to_server = {
            "weather": "weather",
            "financial": "financial",
            "knowledge_base": None,  # 使用传统的RAG知识库
            "history": None,  # 使用对话历史
        }
        
        # 确保MCP管理器运行
        if not mcp_manager.running:
            mcp_manager.start()
        
        # 预连接常用的MCP服务器，提高响应速度
        self._preconnect_servers()
    
    def _preconnect_servers(self):
        """预连接MCP服务器，提高响应速度"""
        try:
            import threading
            
            def connect_weather():
                try:
                    print("[MCP预连接] 正在连接天气服务器...")
                    if mcp_manager.connect_server("weather"):
                        print("[MCP预连接] 天气服务器连接成功")
                    else:
                        print("[MCP预连接] 天气服务器连接失败")
                except Exception as e:
                    print(f"[MCP预连接] 天气服务器连接出错: {str(e)}")
            
            # 在后台线程中连接，避免阻塞初始化
            threading.Thread(target=connect_weather, daemon=True).start()
            
        except Exception as e:
            print(f"[MCP预连接] 预连接服务器时出错: {str(e)}")
    
    def process_intent(self, intent_result: Dict[str, Any], question: str, 
                      conversation_history: List[Dict[str, Any]], top_k: int = 5) -> Any:
        """
        处理意图并路由到相应的服务
        
        Args:
            intent_result: 意图识别结果
            question: 用户问题
            conversation_history: 对话历史
            top_k: 知识库检索的文档数量
            
        Returns:
            处理结果 (可能是流式生成器或结果字典)
        """
        intent = intent_result.get("intent", "knowledge_base")
        entities = intent_result.get("entities", {})
        logger.info(f"处理意图: {intent}, 实体: {entities}")
        
        try:
            if intent == "weather":
                print("[MCP处理器] 路由到天气处理")
                return self._handle_weather_intent(entities, question, conversation_history)
            elif intent == "financial":
                print("[MCP处理器] 路由到财务处理")
                return self._handle_financial_intent(entities, question, conversation_history)
            elif intent == "knowledge_base":
                print("[MCP处理器] 路由到知识库处理")
                return self._handle_knowledge_base_intent(question, conversation_history, top_k)
            elif intent == "history":
                print("[MCP处理器] 路由到历史对话处理")
                return self._handle_history_intent(conversation_history)
            else:
                print(f"[MCP处理器] 未知意图 {intent}，回退到知识库处理")
                # 默认使用知识库处理
                return self._handle_knowledge_base_intent(question, conversation_history, top_k)
                
        except Exception as e:
            print(f"[MCP处理器] 处理意图时出错: {str(e)}")
            logger.error(f"处理意图时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._generate_error_response(f"处理请求时出错: {str(e)}", conversation_history)
    
    def _handle_weather_intent(self, entities: Dict[str, Any], question: str, 
                              conversation_history: List[Dict[str, Any]]) -> Any:
        """处理天气查询意图"""
        try:
                
            # 提取地点信息
            location = self._extract_location(entities, question)
            print(f"[天气处理] 提取到的城市: {location}")
            
            if not location:
                print("[天气处理] 未能识别城市名称")
                return self._generate_error_response("无法识别查询的城市，请明确指定城市名称", conversation_history)
            
            logger.info(f"查询城市: {location}")
            
            # 首先尝试调用天气MCP服务器
            import time
            start_time = time.time()
            from API.weatherService import WeatherService
            weather_service = WeatherService()
            weather_result = weather_service.get_weather(location)
            # weather_result = mcp_manager.query_weather(location)
            end_time = time.time()
            print("mcp调用耗时", end_time-start_time)
            # 构建包含天气信息的对话上下文
            weather_context = self._format_weather_info(weather_result, location)
            # 生成回答
            print("[天气处理] 生成天气回答...")
            result = self._generate_weather_response(weather_context, question, conversation_history)
            print("[天气处理] 天气查询处理完成")
            ftime = time.time()
            print("天气处理总用时", ftime-start_time)
            return result
            
        except Exception as e:
            print(f"[天气处理] 处理天气意图时出错: {str(e)}")
            logger.error(f"处理天气意图时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._generate_error_response("天气查询服务暂时不可用", conversation_history)
    
    def _handle_financial_intent(self, entities: Dict[str, Any], question: str,
                                conversation_history: List[Dict[str, Any]]) -> Any:
        """处理财务查询意图"""
        try:
            # 调用财务MCP服务器
            financial_result = mcp_manager.query_financial_data(question)
            
            if "error" in financial_result:
                error_msg = f"财务查询失败: {financial_result['error']}"
                return self._generate_error_response(error_msg, conversation_history)
            
            # 生成财务分析回答
            return self._generate_financial_response(financial_result, question, conversation_history)
            
        except Exception as e:
            logger.error(f"处理财务意图时出错: {str(e)}")
            return self._generate_error_response("财务查询服务暂时不可用", conversation_history)
    
    def _handle_knowledge_base_intent(self, question: str, conversation_history: List[Dict[str, Any]], 
                                     top_k: int) -> Any:
        """处理知识库查询意图 - 使用传统RAG方法"""
        try:
            from qwenRagQuery import retrieve_documents, build_context
            from intent.processIntent import HandleAnswer
            
            # 检索文档
            docs = retrieve_documents(question, top_k)
            logger.info(f"检索到 {len(docs)} 个相关文档")
            
            # 构建上下文
            prompt = build_context(docs, conversation_history)
            
            # 生成答案
            handle_answer = HandleAnswer()
            return handle_answer.generate_answer(prompt, "knowledge_base")
            
        except Exception as e:
            logger.error(f"处理知识库查询时出错: {str(e)}")
            return self._generate_error_response("知识库查询失败", conversation_history)
    
    def _handle_history_intent(self, conversation_history: List[Dict[str, Any]]) -> Any:
        """处理对话历史相关的查询"""
        try:
            from intent.processIntent import HandleAnswer
            
            # 直接使用对话历史生成回答
            handle_answer = HandleAnswer()
            return handle_answer.generate_answer(conversation_history, "history")
            
        except Exception as e:
            logger.error(f"处理历史对话时出错: {str(e)}")
            return self._generate_error_response("无法处理历史对话查询", conversation_history)
    
    def _extract_location(self, entities: Dict[str, Any], question: str) -> str:
        """从实体和问题中提取位置信息"""
        location = ""
        
        # 从实体中提取
        if isinstance(entities, dict):
            location = entities.get("location", "")
        elif isinstance(entities, list):
            for entity in entities:
                if entity.get("type") == "location":
                    location = entity.get("value", "")
                    break
        
        # 如果实体中没有找到，尝试从问题中提取常见城市名
        if not location:
            import re
            # 简单的中文城市名提取
            cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "重庆", "武汉", "西安", "天津", "青岛", "大连", "厦门", "苏州", "无锡", "宁波", "长沙", "郑州", "沈阳"]
            for city in cities:
                if city in question:
                    location = city
                    break
        
        return location
    
    def _format_weather_info(self, weather_data: Any, location: str) -> str:
        """格式化天气信息"""
        timeNow = datetime.datetime.now().strftime("%Y-%m-%d")
        print("weather_data", weather_data)
        try:
            if isinstance(weather_data, dict) and "text" in weather_data:
                return f"今天是{timeNow},{location}的天气信息：{weather_data['text']}"
            elif isinstance(weather_data, str):
                return f"今天是{timeNow},{location}的天气信息：{weather_data}"
            else:
                return f"今天是{timeNow},{location}的天气信息：{json.dumps(weather_data, ensure_ascii=False)}"
        except Exception as e:
            logger.error(f"格式化天气信息失败: {str(e)}")
            return f"{location}的天气信息获取成功"
    
    def _generate_weather_response(self, weather_context: str, question: str, 
                                  conversation_history: List[Dict[str, Any]]) -> Any:
        """生成天气回答"""
        try:
            from intent.processIntent import HandleAnswer
            # 构建包含天气信息的prompt
            messages = conversation_history + [
                {"role": "user", "content": weather_context},
                {"role": "user", "content": question}
            ]
            handle_answer = HandleAnswer()
            import time
            start_time = time.time()
            result = handle_answer.generate_answer(messages, "weather")
            end_time = time.time()
            
            print(f"[天气回答生成] 回答生成完成，耗时: {end_time - start_time:.2f}秒")
            return result
            
        except Exception as e:
            print(f"[天气回答生成] 生成天气回答时出错: {str(e)}")
            logger.error(f"生成天气回答时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._generate_simple_response("天气信息已获取，但回答生成失败", conversation_history)
    
    def _generate_financial_response(self, financial_data: Any, question: str,
                                   conversation_history: List[Dict[str, Any]]) -> Any:
        """生成财务分析回答"""
        try:
            from intent.processIntent import HandleAnswer
            
            # 构建包含财务数据的prompt
            financial_context = f"财务查询结果：{json.dumps(financial_data, ensure_ascii=False)}"
            messages = conversation_history + [
                {"role": "user", "content": financial_context},
                {"role": "user", "content": question}
            ]
            
            handle_answer = HandleAnswer()
            return handle_answer.generate_answer(messages, "financial")
            
        except Exception as e:
            logger.error(f"生成财务回答时出错: {str(e)}")
            return self._generate_simple_response("财务数据已获取，但分析生成失败", conversation_history)
    
    def _generate_error_response(self, error_message: str, conversation_history: List[Dict[str, Any]]) -> Any:
        """生成错误响应"""
        return self._generate_simple_response(error_message, conversation_history)
    
    def _generate_simple_response(self, message: str, conversation_history: List[Dict[str, Any]]) -> Any:
        """生成简单的文本响应"""
        try:
            from intent.processIntent import HandleAnswer
            
            messages = conversation_history + [
                {"role": "user", "content": message}
            ]
            
            handle_answer = HandleAnswer()
            return handle_answer.generate_answer(messages, "simple")
            
        except Exception as e:
            logger.error(f"生成简单回答时出错: {str(e)}")
            # 如果连简单回答都失败，返回一个基本的回答
            class SimpleResponse:
                def __iter__(self):
                    yield type('obj', (object,), {
                        'choices': [type('obj', (object,), {
                            'delta': type('obj', (object,), {
                                'audio': {'transcript': message, 'data': ''}
                            })()
                        })()]
                    })()
            
            return SimpleResponse()


def cleanup_mcp_connections():
    """清理MCP连接的辅助函数"""
    try:
        mcp_manager.stop()
        logger.info("MCP连接已清理")
    except Exception as e:
        logger.error(f"清理MCP连接时出错: {str(e)}")


# 注册清理函数
import atexit
atexit.register(cleanup_mcp_connections) 