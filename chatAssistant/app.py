import base64
import io
import logging
import os
import time
import wave
import json
from typing import List, Dict, Any

import numpy as np
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from openai import OpenAI

from config import config
from intent.processIntent import HandleAnswer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化配置
load_dotenv()

# 初始化Flask应用
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route('/')
def index():
    """默认路由，重定向到演示页面"""
    return app.send_static_file('upload_demo.html')


@app.route('/demo')
def demo():
    """演示页面路由"""
    return app.send_static_file('upload_demo.html')


class AudioConfig:
    """音频配置常量类"""
    # 录音参数
    CHANNELS = 1
    RATE = 16000  # 16kHz更适合语音识别
    CHUNK = 480  # 30ms的帧大小
    SILENCE_TIMEOUT = 0.4  # 静音超时(秒)
    THRESHOLD = 10000  # 音量阈值
    RECORD_MAXSECONDS = 20  # 最大录音时长
    # 播放参数
    PLAY_RATE = 24000  # TTS通常使用24kHz
    PLAY_CHUNK = 1024  # 播放块大小
    # 前两秒不检测静音
    PLAY_SILENCE_TIMEOUT = 2  # 播放静音超时(秒)


class ConversationManager:
    """管理对话历史和系统消息"""

    def __init__(self):
        self.sys_msg = {
            "role": "system",
            "content": "你是一个语音助手，根据提供的上下文回答用户语音描述的问题。回答应简洁明了、专业准确"
        }
        self.message: List[Dict[str, Any]] = []
        self.max_history = 5  # 保留最近的5条对话

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.message.append({"role": "user", "content": [content]})
        self._trim_history()

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息"""
        self.message.append({"role": "assistant", "content": content.strip()})
        self._trim_history()

    def get_recent_messages(self) -> List[Dict[str, Any]]:
        """获取最近的对话历史"""
        return self.message[-self.max_history:]

    def _trim_history(self) -> None:
        """修剪对话历史，保留最近的max_history条消息"""
        if len(self.message) > self.max_history * 2:  # 用户和助手各5条
            self.message = self.message[-self.max_history * 2:]


class AudioProcessor:
    """处理音频数据的类"""

    @staticmethod
    def base64_to_wav(base64_audio: str) -> bytes:
        """将base64音频数据转换为WAV格式"""
        try:
            # 解码base64数据
            audio_data = base64.b64decode(base64_audio)

            with io.BytesIO() as wav_buffer:
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(AudioConfig.CHANNELS)
                    wav_file.setsampwidth(2)  # 16-bit audio
                    wav_file.setframerate(AudioConfig.RATE)
                    wav_file.writeframes(audio_data)
                return wav_buffer.getvalue()
        except Exception as e:
            logger.error(f"Error converting base64 to WAV: {e}")
            raise


class VoiceAssistant:
    """运行语音助手主循环"""

    def __init__(self):
        self.conversation = ConversationManager()
        self.audio_processor = AudioProcessor()
        self.is_speaking = False
        # 预初始化MCP处理器，避免每次使用时重新创建和启动
        self.mcp_processor = None
        self._init_mcp_processor()

    def _init_mcp_processor(self):
        """初始化MCP处理器"""
        try:
            print("正在初始化MCP处理器...")
            from intent.mcpIntentProcessor import MCPIntentProcessor
            self.mcp_processor = MCPIntentProcessor()
        except Exception as e:
            logger.error(f"MCP处理器初始化失败: {str(e)}")
            self.mcp_processor = None

    def _process_with_mcp(self, intent_result, user_input, conversation_history):
        """统一的MCP处理逻辑"""
        try:
            # 检查MCP处理器是否可用
            if self.mcp_processor is None:
                print("MCP处理器未初始化，尝试重新初始化...")
                self._init_mcp_processor()
            
            if self.mcp_processor is not None:
                return self.mcp_processor.process_intent(
                    intent_result, 
                    user_input, 
                    conversation_history, 
                    3
                )
            else:
                print("MCP处理器不可用，回退到传统处理")
                raise Exception("MCP处理器不可用")
                
        except Exception as e:
            logger.error(f"MCP处理失败，回退到传统处理: {str(e)}")
            # 回退到传统RAG处理
            handleAnswer = HandleAnswer()
            return handleAnswer.answer_question(user_input, conversation_history, 3)

    def process_input(self, data: str, input_type: str, description: str = ""):
        """处理接收到的输入数据（音频、文本、图片）"""
        try:
            startTime = time.time()
            rag_result = None
            suggested_action = None
            
            if input_type == "audio":
                logger.info("Processing audio data...")
                
                # 使用新的音频意图处理器
                from intent.audioIntentProcessor import AudioIntentProcessor
                audio_processor = AudioIntentProcessor()
                s_time = time.time()    
                intent_result = audio_processor.process_audio_with_intent(data)
                end_time = time.time()
                print("音频意图识别用时：", end_time - s_time)
                
                # 检查是否有错误
                if "error" in intent_result:
                    logger.error(f"音频处理失败: {intent_result['error']}")
                    socketio.emit('error', {'message': '语音识别失败，请重试'})
                    return
                
                transcription = intent_result.get("transcription", "")
                
                # 添加到对话历史
                self.conversation.add_user_message({
                    "type": "text",
                    "text": transcription
                })
                time_start = time.time()
                # 根据意图调用相应的服务
                rag_result = self._process_with_mcp(intent_result, transcription, self.conversation.get_recent_messages())
                
                end_time = time.time()
                print("AI意图处理用时：", end_time - time_start)
                print("AI意图+处理用时：", end_time - startTime)
            elif input_type == "text":
                # 文本输入现在也支持MCP处理
                self.conversation.add_user_message({
                    "type": "text",
                    "text": f"{data}"
                })
                
                # 使用MCP意图处理器处理文本
                from intent.intentRecognizer import IntentRecognizer
                
                # 首先进行意图识别
                intent_recognizer = IntentRecognizer()
                intent_result = intent_recognizer.recognize(data)
                print("intent_result", intent_result)
                
                rag_result = self._process_with_mcp(intent_result, data, self.conversation.get_recent_messages())
                
            elif input_type == "image":
                logger.info("Processing image data...")
                data_image = data['image']
                data_text = data['text']
                description = data_text
                # 使用新的图片意图处理器
                from intent.imageIntentProcessor import ImageIntentProcessor
                from intent.processIntent import ProcessIntent
                image_processor = ImageIntentProcessor()
                s_time = time.time()
                intent_result = image_processor.process_image_with_intent(data_image, data_text)
                end_time = time.time()
                print("图片意图识别用时：", end_time - s_time)
                
                # 检查是否有错误
                if "error" in intent_result:
                    logger.error(f"图片处理失败: {intent_result['error']}")
                    socketio.emit('error', {'message': '图片识别失败，请重试'})
                    return
                
                ocr_text = intent_result.get("ocr_text", "")
                suggested_action = intent_result.get("suggested_action", {})
                
                print(f"图片OCR结果: {ocr_text}")
                print(f"识别意图: {intent_result.get('intent')}")
                print(f"建议操作: {suggested_action}")
                
                # 添加到对话历史
                combined_message = f"用户描述：{description}\n图片内容：{suggested_action}"
                self.conversation.add_user_message({
                    "type": "text",
                    "text": combined_message
                })
                processIntent = ProcessIntent("image")
                # 处理图片意图并生成答案
                rag_result, suggested_action = processIntent.process_intent(
                    intent_result, description, self.conversation.get_recent_messages()
                )
                
                end_time = time.time()
                print("图片AI处理总用时：", end_time - startTime)

            # 发送开始说话事件
            socketio.emit('speaking_start')

            # 发送建议操作（如果有）
            if suggested_action and suggested_action.get("action_type") != "error":
                socketio.emit('suggested_action', {
                    'action': suggested_action,
                    'inputType': input_type
                })

            # 流式请求与播放
            s_time = time.time()
            full_response = ""
            self.is_speaking = True
            
            # 添加音频片段计数器，用于调试
            audio_chunk_count = 0
            first_audio_sent = False
            
            for chunk in rag_result:
                if not self.is_speaking:
                    break
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "audio"):
                        # 处理文本转录
                        transcript = delta.audio.get("transcript", "")                    
                        # 处理音频数据
                        audio_data = delta.audio.get("data", "")
                        if audio_data:
                            audio_chunk_count += 1
                            current_time = time.time()
                            
                            # 记录第一个音频块的延迟
                            if not first_audio_sent:
                                first_audio_delay = current_time - s_time
                                print(f"首个音频块延迟: {first_audio_delay:.3f}秒")
                                first_audio_sent = True
                            
                            # 立即发送音频数据，不等待缓冲
                            socketio.emit('audio', {
                                'data': audio_data, 
                                "inputType": input_type,
                                'chunk_id': audio_chunk_count,  # 添加块ID用于调试
                                'timestamp': current_time,  # 添加时间戳
                                'size': len(audio_data)  # 添加数据大小
                            })
                            # 强制刷新socket连接，确保数据立即发送
                            socketio.sleep(0)
                            
                        if transcript:
                            socketio.emit('transcript', {'text': transcript})
                            full_response += transcript
            end_time = time.time()
            # 流式播放音频用时
            print("流式播放音频用时：", end_time - s_time)
            # AI回答用时
            print("AI回答总用时：", end_time - startTime)
            # 发送结束说话事件
            socketio.emit('speaking_end', {"inputType": input_type})
            self.is_speaking = False

            # 保存对话
            if full_response:
                self.conversation.add_assistant_message(full_response)

        except Exception as e:
            logger.error(f"处理输入时出错: {e}")
            socketio.emit('error', {'message': str(e)})
            self.is_speaking = False


# 创建全局助手实例
assistant = VoiceAssistant()


@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')


@socketio.on('audio_data')
def handle_audio_data(data):
    """处理接收到的音频数据"""
    if 'data' in data:
        assistant.process_input(data['data'], "audio")


@socketio.on('text_data')
def handle_text(data):
    print("处理文本。。。。。。。。。。")
    if 'text' in data:
        assistant.process_input(data['text'], "text")


@socketio.on('image_data')
def handle_image_data(data):
    """处理接收到的图片数据"""
    print("处理图片数据...")
    if 'image' in data:
        description = data.get('description', '')  # 获取用户的描述文字
        assistant.process_input(data, "image", description)


@socketio.on('stop_speaking')
def handle_stop_speaking():
    """处理停止说话事件"""
    logger.info("Received stop speaking request")
    assistant.is_speaking = False


if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=config["port"], debug=True)
    finally:
        # 清理MCP连接
        try:
            from intent.mcpIntentProcessor import cleanup_mcp_connections
            cleanup_mcp_connections()
        except Exception as e:
            logger.error(f"清理MCP连接时出错: {str(e)}")
