from dotenv.main import logger
import redis
import json
import logging
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()

logger = logging.getLogger(__name__)

r = redis.from_url(os.getenv("REDIS_URL"))

SESSION_TTL = 3600 # 1 hour - conversation history
PREFS_TTL = 604800 # 7 days - user preferences
MAX_MESSAGES = 100 # max messages per session

def save_message(session_id: str, role: str, content: str):
    try:
        key = f"session: {session_id}: message"
        message = json.dumps({"role": role, "content": content})
        r.rpush(key, message)
        r.ltrim(key, -MAX_MESSAGES, -1)
        r.expire(key, SESSION_TTL)
    except redis.RedisError as e:
        logger.warning(f"Redis save_message failed: {e}")

def get_messages(session_id: str) -> list:
    try:
        key = f"session:{session_id}:messages"
        raw = r.lrange(key, 0, -1)
        return [json.loads(m.decode() if isinstance(m, bytes) else m) for m in raw]
    except redis.RedisError as e:
        logger.warning(f"Redis get_messages failed: {e}")
    
def save_user_address(session_id: str, address: str):
    try:
        key = f"session:{session_id}:address"
        r.set(key, address, ex=PREFS_TTL)
    except redis.RedisError as e:
        logger.warning(f"Redis save_user_address failed: {e}")

def get_user_address(session_id: str) -> Optional[str]:
    try:
        key = f"session:{session_id}:address"
        val = r.get(key)
        return val.decode() if val else None
    except redis.RedisError as e:
        logger.warning(f"Redis get_user_address failed: {e}")
        return None

def clear_session(session_id: str):
    try:
        for key in r.scan_iter(f"session:{session_id}:*"):
            r.delete(key)
    except redis.RedisError as e:
        logger.warning(f"Redis clear_session failed: {e}")