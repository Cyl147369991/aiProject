import json

from openai import OpenAI
from typing import List, Dict, Any

# Qwen 嵌入自定义包装器
class QwenEmbeddings:
    def __init__(self, apiKey, baseUrl):
        self.client = OpenAI(
            api_key=apiKey,  # 如果您没有配置环境变量，请在此处用您的API Key进行替换
            base_url=baseUrl,  # 阿里云百炼服务的base_url
        )

    def _get_embedding(self, text: str) -> List[float]:
        completion = self.client.embeddings.create(
            model="text-embedding-v1",
            input=text,
            encoding_format="float"
        )
        jsonstr = completion.model_dump_json()
        # 将c_vectors字符串转为json对象
        embedding_data = json.loads(jsonstr)
        return embedding_data["data"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._get_embedding(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._get_embedding(text)