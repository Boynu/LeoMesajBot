import logging

from pyrogram import Client
import pymongo
from config import API_HASH, API_ID, TOKEN, MONGODB_URI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("log.txt")],
)

mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client.whisper_bot

client = Client(
    "whisper_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TOKEN,
    plugins=dict(root="plugins"),
)


if __name__ == "__main__":
    client.run()
