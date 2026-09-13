import os

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()


def verify_api_key(x_api_key: str = Header(...)):
    expected = os.environ["CHAT_API_KEY"]
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
