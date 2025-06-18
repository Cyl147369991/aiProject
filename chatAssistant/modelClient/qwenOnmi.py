from openai import OpenAI
import os
import json

class QwenOnmi:
    def __init__(self,key,baseurl,modelname) -> None:
        self.client = OpenAI(
            api_key=key,
            base_url=baseurl
        )
        self.modelname = modelname
    
    def chat_stream(self,messages,modality:list[str]=["text","audio"]):
        completion = self.client.chat.completions.create(
            model=self.modelname,
            messages=messages,
            modalities=modality,
            audio={"voice": "Chelsie", "format": "wav"},
            stream=True,
            stream_options={"include_usage": True},
        )
        return completion
    
