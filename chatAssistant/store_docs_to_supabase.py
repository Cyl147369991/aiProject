import json
import os

from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from openai import OpenAI
from supabase import create_client
from QwenEmbeddings import QwenEmbeddings

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN-ONMI-TURBO_API_KEY")
embbinding_key = os.getenv("TEXT-EMBEDDING-V1_KEY")

# 初始化客户端
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)


def custom_text_loader(file_path):
    return TextLoader(file_path, encoding="utf-8")


# 文档加载与分块
def load_and_split_docs(dir_path: str = "./documents"):
    loader = DirectoryLoader(dir_path, glob="**/*.txt", loader_cls=custom_text_loader)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    texts = text_splitter.split_documents(documents)
    print("texts:", texts)
    # 转换为适合Supabase存储的格式
    doc_items = []
    for i, text in enumerate(texts):
        doc_items.append({
            "content": text.page_content,
            "metadata": {
                "source": text.metadata.get("source", f"doc_{i}"),
                "page": text.metadata.get("page", 0)
            }
        })

    return doc_items


# 生成嵌入并存储到Supabase
def store_embeddings_to_supabase(docs):
    # 初始化嵌入模型
    embeddings = QwenEmbeddings(embbinding_key, "https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 提取文本内容
    texts = [doc["content"] for doc in docs]

    # 生成嵌入向量
    print(f"正在生成{len(texts)}个文本块的嵌入向量...")
    embedding_json = embeddings.embed_documents(texts)
    # 将embedding_vectors字符串转为json对象
    embedding_data = json.loads(embedding_json)
    # 准备数据批量插入
    data_to_insert = []
    for i, doc in enumerate(docs):
        data_to_insert.append({
            "content": doc["content"],
            "metadata": doc["metadata"],
            "embedding": embedding_data["data"][i]["embedding"]
        })

    # 批量插入到Supabase
    print(f"正在将{len(data_to_insert)}条记录存入Supabase...")
    print("data_to_insert:\n", data_to_insert)
    response = supabase.table("testdoc").insert(data_to_insert).execute()

    if len(response.data) > 0:
        print(f"成功存入{len(response.data)}条记录")
    else:
        print("存入失败:", response.error)


if __name__ == '__main__':
    docs = load_and_split_docs(".")
    print("items:", docs)
    store_embeddings_to_supabase(docs)
