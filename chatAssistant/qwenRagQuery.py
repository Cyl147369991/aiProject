import json
import os
import sys
import time
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
from QwenEmbeddings import QwenEmbeddings

# 修复导入 - 使用绝对导入而不是相对导入
try:
    from config import config
except ImportError:
    # 如果导入失败，创建一个默认的 config 对象
    config = {
        "model": "qwen-omni-turbo",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "port": 8000,
    }

load_dotenv()

# 设置环境变量
supabase = create_client(os.getenv("SUPABASE_URL"),
                         os.getenv("SUPABASE_KEY"))

# 初始化客户端和模型
def get_qestion_embedding(question):
    print("qestion=====", question,file=sys.stderr)
    sys.stderr.flush()
    # 初始化嵌入模型
    embeddings = QwenEmbeddings(os.getenv("TEXT-EMBEDDING-V1_KEY"), "https://dashscope.aliyuncs.com/compatible-mode/v1")
    # 初始化向量存储
    question_embedding = embeddings._get_embedding(question)
    return question_embedding


def retrieve_documents(question: str, top_k: int = 5) -> list[str]:
    # 获取问题嵌入
    input_embedding = get_qestion_embedding(question)
    # 调用Supabase的match_documents函数
    response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": input_embedding,
            "match_threshold": 0.3,  # 可调整的相似度阈值
            "match_count": top_k,
            "table_name": "testdoc"
        }
    ).execute()

    # 提取文本内容
    return [doc['content'] for doc in response.data]


def build_context(documents: list[str], his) -> list:
    messages = []
    textArr = []
    messages = messages + his
    for document in documents:
        docs = {"type": "text", "text": document}
        textArr.append(docs)
    if len(textArr) > 0:
        messages.append({"role": "user", "content": textArr})
    return messages



if __name__ == "__main__":
    start_time = time.time()

    # 测试不同的问题
    test_questions = [
        "evancheng是谁?",
        "北京今天天气怎么样？",
        "上海明天的天气如何？",
        "我刚才问了什么？"
    ]

    his = []
    # for question in test_questions:
    #     print(f"\n问题: {question}")
    #     completion = answer_question(question, his, top_k=3)
    #
    #     full_response = ""
    #     for chunk in completion:
    #         if chunk.choices:
    #             delta = chunk.choices[0].delta
    #             if hasattr(delta, "audio"):
    #                 transcript = delta.audio.get("transcript", "")
    #                 if transcript:
    #                     full_response += transcript
    #
    #     print(f"回答: {full_response}")
    #
    #     # 更新历史对话
    #     his.append({"role": "user", "content": question})
    #     his.append({"role": "assistant", "content": full_response})
    #
    # endtime = time.time()
    # time_diff = round(endtime - start_time, 2)
    # print(f"总耗时: {time_diff}秒")
    #     for doc in result["source_documents"]:
    #         print(f"- {doc.metadata['source']}")
    # 测试天气
    # weth = WeatherService()
    # data = weth.get_weather("深圳", "forecast")
    # print(data)
    # jsonstr = "{\"intent\": \"weather\", \"transcription\": \"深圳今天天气怎么样？\", \"entities\": {\"location\": \"深圳\", \"time\": \"今天\"}, \"confidence\": 0.95}"
    # jsondata = json.loads(jsonstr.replace("\\", ""))
    # print(jsondata)
   
    