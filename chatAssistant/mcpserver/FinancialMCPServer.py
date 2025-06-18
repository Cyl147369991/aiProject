import asyncio
import io
import json
import sqlite3
from typing import List

import pandas as pd
from dotenv import load_dotenv
from mcp import types
from mcp.server import Server as McpServer
from mcp.server.stdio import stdio_server
from supabase import create_client
import sys
import os

from openai import OpenAI
# 加载环境变量
load_dotenv()

# Add the parent directory to the path to import QwenEmbeddings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from QwenEmbeddings import QwenEmbeddings

class FinancialMCPServer:
    def __init__(self):
        self.app = McpServer("financial-data-server")
        self.excel_files = {}  # Cache for Excel data

        # 初始化Supabase客户端
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = create_client(self.supabase_url,
                                      self.supabase_key) if self.supabase_url and self.supabase_key else None

        self.setup_handlers()

    def setup_handlers(self):
        """Setup all MCP handlers"""

        @self.app.list_resources()
        async def list_resources() -> List[types.Resource]:
            """List available financial data resources"""
            return [
                types.Resource(
                    uri="financial://reports/summary",
                    name="Financial Reports Summary",
                    description="Overview of all available financial reports",
                    mimeType="application/json"
                ),
                # Supabase资源
                types.Resource(
                    uri="supabase://documents",
                    name="Supabase Documents",
                    description="Document embeddings stored in Supabase",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="supabase://financial-data",
                    name="Financial Data in Supabase",
                    description="Financial records stored in Supabase database",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="financial://database/schema",
                    name="Sales Database Schema",
                    description="Database tables and column information",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="financial://reports/balance-sheet",
                    name="Balance Sheet Data",
                    description="Latest balance sheet information",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="financial://reports/income-statement",
                    name="Income Statement Data",
                    description="Profit and loss information",
                    mimeType="application/json"
                )
            ]

        @self.app.read_resource()
        async def read_resource(uri: str) -> str:
            """Read financial data resources"""
            try:
                if uri == "financial://reports/summary":
                    return await self.get_reports_summary()
                elif uri == "financial://database/schema":
                    return await self.get_database_schema()
                elif uri == "financial://reports/balance-sheet":
                    return await self.get_balance_sheet_data()
                elif uri == "financial://reports/income-statement":
                    return await self.get_income_statement_data()
                # 处理Supabase资源
                elif uri == "supabase://documents":
                    return await self.get_supabase_documents()
                elif uri == "supabase://financial-data":
                    return await self.get_supabase_financial_data()
                else:
                    return json.dumps({"error": "Resource not found"})
            except Exception as e:
                return json.dumps({"error": str(e)})

        # 其余代码保持不变...
        @self.app.list_tools()
        async def list_tools() -> List[types.Tool]:
            """Define available financial analysis tools"""
            tools = [
                types.Tool(
                    name="query_financial_data",
                    description="Query financial reports using natural language. Can analyze Excel reports, calculate ratios, trends, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language question about financial data"
                            },
                            "report_type": {
                                "type": "string",
                                "enum": ["balance_sheet", "income_statement", "cash_flow", "all"],
                                "description": "Which financial report to analyze"
                            },
                            "time_period": {
                                "type": "string",
                                "description": "Time period for analysis (e.g., 'Q1 2024', 'last 3 months')"
                            }
                        },
                        "required": ["question"]
                    }
                ),
                types.Tool(
                    name="query_sales_data",
                    description="Query sales orders database using natural language. Can filter by date, customer, product, region, etc.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language question about sales data"
                            },
                            "date_range": {
                                "type": "string",
                                "description": "Date range for sales analysis"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional filters (customer, product, region, etc.)"
                            }
                        },
                        "required": ["question"]
                    }
                ),
                types.Tool(
                    name="generate_financial_report",
                    description="Generate custom financial analysis reports combining Excel and database data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "report_request": {
                                "type": "string",
                                "description": "Description of the desired report"
                            },
                            "include_charts": {
                                "type": "boolean",
                                "default": False,
                                "description": "Whether to include chart descriptions"
                            }
                        },
                        "required": ["report_request"]
                    }
                ),
                types.Tool(
                    name="compare_periods",
                    description="Compare financial or sales data across different time periods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric": {
                                "type": "string",
                                "description": "What to compare (revenue, profit, sales volume, etc.)"
                            },
                            "periods": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Time periods to compare"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["absolute", "percentage", "trend"],
                                "default": "percentage"
                            }
                        },
                        "required": ["metric", "periods"]
                    }
                ),
                # 添加Supabase查询工具
                types.Tool(
                    name="query_supabase_data",
                    description="Query data from Supabase database using natural language",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language question about Supabase data"
                            },
                            "table": {
                                "type": "string",
                                "description": "Specific table to query in Supabase"
                            }
                        },
                        "required": ["question"]
                    }
                ),
                # 添加一个简单的测试工具
                types.Tool(
                    name="test_tool",
                    description="A simple test tool to verify MCP connection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Test message"
                            }
                        },
                        "required": ["message"]
                    }
                ),
                # 添加演示工具和资源联系的工具
                types.Tool(
                    name="get_resource_summary",
                    description="演示工具如何访问资源数据 - 获取所有可用资源的摘要信息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_details": {
                                "type": "boolean",
                                "default": True,
                                "description": "是否包含详细信息"
                            }
                        },
                        "required": []
                    }
                )
            ]
            return tools

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[types.TextContent]:
            """Execute financial analysis tools"""
            print(f"=== 收到工具调用请求 ===", file=sys.stderr)
            print(f"工具名称: {name}", file=sys.stderr)
            print(f"参数: {arguments}", file=sys.stderr)
            print(f"========================", file=sys.stderr)
            sys.stderr.flush()
            
            try:
                if name == "query_financial_data":
                    print("执行: query_financial_data", file=sys.stderr)
                    result = await self.query_financial_data(arguments)
                elif name == "query_sales_data":
                    print("执行: query_sales_data", file=sys.stderr)
                    result = await self.query_sales_data(arguments)
                elif name == "generate_financial_report":
                    print("执行: generate_financial_report", file=sys.stderr)
                    result = await self.generate_financial_report(arguments)
                elif name == "compare_periods":
                    print("执行: compare_periods", file=sys.stderr)
                    result = await self.compare_periods(arguments)
                elif name == "query_supabase_data":
                    result = await self.query_supabase_data(arguments)
                elif name == "test_tool":
                    result = await self.test_tool(arguments)
                # 添加一个演示工具和资源联系的工具
                elif name == "get_resource_summary":
                    # 演示：工具内部调用 read_resource 方法
                    print("执行: get_resource_summary - 演示工具调用资源", file=sys.stderr)
                    # 直接调用 read_resource 处理器中使用的方法
                    reports_summary = await self.get_reports_summary()
                    schema_info = await self.get_database_schema()
                    result = {
                        "message": "工具成功调用了资源数据",
                        "reports_summary": json.loads(reports_summary),
                        "database_schema": json.loads(schema_info),
                        "note": "这展示了工具如何访问和资源相同的底层数据"
                    }
                else:
                    print(f"未知工具: {name}", file=sys.stderr)
                    result = {"error": "Unknown tool"}

                print(f"工具执行结果: {result}", file=sys.stderr)
                sys.stderr.flush()
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                print(f"工具执行出错: {str(e)}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    # 添加Supabase相关方法
    async def get_supabase_documents(self) -> str:
        """获取Supabase中存储的文档"""
        try:
            if not self.supabase:
                return json.dumps({"error": "Supabase client not initialized. Check your environment variables."})

            # 从testdoc表获取数据，限制返回前10条记录
            response = self.supabase.table("testdoc").select("id, content, metadata").limit(10).execute()

            if hasattr(response, 'data'):
                return json.dumps({
                    "documents": response.data,
                    "count": len(response.data)
                })
            else:
                return json.dumps({"error": "Failed to fetch documents from Supabase"})
        except Exception as e:
            return json.dumps({"error": f"Error fetching Supabase documents: {str(e)}"})

    async def get_supabase_financial_data(self) -> str:
        """获取Supabase中存储的财务数据"""
        try:
            if not self.supabase:
                return json.dumps({"error": "Supabase client not initialized. Check your environment variables."})

            # 假设财务数据存储在financial_data表中
            response = self.supabase.table("financial_data").select("*").limit(20).execute()

            if hasattr(response, 'data'):
                return json.dumps({
                    "financial_data": response.data,
                    "count": len(response.data)
                })
            else:
                return json.dumps({"error": "Failed to fetch financial data from Supabase"})
        except Exception as e:
            return json.dumps({"error": f"Error fetching financial data: {str(e)}"})

    async def query_supabase_data(self, arguments: dict) -> dict:
        """处理对Supabase数据的自然语言查询"""
        import sys
        question = arguments["question"]
        table = arguments.get("table", "testdoc")  # 默认查询testdoc表
        try:
            if not self.supabase:
                print("Supabase client not initialized!", file=sys.stderr)
                return {"error": "Supabase client not initialized. Check your environment variables."}

            # 这里可以根据问题内容构建更复杂的查询
            # 简单示例：根据问题中的关键词过滤内容
            keywords = question.lower().split()

            # 如果是文档表，可以搜索内容
            if table == "testdoc":
                print("Processing testdoc table query", file=sys.stderr)
                # 首先尝试向量搜索
                try:
                    print("Getting question embedding...", file=sys.stderr)
                    input_embedding = get_qestion_embedding(",".join(keywords))
                    print(f"Embedding result: {input_embedding is not None}", file=sys.stderr)
                    sys.stderr.flush()
                    
                    # 检查是否是假的嵌入向量
                    is_dummy_embedding = (input_embedding and 
                                         len(input_embedding) == 1536 and 
                                         all(x == 0.1 for x in input_embedding))
                    
                    if input_embedding and not is_dummy_embedding:
                        # 调用Supabase的match_documents函数
                        print("Calling Supabase RPC function...", file=sys.stderr)
                        response = self.supabase.rpc(
                            "match_documents",
                            {
                                "query_embedding": input_embedding,
                                "match_threshold": 0.3,  # 可调整的相似度阈值
                                "match_count": 3,
                                "table_name": "testdoc"
                            }
                        ).execute()
                        print(f"Supabase response: {response}", file=sys.stderr)
                        sys.stderr.flush()
                        
                        result = [doc['content'] for doc in response.data]
                        print(f"Extracted content from vector search: {result}", file=sys.stderr)
                        
                        if result:  # 如果向量搜索有结果
                            return {
                                "question1": question,
                                "results": result,
                                "total_matches": len(result),
                                "search_method": "vector_search"
                            }
                    
                except Exception as vector_error:
                    print(f"Vector search failed: {vector_error}", file=sys.stderr)
                
                # 如果向量搜索失败或没有结果，使用简单文本搜索
                print("Falling back to simple text search...", file=sys.stderr)
                try:
                    # 使用 ilike 进行模糊文本搜索
                    search_term = f"%{question}%"
                    response = self.supabase.table(table).select("*").ilike("content", search_term).limit(5).execute()
                    
                    if response.data:
                        result = [doc['content'] for doc in response.data]
                        print(f"Extracted content from text search: {result}", file=sys.stderr)
                        return {
                            "question1": question,
                            "results": result,
                            "total_matches": len(result),
                            "search_method": "text_search"
                        }
                    else:
                        # 如果没有找到匹配的内容，返回一些示例数据
                        print("No matches found, fetching sample data...", file=sys.stderr)
                        response = self.supabase.table(table).select("*").limit(3).execute()
                        if response.data:
                            result = [doc.get('content', str(doc)) for doc in response.data]
                            return {
                                "question1": question,
                                "results": result,
                                "total_matches": len(result),
                                "search_method": "sample_data",
                                "note": "No specific matches found, showing sample data"
                            }
                            
                except Exception as text_search_error:
                    print(f"Text search also failed: {text_search_error}", file=sys.stderr)
                    
                return {
                    "question1": question,
                    "results": [],
                    "total_matches": 0,
                    "error": "Both vector and text search failed"
                }
            else:
                print(f"Processing other table: {table}", file=sys.stderr)
                # 对于其他表，返回前几条记录
                response = self.supabase.table(table).select("*").limit(5).execute()

                if hasattr(response, 'data'):
                    return {
                        "question1": question,
                        "table": table,
                        "results": response.data,
                        "count": len(response.data)
                    }

            return {"error": "No relevant data found"}
        except Exception as e:
            print(f"Error in query_supabase_data: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Error querying Supabase: {str(e)}"}

    # 保留原有方法...
    async def load_excel_data(self, file_path: str, sheet_name: str = None):
        """Load Excel data with caching"""
        cache_key = f"{file_path}:{sheet_name}"
        if cache_key not in self.excel_files:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
            self.excel_files[cache_key] = df
        return self.excel_files[cache_key]

    async def get_reports_summary(self) -> str:
        """Get summary of available financial reports"""
        # Scan for Excel files in reports directory
        reports_dir = "./financial_reports"  # Adjust path
        available_reports = []

        if os.path.exists(reports_dir):
            for file in os.listdir(reports_dir):
                if file.endswith(('.xlsx', '.xls')):
                    # Get basic info about each Excel file
                    try:
                        xl_file = pd.ExcelFile(os.path.join(reports_dir, file))
                        available_reports.append({
                            "filename": file,
                            "sheets": xl_file.sheet_names,
                            "last_modified": os.path.getmtime(os.path.join(reports_dir, file))
                        })
                    except Exception as e:
                        available_reports.append({
                            "filename": file,
                            "error": str(e)
                        })

        return json.dumps({
            "available_reports": available_reports,
            "total_files": len(available_reports)
        })

    async def get_database_schema(self) -> str:
        """Get database schema information from Supabase"""
        if not self.supabase:
            return json.dumps({"error": "Supabase client not initialized. Check your environment variables."})

        try:
            # 查询所有表名
            response = self.supabase.table("information_schema.tables") \
                .select("table_name") \
                .eq("table_schema", "public") \
                .execute()
            tables = [row["table_name"] for row in response.data]

            schema_info = {}
            for table_name in tables:
                # 查询每个表的字段信息
                col_response = self.supabase.table("information_schema.columns") \
                    .select("column_name,data_type,is_nullable") \
                    .eq("table_name", table_name) \
                    .execute()
                schema_info[table_name] = [
                    {
                        "name": col["column_name"],
                        "type": col["data_type"],
                        "nullable": col["is_nullable"] == "YES"
                    }
                    for col in col_response.data
                ]
            return json.dumps(schema_info)
        except Exception as e:
            return json.dumps({"error": f"Error fetching schema from Supabase: {str(e)}"})

    async def query_financial_data(self, arguments: dict) -> dict:
        """Process natural language queries for financial data"""
        question = arguments["question"]
        report_type = arguments.get("report_type", "all")
        time_period = arguments.get("time_period")

        # This is where you'd integrate with an LLM to interpret the question
        # For now, providing a structured approach

        # Example: Load balance sheet data
        try:
            if report_type in ["balance_sheet", "all"]:
                balance_sheet = await self.load_excel_data("./financial_reports/balance_sheet.xlsx")

            # Simple keyword-based analysis (you'd replace this with LLM processing)
            if "revenue" in question.lower():
                # Extract revenue data
                revenue_analysis = await self.analyze_revenue(question, time_period)
                return revenue_analysis
            elif "profit" in question.lower() or "margin" in question.lower():
                profit_analysis = await self.analyze_profitability(question, time_period)
                return profit_analysis
            else:
                return {
                    "question": question,
                    "interpretation": "General financial query",
                    "suggestion": "Please be more specific about what financial metric you'd like to analyze",
                    "available_metrics": ["revenue", "profit", "assets", "liabilities", "cash_flow"]
                }

        except Exception as e:
            return {"error": f"Error processing financial query: {str(e)}"}

    async def query_sales_data(self, arguments: dict) -> dict:
        """Process natural language queries for sales data (Supabase version)"""
        question = arguments["question"]
        date_range = arguments.get("date_range")
        filters = arguments.get("filters", {})

        if not self.supabase:
            return {"error": "Supabase client not initialized. Check your environment variables."}

        try:
            query = self.supabase.table("sales_orders").select("*")
            # 处理日期范围
            if date_range:
                # 假设 date_range 是 "2023-01-01,2023-12-31"
                if "," in date_range:
                    start, end = date_range.split(",")
                    query = query.gte("order_date", start).lte("order_date", end)
                else:
                    query = query.gte("order_date", date_range)
            # 处理其他过滤条件
            for key, value in filters.items():
                query = query.eq(key, value)
            response = query.execute()
            df = pd.DataFrame(response.data)

            # 分析逻辑
            if not df.empty:
                if "top" in question.lower() and "customer" in question.lower():
                    if 'customer_name' in df.columns and 'total_amount' in df.columns:
                        top_customers = df.groupby('customer_name')['total_amount'].sum().sort_values(ascending=False).head(10)
                        return {
                            "question": question,
                            "analysis": "Top customers by sales volume",
                            "results": top_customers.to_dict()
                        }
                elif "monthly" in question.lower() or "trend" in question.lower():
                    if 'order_date' in df.columns and 'total_amount' in df.columns:
                        monthly_sales = df.groupby(pd.to_datetime(df['order_date']).dt.to_period('M'))['total_amount'].sum()
                        return {
                            "question": question,
                            "analysis": "Monthly sales trend",
                            "results": {str(k): float(v) for k, v in monthly_sales.items()}
                        }
                return {
                    "question": question,
                    "total_records": len(df),
                    "total_sales": float(df['total_amount'].sum()) if 'total_amount' in df.columns else "N/A",
                    "date_range": f"{df['order_date'].min()} to {df['order_date'].max()}" if 'order_date' in df.columns else "N/A"
                }
            else:
                return {
                    "question": question,
                    "total_records": 0,
                    "total_sales": 0,
                    "date_range": "N/A",
                    "note": "No records found for the given query."
                }
        except Exception as e:
            return {"error": f"Error querying sales data from Supabase: {str(e)}"}

    async def generate_financial_report(self, arguments: dict) -> dict:
        """Generate custom financial reports"""
        report_request = arguments["report_request"]
        include_charts = arguments.get("include_charts", False)

        # This would integrate with an LLM to understand the report request
        # and generate appropriate analysis

        return {
            "report_request": report_request,
            "status": "Report generation would be implemented here",
            "next_steps": [
                "Parse report requirements using LLM",
                "Query relevant data sources",
                "Perform calculations and analysis",
                "Format results as requested"
            ]
        }

    async def compare_periods(self, arguments: dict) -> dict:
        """Compare data across time periods"""
        metric = arguments["metric"]
        periods = arguments["periods"]
        analysis_type = arguments.get("analysis_type", "percentage")

        return {
            "metric": metric,
            "periods": periods,
            "analysis_type": analysis_type,
            "status": "Period comparison would be implemented here"
        }

    async def analyze_revenue(self, question: str, time_period: str = None) -> dict:
        """Analyze revenue-related questions"""
        # Placeholder for revenue analysis logic
        return {
            "analysis_type": "Revenue Analysis",
            "question": question,
            "time_period": time_period,
            "results": "Revenue analysis results would be calculated here"
        }

    async def analyze_profitability(self, question: str, time_period: str = None) -> dict:
        """Analyze profitability-related questions"""
        # Placeholder for profitability analysis logic
        return {
            "analysis_type": "Profitability Analysis",
            "question": question,
            "time_period": time_period,
            "results": "Profitability analysis results would be calculated here"
        }

    async def get_balance_sheet_data(self) -> str:
        """Get latest balance sheet data"""
        try:
            df = await self.load_excel_data("./financial_reports/balance_sheet.xlsx")
            return df.to_json(orient='records')
        except Exception as e:
            return json.dumps({"error": f"Could not load balance sheet: {str(e)}"})

    async def get_income_statement_data(self) -> str:
        """Get latest income statement data"""
        try:
            df = await self.load_excel_data("./financial_reports/income_statement.xlsx")
            return df.to_json(orient='records')
        except Exception as e:
            return json.dumps({"error": f"Could not load income statement: {str(e)}"})

    async def test_tool(self, arguments: dict) -> dict:
        """A simple test tool to verify MCP connection"""
        message = arguments["message"]
        return {
            "message": message,
            "status": "Test tool executed successfully"
        }

    # 添加演示方法：展示资源和工具的数据共享
    async def get_resource_data_for_tool(self, resource_uri: str) -> dict:
        """
        演示方法：工具如何访问资源数据
        这是连接 read_resource 和 call_tool 的桥梁方法
        """
        try:
            # 模拟调用 read_resource 的逻辑
            if resource_uri == "financial://reports/summary":
                data = await self.get_reports_summary()
            elif resource_uri == "financial://database/schema":
                data = await self.get_database_schema()
            elif resource_uri == "financial://reports/balance-sheet":
                data = await self.get_balance_sheet_data()
            elif resource_uri == "supabase://documents":
                data = await self.get_supabase_documents()
            else:
                return {"error": "Unknown resource URI"}
            
            return {"data": json.loads(data), "source": resource_uri}
        except Exception as e:
            return {"error": f"Failed to get resource data: {str(e)}"}

    # 改进的工具方法，展示如何使用资源数据
    async def enhanced_financial_analysis(self, arguments: dict) -> dict:
        """
        增强的财务分析工具，展示如何结合多个资源的数据
        """
        analysis_type = arguments.get("analysis_type", "comprehensive")
        
        # 通过资源获取基础数据
        reports_data = await self.get_resource_data_for_tool("financial://reports/summary")
        schema_data = await self.get_resource_data_for_tool("financial://database/schema")
        
        # 基于资源数据进行分析
        analysis_result = {
            "analysis_type": analysis_type,
            "data_sources": [
                {"uri": "financial://reports/summary", "status": "loaded" if "error" not in reports_data else "error"},
                {"uri": "financial://database/schema", "status": "loaded" if "error" not in schema_data else "error"}
            ],
            "insights": [],
            "methodology": "Tool accessed multiple resources to provide comprehensive analysis"
        }
        
        # 基于获取的资源数据生成洞察
        if "error" not in reports_data:
            reports_info = reports_data["data"]
            if "available_reports" in reports_info:
                analysis_result["insights"].append(f"Found {reports_info['total_files']} financial reports available")
        
        if "error" not in schema_data:
            schema_info = schema_data["data"]
            table_count = len(schema_info) if isinstance(schema_info, dict) else 0
            analysis_result["insights"].append(f"Database contains {table_count} tables for analysis")
        
        return analysis_result


def get_qestion_embedding(question):
    """获取问题的嵌入向量"""
    try:
        # 初始化嵌入模型
        api_key = os.getenv("TEXT-EMBEDDING-V1_KEY")
        if not api_key:
            print("TEXT-EMBEDDING-V1_KEY not found, using dummy embedding", file=sys.stderr)
            return [0.1] * 1536
            
        embeddings = QwenEmbeddings(api_key, "https://dashscope.aliyuncs.com/compatible-mode/v1")
        # 初始化向量存储
        question_embedding = embeddings._get_embedding(question)
        return question_embedding
    except Exception as e:
        print(f"Error in get_qestion_embedding: {e}", file=sys.stderr)
        # 返回假的嵌入向量作为备选
        return [0.1] * 1536

# Server startup
async def main():
    print("启动 Financial MCP 服务器...")
    server = FinancialMCPServer()
    print("服务器实例创建完成")

    # Run the MCP server
    print("开始监听 stdio 连接...")
    async with stdio_server() as (read_stream, write_stream):
        print("stdio 服务器已准备就绪，开始运行 MCP 应用...")
        await server.app.run(
            read_stream,
            write_stream,
            server.app.create_initialization_options()
        )


if __name__ == "__main__":
    print("=== Financial MCP Server 启动 ===")
    asyncio.run(main())
