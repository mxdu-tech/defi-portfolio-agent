import re
import redis
import json
import logging
from datetime import datetime, timezone
from web3 import Web3
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

SESSION_TTL  = 3600    # 1 hour  — conversation history
PREFS_TTL    = 2592000 # 30 days — preferences
MAX_MESSAGES = 100

# ── Helpers ──────────────────────────────────────────────────

def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()

def _normalize_address(address: str) -> str:
    """Validate and normalize to checksum address. Raises ValueError if invalid."""
    if not isinstance(address, str):
        raise ValueError(f"Address must be a string, got {type(address)}")
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address.strip()):
        raise ValueError(f"Invalid Ethereum address format: {address}")
    try:
        return Web3.to_checksum_address(address.strip())
    except Exception as e:
        raise ValueError(f"Checksum failed for {address}: {e}")

def _safe_decode(val) -> any:
    """Decode bytes and attempt JSON parse, fallback to raw string."""
    s = val.decode() if isinstance(val, bytes) else val
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s

# ── Session level ────────────────────────────────────────────

def save_message(session_id: str, role: str, content: str):
    try:
        key = f"session:{session_id}:messages"
        message = json.dumps({
            "role": role,
            "content": content,
            "ts": _now_ts(),
        })
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
        return []

def save_session_address(session_id: str, address: str):
    """Link normalized address to session for quick lookup."""
    try:
        normalized = _normalize_address(address)
        key = f"session:{session_id}:meta"
        r.hset(key, mapping={"address": normalized})
        r.expire(key, SESSION_TTL)
    except ValueError as e:
        logger.warning(f"Invalid address skipped: {e}")
    except redis.RedisError as e:
        logger.warning(f"Redis save_session_address failed: {e}")

def get_user_address(session_id: str) -> Optional[str]:
    """Read address from session meta."""
    try:
        val = r.hget(f"session:{session_id}:meta", "address")
        return val.decode() if val else None
    except redis.RedisError as e:
        logger.warning(f"Redis get_user_address failed: {e}")
        return None

def clear_session(session_id: str):
    """Clear session-level data only. User-level prefs/meta are preserved."""
    try:
        r.delete(
            f"session:{session_id}:messages",
            f"session:{session_id}:meta",
        )
    except redis.RedisError as e:
        logger.warning(f"Redis clear_session failed: {e}")

# ── User level ───────────────────────────────────────────────

def save_user_meta(address: str):
    """Persist user-level identity. first_seen is set once, last_seen always updated."""
    try:
        addr = _normalize_address(address)
        key = f"user:{addr}:meta"
        r.hsetnx(key, "first_seen", _now_ts())  # only set if not exists
        r.hset(key, "last_seen", _now_ts())      # always update
    except ValueError as e:
        logger.warning(f"Invalid address skipped: {e}")
    except redis.RedisError as e:
        logger.warning(f"Redis save_user_meta failed: {e}")

def save_user_prefs(address: str, prefs: dict):
    """Write all prefs as Redis Hash fields."""
    try:
        addr = _normalize_address(address)
        serialized = {k: json.dumps(v) for k, v in prefs.items()}
        r.hset(f"user:{addr}:prefs", mapping=serialized)
    except ValueError as e:
        logger.warning(f"Invalid address skipped: {e}")
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning(f"Redis save_user_prefs failed: {e}")

def get_user_prefs(address: str) -> dict:
    """Read all prefs from Redis Hash."""
    try:
        addr = _normalize_address(address)
        raw = r.hgetall(f"user:{addr}:prefs")
        if not raw:
            return {}
        return {
            (k.decode() if isinstance(k, bytes) else k): _safe_decode(v)
            for k, v in raw.items()
        }
    except ValueError as e:
        logger.warning(f"Invalid address: {e}")
        return {}
    except redis.RedisError as e:
        logger.warning(f"Redis get_user_prefs failed: {e}")
        return {}

def update_user_pref(address: str, field: str, value):
    """Single-field update using Redis Hash — safe under concurrency.
    NOTE: For complex nested values, consider a dedicated key per field.
    """
    try:
        addr = _normalize_address(address)
        serialized = json.dumps(value) if not isinstance(value, str) else value
        r.hset(f"user:{addr}:prefs", field, serialized)
    except ValueError as e:
        logger.warning(f"Invalid address: {e}")
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning(f"Redis update_user_pref failed: {e}")