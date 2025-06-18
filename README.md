# AI语音助手项目

这是一个基于Vue.js前端和Flask后端的AI语音助手项目，支持语音交互、图像处理、意图识别等功能。

## 项目结构

```
AI/
├── chatAssistant/                 # 后端主目录
│   ├── app.py                    # Flask主应用入口
│   ├── config.py                 # 配置文件
│   ├── run_server.py             # 服务器启动脚本
│   ├── API/                      # API服务
│   │   └── weatherService.py     # 天气服务
│   ├── intent/                   # 意图识别模块
│   │   ├── audioIntentProcessor.py    # 音频意图处理器
│   │   ├── imageIntentProcessor.py    # 图像意图处理器
│   │   ├── intentRecognizer.py        # 意图识别器
│   │   ├── mcpIntentProcessor.py      # MCP意图处理器
│   │   └── processIntent.py           # 意图处理主文件
│   ├── mcpclient/                # MCP客户端
│   │   ├── financial_mcp_client.py    # 财务MCP客户端
│   │   ├── mcp_client_manager.py      # MCP客户端管理器
│   │   └── supabse_query_client.py    # Supabase查询客户端
│   ├── mcpserver/                # MCP服务器
│   │   ├── FinancialMCPServer.py      # 财务MCP服务器
│   │   └── weatherMcpServer_stdio.py  # 天气MCP服务器
│   ├── modelClient/              # 模型客户端
│   │   └── qwenOnmi.py          # 通义千问Omni客户端
│   └── static/                   # 静态文件
├── frontend/                     # 前端Vue.js项目
│   ├── src/
│   │   ├── App.vue              # 主应用组件
│   │   └── components/
│   │       └── VoiceAssistant.vue   # 语音助手组件
│   ├── package.json             # 前端依赖配置
│   └── public/
└── README.md                    # 项目说明文档
```

## 功能特性

- 🎤 **语音交互**: 支持实时语音识别和语音合成
- 🖼️ **图像处理**: 支持图像上传、OCR文字识别
- 🤖 **意图识别**: 智能识别用户意图（知识查询、天气查询、请假等）
- 🌤️ **天气服务**: 提供实时天气查询功能
- 💼 **MCP协议**: 支持Model Context Protocol进行多模态交互
- 📊 **财务数据**: 支持财务数据查询和分析
- 🔍 **知识库**: 基于RAG的知识库问答系统

## 环境要求

### 后端环境
- Python 3.8+
- 操作系统: Windows/Linux/macOS

### 前端环境
- Node.js 14+
- npm 6+

## 后端依赖库安装

首先确保已安装Python，然后安装以下依赖：

```bash
cd chatAssistant
pip install -r requirements.txt
```

### 主要依赖库：

#### Web框架和通信
```bash
pip install flask==3.0.2
pip install flask-socketio==5.3.6
pip install flask-cors==3.0.10
pip install python-socketio==5.11.1
pip install python-engineio==4.9.0
pip install gunicorn
pip install gevent
pip install gevent-websocket
```

#### AI和机器学习
```bash
pip install openai==1.3.0
pip install numpy==1.21.2
```

#### 音频处理
```bash
pip install pyaudio==0.2.11
pip install wave
```

#### 数据处理和存储
```bash
pip install pandas
pip install supabase
pip install sqlite3  # Python内置
```

#### 文档处理和RAG
```bash
pip install langchain
pip install langchain-community
```

#### 配置和环境
```bash
pip install python-dotenv==0.19.0
```

#### MCP协议支持
```bash
pip install mcp
```

#### HTTP请求
```bash
pip install requests
```

## 前端依赖安装

```bash
cd frontend
npm install
```

### 主要前端依赖：
- Vue.js 2.6.14
- Element UI 2.15.14
- Socket.IO Client 4.7.4

## 环境配置

在`chatAssistant`目录下创建`.env`文件，配置以下环境变量：

```env
# 通义千问API配置
QWEN-ONMI-TURBO_API_KEY=your_qwen_api_key
QWEN-VL-PLUS_KEY=your_qwen_vl_api_key

# OpenWeather API配置
OPENWEATHER_API_KEY=your_openweather_api_key

# Supabase配置
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## 启动方式

### 1. 启动后端服务

```bash
cd chatAssistant
python app.py
```

后端服务将在 `http://localhost:8000` 启动

### 2. 启动前端服务

```bash
cd frontend
npm run serve
```

前端服务将在 `https://localhost:8080` 启动（支持HTTPS）

## API接口

### Socket.IO事件

- `audio_data`: 发送音频数据
- `text_data`: 发送文本数据  
- `image_data`: 发送图像数据
- `stop_speaking`: 停止语音播放

### REST API

- `GET /`: 主页
- `GET /demo`: 演示页面

## 开发说明

### 音频处理配置
- 采样率: 16kHz (语音识别)
- 通道数: 1 (单声道)
- 位深度: 16位
- 播放采样率: 24kHz (TTS输出)

### 意图识别类型
- `knowledge_base`: 知识库查询
- `weather`: 天气查询
- `news`: 新闻查询
- `conversation`: 普通对话
- `history`: 历史对话
- `take_leave`: 请假申请
- `reimbursement`: 报销相关

## 故障排除

### 常见问题

1. **音频设备权限**: 确保浏览器已授权麦克风权限
2. **HTTPS要求**: 前端使用HTTPS以支持音频录制
3. **API Key配置**: 确保`.env`文件中的API密钥正确配置
4. **端口冲突**: 检查8000和8080端口是否被占用

### 日志查看

后端日志保存在 `chatAssistant/assistant.log` 文件中

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情 