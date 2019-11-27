import logging

from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import MONGODB_URL
from .mongodb import db


async def connect_to_mongo():
    logging.info("[MongoDB] Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(str(MONGODB_URL))
    logging.info("[MongoDB] Successfully connected")


async def close_mongo_connection():
    logging.info("[MongoDB] Closing MongoDB connection...")
    db.client.close()
    logging.info("[MongoDB] Successfully closed MongoDB connection...")