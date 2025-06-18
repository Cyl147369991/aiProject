import asyncio
import json
import os
from typing import List, Dict, Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp import types
from mcp.client.stdio import stdio_client


class FinancialMCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.resources = []
        self.tools = []
        self.server_params = None

    async def connect(self, server_script_path: str = "mcpserver/financial_mcp_server.py"):
        """连接到MCP服务器"""
        # 设置服务器参数
        self.server_params = StdioServerParameters(
            command="python",
            args=[server_script_path]
        )

        # 连接到服务器
        async with stdio_client(self.server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()
                print("成功连接到Financial MCP服务器")

                # 初始化时获取可用资源和工具
                await self.refresh_resources()
                await self.refresh_tools()

    async def refresh_resources(self):
        """获取服务器上可用的资源列表"""
        if self.session:
            try:
                self.resources = await self.session.list_resources()
                print(f"发现 {len(self.resources)} 个可用资源:")
                for resource in self.resources:
                    print(f"  - {resource.name}: {resource.uri} ({resource.description})")
            except Exception as e:
                print(f"获取资源列表失败: {str(e)}")

    async def refresh_tools(self):
        """获取服务器上可用的工具列表"""
        if self.session:
            try:
                self.tools = await self.session.list_tools()
                print(f"发现 {len(self.tools)} 个可用工具:")
                for tool in self.tools:
                    print(f"  - {tool.name}: {tool.description}")
            except Exception as e:
                print(f"获取工具列表失败: {str(e)}")

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """读取指定URI的资源内容"""
        if not self.session:
            return {"error": "未连接到服务器"}

        try:
            content = await self.session.read_resource(uri)
            return json.loads(content)
        except Exception as e:
            print(f"读取资源 {uri} 时出错: {str(e)}")
            return {"error": str(e)}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """调用指定的工具"""
        if not self.session:
            return [{"error": "未连接到服务器"}]

        try:
            result = await self.session.call_tool(tool_name, arguments)
            parsed_results = []
            print("result:", result)
            for content in result:
                if hasattr(content, 'type') and content.type == "text":
                    try:
                        parsed_results.append(json.loads(content.text))
                    except:
                        parsed_results.append({"text": content.text})
                else:
                    parsed_results.append({"content_type": str(type(content)), "data": str(content)})

            return parsed_results
        except Exception as e:
            print(f"调用工具 {tool_name} 时出错: {str(e)}")
            return [{"error": str(e)}]

    def find_resource_by_name(self, name: str) -> Optional[types.Resource]:
        """通过名称查找资源"""
        for resource in self.resources:
            if name.lower() in resource.name.lower():
                return resource
        return None

    def find_tool_by_name(self, name: str) -> Optional[types.Tool]:
        """通过名称查找工具"""
        for tool in self.tools:
            if name.lower() in tool.name.lower():
                return tool
        return None

    async def query_supabase_data(self, question: str, table: str = "testdoc") -> Dict[str, Any]:
        """使用自然语言查询Supabase数据"""
        arguments = {
            "question": question,
            "table": table
        }
        results = await self.call_tool("query_supabase_data", arguments)
        return results[0] if results else {"error": "查询未返回结果"}

    async def query_financial_data(self, question: str, report_type: str = "all", time_period: str = None) -> Dict[
        str, Any]:
        """使用自然语言查询财务数据"""
        arguments = {
            "question": question,
            "report_type": report_type
        }
        if time_period:
            arguments["time_period"] = time_period

        results = await self.call_tool("query_financial_data", arguments)
        return results[0] if results else {"error": "查询未返回结果"}

    async def generate_report(self, report_request: str, include_charts: bool = False) -> Dict[str, Any]:
        """生成自定义财务报告"""
        arguments = {
            "report_request": report_request,
            "include_charts": include_charts
        }
        results = await self.call_tool("generate_financial_report", arguments)
        return results[0] if results else {"error": "报告生成失败"}

    async def compare_financial_periods(self, metric: str, periods: List[str], analysis_type: str = "percentage") -> \
    Dict[str, Any]:
        """比较不同时期的财务数据"""
        arguments = {
            "metric": metric,
            "periods": periods,
            "analysis_type": analysis_type
        }
        results = await self.call_tool("compare_periods", arguments)
        return results[0] if results else {"error": "期间比较失败"}

    async def run_with_connection(self, server_script_path: str = "mcpserver/financial_mcp_server.py"):
        """运行客户端并保持连接"""
        self.server_params = StdioServerParameters(
            command="python",
            args=[server_script_path]
        )

        async with stdio_client(self.server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                self.session = session
                await session.initialize()
                print("成功连接到Financial MCP服务器")

                # 初始化时获取可用资源和工具
                await self.refresh_resources()
                await self.refresh_tools()

                # 在这里可以执行其他操作
                return self.session


async def interactive_demo():
    """交互式演示客户端功能"""
    client = FinancialMCPClient()

    async with stdio_client(StdioServerParameters(
            command="python",
            args=["../mcpserver/FinancialMCPServer.py"]
    )) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            client.session = session
            await session.initialize()
            print("成功连接到Financial MCP服务器")

            # 初始化时获取可用资源和工具
            await client.refresh_resources()
            await client.refresh_tools()

            while True:
                print("\n===== Financial MCP Client =====")
                print("1. 查看所有资源")
                print("2. 查看所有工具")
                print("3. 读取资源")
                print("4. 查询Supabase数据")
                print("5. 查询财务数据")
                print("6. 生成财务报告")
                print("7. 比较财务期间")
                print("0. 退出")

                choice = input("请选择操作: ")

                if choice == "0":
                    print("退出程序")
                    break

                elif choice == "1":
                    await client.refresh_resources()

                elif choice == "2":
                    await client.refresh_tools()

                elif choice == "3":
                    print("可用资源:")
                    for i, resource in enumerate(client.resources):
                        print(f"{i + 1}. {resource.name} ({resource.uri})")

                    try:
                        resource_idx = int(input("选择资源编号: ")) - 1
                        if 0 <= resource_idx < len(client.resources):
                            uri = client.resources[resource_idx].uri
                            result = await client.read_resource(uri)
                            print(f"\n资源内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
                        else:
                            print("无效的资源编号")
                    except ValueError:
                        print("请输入有效的数字")

                elif choice == "4":
                    question = input("输入查询问题: ")
                    table = input("输入表名 (默认为testdoc): ") or "testdoc"
                    result = await client.query_supabase_data(question, table)
                    print(f"\n查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

                elif choice == "5":
                    question = input("输入财务查询问题: ")
                    report_type = input("报告类型 (balance_sheet/income_statement/cash_flow/all，默认为all): ") or "all"
                    time_period = input("时间段 (可选): ") or None
                    result = await client.query_financial_data(question, report_type, time_period)
                    print(f"\n查询结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

                elif choice == "6":
                    report_request = input("描述所需的报告: ")
                    include_charts = input("是否包含图表 (y/n, 默认为n): ").lower() == "y"
                    result = await client.generate_report(report_request, include_charts)
                    print(f"\n报告结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

                elif choice == "7":
                    metric = input("要比较的指标 (如revenue, profit等): ")
                    periods_str = input("要比较的时期 (用逗号分隔，如'Q1 2023,Q2 2023,Q3 2023'): ")
                    periods = [p.strip() for p in periods_str.split(",")]
                    analysis_type = input("分析类型 (absolute/percentage/trend，默认为percentage): ") or "percentage"
                    result = await client.compare_financial_periods(metric, periods, analysis_type)
                    print(f"\n比较结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

                else:
                    print("无效的选择，请重试")


async def simple_demo():
    """简单演示客户端基本功能"""
    client = FinancialMCPClient()
    # 设置服务器参数 - 修复路径
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建服务器脚本的绝对路径
    server_script_path = os.path.join(os.path.dirname(current_dir), "mcpserver", "FinancialMCPServer.py")
    async with stdio_client(StdioServerParameters(
            command="python",
            args=[server_script_path]
    )) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            client.session = session
            await session.initialize()
            print("成功连接到Financial MCP服务器")

            # 初始化时获取可用资源和工具
            await client.refresh_resources()
            await client.refresh_tools()

            # 读取Supabase文档资源
            print("\n获取Supabase文档:")
            try:
                supabase_docs = await client.read_resource("supabase://documents")
                print(json.dumps(supabase_docs, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"获取Supabase文档失败: {e}")

            # 查询Supabase数据
            print("\n查询Supabase数据:")
            try:
                query_result = await client.query_supabase_data("查找关于财务报表的文档")
                print(json.dumps(query_result, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"查询Supabase数据失败: {e}")

            # 获取财务数据摘要
            print("\n获取财务报告摘要:")
            try:
                summary = await client.read_resource("financial://reports/summary")
                print(json.dumps(summary, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"获取财务报告摘要失败: {e}")

            # 查询财务数据
            print("\n查询财务数据:")
            try:
                financial_query = await client.query_financial_data("分析过去3个月的收入趋势")
                print(json.dumps(financial_query, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"查询财务数据失败: {e}")


if __name__ == "__main__":
    # 选择运行交互式演示或简单演示
    mode = input("选择模式 (1: 交互式演示, 2: 简单演示): ")

    if mode == "1":
        asyncio.run(interactive_demo())
    else:
        asyncio.run(simple_demo())
