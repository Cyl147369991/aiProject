import asyncio
import json
import logging
import os
import subprocess
from typing import Dict, List, Any, Optional
from threading import Thread, Event
import queue
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPServerConnection:
    """单个MCP服务器连接的管理类"""
    
    def __init__(self, name: str, script_path: str, description: str = ""):
        self.name = name
        self.script_path = script_path
        self.description = description
        self.session: Optional[ClientSession] = None
        self.tools = []
        self.resources = []
        self.connected = False
        self.server_process = None
        # 异步上下文管理器
        self.stdio_context = None
        self.session_context = None
        self.read_stream = None
        self.write_stream = None
        
    async def connect(self):
        """连接到MCP服务器"""
        try:
            # 设置服务器参数
            server_params = StdioServerParameters(
                command="python",
                args=[self.script_path]
            )
            
            # 使用正确的异步上下文管理器方式
            self.stdio_context = stdio_client(server_params)
            self.read_stream, self.write_stream = await self.stdio_context.__aenter__()
            
            self.session_context = ClientSession(self.read_stream, self.write_stream)
            self.session = await self.session_context.__aenter__()
            await self.session.initialize()
            
            # 获取工具和资源列表
            await self.refresh_capabilities()
            self.connected = True
            logger.info(f"成功连接到MCP服务器: {self.name}")
            
        except Exception as e:
            logger.error(f"连接MCP服务器 {self.name} 失败: {str(e)}")
            self.connected = False
            # 清理连接
            await self._cleanup_connection()
            raise
    
    async def disconnect(self):
        """断开MCP服务器连接"""
        try:
            await self._cleanup_connection()
            self.connected = False
            logger.info(f"断开MCP服务器连接: {self.name}")
        except Exception as e:
            logger.error(f"断开MCP服务器 {self.name} 连接时出错: {str(e)}")
    
    async def _cleanup_connection(self):
        """清理连接资源"""
        try:
            if hasattr(self, 'session_context') and self.session_context:
                await self.session_context.__aexit__(None, None, None)
                self.session_context = None
                self.session = None
            
            if hasattr(self, 'stdio_context') and self.stdio_context:
                await self.stdio_context.__aexit__(None, None, None)
                self.stdio_context = None
                
        except Exception as e:
            logger.error(f"清理连接资源时出错: {str(e)}")
    
    async def refresh_capabilities(self):
        """刷新服务器的工具和资源列表"""
        if not self.session:
            return
            
        try:
            # 获取工具列表
            self.tools = await self.session.list_tools()
            print("self.tools", self.tools)
            logger.info(f"服务器 {self.name} 有 {len(self.tools)} 个工具")
            
            # 获取资源列表
            self.resources = await self.session.list_resources()
            logger.info(f"服务器 {self.name} 有 {len(self.resources)} 个资源")
            
        except Exception as e:
            logger.error(f"刷新服务器 {self.name} 能力时出错: {str(e)}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """调用服务器上的工具"""
        if not self.session or not self.connected:
            return [{"error": f"服务器 {self.name} 未连接"}]
        
        try:
            import time
            tool_start = time.time()
            logger.info(f"调用服务器工具: {self.name}.{tool_name}")
            result = await self.session.call_tool(tool_name, arguments)
            parsed_results = []
            for content in result:
                if content[1] is not None and isinstance(content[1], list):
                    result_content = content[1]
                    for item in result_content:
                        if item.type == "text":
                            parsed_results.append(item.text)
                # if hasattr(content, 'text'):
                #     print("content.text", content.get("text",""))
                # if hasattr(content, 'type') and content.type == "text":
                #     try:
                #         print("content.text", content.text)
                #         # 尝试解析JSON
                #         parsed_results.append(json.loads(content.text))
                #     except:
                #         # 如果不是JSON，直接返回文本
                #         parsed_results.append({"text": content.text})
                
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 在服务器 {self.name} 时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return [{"error": str(e)}]


class MCPClientManager:
    """MCP客户端管理器，管理多个MCP服务器连接"""
    
    def __init__(self):
        self.connections: Dict[str, MCPServerConnection] = {}
        self.loop = None
        self.loop_thread = None
        self.running = False
        self.loop_ready = Event()  # 用于同步事件循环启动
        
        # 预定义的MCP服务器配置
        self.server_configs = {
            "weather": {
                "script_path": "chatAssistant/mcpserver/weatherMcpServer_stdio.py",
                "description": "真实天气查询服务"
            },
            "financial": {
                "script_path": "chatAssistant/mcpserver/FinancialMCPServer.py", 
                "description": "财务数据分析服务"
            }
        }
        
    def start(self):
        """启动MCP客户端管理器"""
        if self.running:
            print("MCP客户端管理器已启动===")
            return
            
        self.running = True
        self.loop_ready.clear()  # 清除事件状态
        
        self.loop_thread = Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # 等待事件循环启动完成，最多等待3秒
        if self.loop_ready.wait(timeout=1):
            logger.info("MCP客户端管理器已启动")
        else:
            logger.error("MCP客户端管理器启动超时")
            self.running = False
            raise RuntimeError("MCP客户端管理器启动超时")
    
    def stop(self):
        """停止MCP客户端管理器"""
        if not self.running:
            return
            
        self.running = False
        if self.loop and not self.loop.is_closed():
            # 异步关闭所有连接
            asyncio.run_coroutine_threadsafe(self._disconnect_all(), self.loop)
            # 停止事件循环
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.loop_thread:
            self.loop_thread.join(timeout=5)
        
        logger.info("MCP客户端管理器已停止")
    
    def _run_event_loop(self):
        """在单独线程中运行事件循环"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop_ready.set()  # 通知主线程事件循环已准备就绪
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"事件循环运行时出错: {str(e)}")
            self.loop_ready.set()  # 即使出错也要通知主线程
        finally:
            # 确保循环被关闭
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            print("事件循环清理完成")
    
    async def _disconnect_all(self):
        """断开所有MCP服务器连接"""
        for connection in self.connections.values():
            try:
                await connection.disconnect()
            except Exception as e:
                logger.error(f"断开连接时出错: {str(e)}")
    
    def connect_server(self, server_name: str) -> bool:
        """连接到指定的MCP服务器"""
        if not self.running:
            logger.error("MCP客户端管理器未运行")
            return False
            
        if server_name not in self.server_configs:
            logger.error(f"未知的服务器: {server_name}")
            return False
        
        # 检查是否已经连接
        if server_name in self.connections and self.connections[server_name].connected:
            logger.info(f"服务器 {server_name} 已经连接，跳过连接")
            return True
        
        config = self.server_configs[server_name]
        connection = MCPServerConnection(
            name=server_name,
            script_path=config["script_path"],
            description=config["description"]
        )
        
        try:
            import time
            connect_start = time.time()
            logger.info(f"开始连接MCP服务器: {server_name}")
            
            # 在事件循环中执行连接，使用更短的超时时间
            future = asyncio.run_coroutine_threadsafe(connection.connect(), self.loop)
            future.result(timeout=3)  # 3秒超时，更快失败
            
            connect_end = time.time()
            logger.info(f"连接服务器 {server_name} 成功，耗时: {connect_end - connect_start:.2f}秒")
            
            self.connections[server_name] = connection
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"连接服务器 {server_name} 超时")
            return False
        except Exception as e:
            logger.error(f"连接服务器 {server_name} 失败: {str(e)}")
            return False
    
    def disconnect_server(self, server_name: str) -> bool:
        """断开指定的MCP服务器连接"""
        if server_name not in self.connections:
            return True
        
        connection = self.connections[server_name]
        try:
            future = asyncio.run_coroutine_threadsafe(connection.disconnect(), self.loop)
            future.result(timeout=5)
            del self.connections[server_name]
            return True
        except Exception as e:
            logger.error(f"断开服务器 {server_name} 失败: {str(e)}")
            return False
    
    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """调用指定服务器上的工具"""
        import time
        call_start_time = time.time()
        
        if not self.running:
            return [{"error": "MCP客户端管理器未运行"}]
        
        logger.info(f"开始调用工具: {server_name}.{tool_name}")
        
        # 检查连接状态
        if server_name not in self.connections:
            logger.info(f"服务器 {server_name} 未连接，尝试自动连接")
            connect_start = time.time()
            if not self.connect_server(server_name):
                logger.error(f"连接服务器 {server_name} 失败")
                return [{"error": f"无法连接到服务器: {server_name}"}]
            connect_end = time.time()
            logger.info(f"连接服务器耗时: {connect_end - connect_start:.2f}秒")
        
        connection = self.connections[server_name]
        if not connection.connected:
            logger.error(f"服务器 {server_name} 连接状态异常")
            return [{"error": f"服务器 {server_name} 连接已断开"}]
        
        try:
            logger.info(f"提交异步工具调用: {server_name}.{tool_name}")
            async_start = time.time()
            
            future = asyncio.run_coroutine_threadsafe(
                connection.call_tool(tool_name, arguments), 
                self.loop
            )
            
            # 使用更短的超时时间，避免长时间等待
            result = future.result(timeout=2)  # 3秒超时
            
            async_end = time.time()
            call_end_time = time.time()
            
            logger.info(f"异步调用耗时: {async_end - async_start:.2f}秒")
            logger.info(f"工具调用总耗时: {call_end_time - call_start_time:.2f}秒")
            logger.info(f"工具调用成功: {server_name}.{tool_name}")
            
            return result
            
        except asyncio.TimeoutError:
            call_end_time = time.time()
            logger.error(f"工具调用超时: {server_name}.{tool_name}，总耗时: {call_end_time - call_start_time:.2f}秒")
            return [{"error": f"工具调用超时: {tool_name}"}]
        except Exception as e:
            call_end_time = time.time()
            logger.error(f"调用工具失败: {str(e)}，总耗时: {call_end_time - call_start_time:.2f}秒")
            return [{"error": str(e)}]
    
    def get_available_tools(self) -> Dict[str, List[str]]:
        """获取所有可用的工具列表"""
        available_tools = {}
        for server_name, connection in self.connections.items():
            if connection.connected:
                tool_names = [tool.name for tool in connection.tools]
                available_tools[server_name] = tool_names
        return available_tools
    
    def query_weather(self, city: str) -> Dict[str, Any]:
        """查询天气的便捷方法"""
        result = self.call_tool("weather", "query_weather", {"city": city})
        return result if result else {"error": "天气查询失败"}
    
    def query_financial_data(self, question: str, report_type: str = "all") -> Dict[str, Any]:
        """查询财务数据的便捷方法"""
        result = self.call_tool("financial", "query_financial_data", {
            "question": question,
            "report_type": report_type
        })
        return result[0] if result else {"error": "财务查询失败"}


# 全局MCP客户端管理器实例
mcp_manager = MCPClientManager() 