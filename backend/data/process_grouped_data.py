import asyncio
import pandas as pd
import aiohttp
from zai import ZaiClient
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize client
client = ZaiClient(api_key=os.getenv("GLM_API_KEY"))

ask = input('问：')

# Create chat completion
response = client.chat.completions.create(
    model='GLM-4.7-Flash',
    messages=[
        {'role': 'system', 'content': 'You are an AI writer.'},
        {'role': 'user', 'content': ask},
    ]
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='')