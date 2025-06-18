#!/usr/bin/env python3
import asyncio
import json
import os
import sys

# 设置控制台编码为UTF-8，避免中文乱码
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    question = "evancheng?"
    table = "testdoc"

    # 设置服务器参数 - 修复路径
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建服务器脚本的绝对路径
    server_script_path = os.path.join(os.path.dirname(current_dir), "mcpserver", "FinancialMCPServer.py")
    
    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path]
    )

    try:
        # 连接到服务器
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print("正在初始化连接...")
                await session.initialize()
                print("成功连接到Financial MCP服务器")
                # 调用query_supabase_data工具
                arguments = {
                    "question": question,
                    "table": table
                }


                result = await session.call_tool("query_supabase_data", arguments)
                print("result", result)
                
                # 解析并打印结果
                if result and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        try:
                            # 确保文本内容正确编码
                            text_content = content.text
                            if isinstance(text_content, bytes):
                                text_content = text_content.decode('utf-8', errors='replace')
                            
                            # 尝试解析JSON
                            data = json.loads(text_content)
                            
                            # 格式化输出，确保中文字符正常显示
                            formatted_json = json.dumps(
                                data, 
                                indent=2, 
                                ensure_ascii=False,
                                separators=(',', ': ')
                            )
                            print("查询结果:")
                            print(formatted_json)
                            
                        except json.JSONDecodeError as json_err:
                            print("响应不是有效的JSON:")
                            print(f"JSON解析错误: {json_err}")
                            # 确保文本内容正确显示
                            if isinstance(content.text, bytes):
                                display_text = content.text.decode('utf-8', errors='replace')
                            else:
                                display_text = str(content.text)
                            print("原始响应内容:")
                            print(display_text)
                    else:
                        print(f"收到非文本响应: {type(content)}")
                        print(f"内容: {content}")
                else:
                    print("未收到响应或响应为空")
                    print(f"result对象: {result}")

    except Exception as e:
        print(f"连接或执行出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
