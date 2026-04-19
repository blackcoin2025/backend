import os
import json
import logging
import asyncio
from decimal import Decimal
import redis.asyncio as redis
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ========================
# 🔥 LOAD ENV
# ========================
load_dotenv()

# ========================
# 🔥 CONFIG
# ========================
REDIS_URL = os.getenv("REDIS_URL")
REDIS_REQUIRED = os.getenv("REDIS_REQUIRED", "false").lower() == "true"

redis_client: redis.Redis | None = None


# ========================
# 🔥 SERIALIZATION (CRITIQUE)
# ========================
def serialize_data(obj):
    """
    Permet de rendre JSON compatible avec Decimal
    """
    if isinstance(obj, Decimal):
        return float(obj)  # ou str(obj) si précision critique
    raise TypeError(f"Type non supporté: {type(obj)}")


# ========================
# 🔥 INIT REDIS
# ========================
def init_redis():
    global redis_client

    try:
        if REDIS_URL:
            redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
            logger.info("✅ Redis connecté (URL)")

        else:
            redis_client = redis.Redis(
                host="127.0.0.1",
                port=6379,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30,
            )
            logger.warning("⚠️ REDIS_URL absent → fallback localhost")

    except Exception as e:
        redis_client = None
        logger.error(f"❌ Redis init failed: {e}")

        if REDIS_REQUIRED:
            raise RuntimeError("Redis obligatoire mais indisponible")


# ========================
# 🔌 CLOSE REDIS
# ========================
async def close_redis():
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            logger.info("🔌 Redis fermé proprement")
        except Exception as e:
            logger.warning(f"⚠️ Redis close error: {e}")


# init au démarrage
init_redis()


# ========================
# 🔥 HEALTH CHECK
# ========================
async def is_redis_available():
    if not redis_client:
        return False

    try:
        await redis_client.ping()
        return True
    except Exception as e:
        logger.warning(f"⚠️ Redis ping failed: {e}")
        return False


# ========================
# 🔥 SAFE GET
# ========================
async def cache_get(key: str):
    if not redis_client:
        logger.debug(f"MISS (redis off) [{key}]")
        return None

    try:
        data = await redis_client.get(key)

        if not data:
            return None

        try:
            return json.loads(data)
        except Exception:
            logger.error(f"❌ JSON corrompu [{key}]")
            return None

    except Exception as e:
        logger.error(f"❌ Redis GET failed [{key}]: {e}")
        return None


# ========================
# 🔥 SAFE SET
# ========================
async def cache_set(key: str, value, ttl: int = 60):
    if not redis_client:
        return

    try:
        payload = json.dumps(value, default=serialize_data)

        await redis_client.set(
            key,
            payload,
            ex=ttl
        )

    except Exception as e:
        logger.error(f"❌ Redis SET failed [{key}]: {e}")


# ========================
# 🔥 SAFE DELETE
# ========================
async def cache_delete(key: str):
    if not redis_client:
        return

    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"❌ Redis DELETE failed [{key}]: {e}")


# ========================
# 🔒 LOCK (SÉCURISÉ)
# ========================
async def cache_lock(key: str, ttl: int = 5) -> bool:
    """
    Lock distribué SAFE
    """
    if not redis_client:
        logger.error(f"❌ Redis requis pour lock [{key}]")
        return False

    try:
        result = await redis_client.set(key, "1", ex=ttl, nx=True)
        return result is True

    except Exception as e:
        logger.error(f"❌ Redis LOCK failed [{key}]: {e}")
        return False


# ========================
# 🔁 CACHE WRAPPER (ANTI-STAMPEDE)
# ========================
async def cache_or_execute(key: str, ttl: int, callback):
    """
    Pattern PRO avec protection anti stampede
    """

    # 1. cache direct
    cached = await cache_get(key)
    if cached is not None:
        return cached

    # 2. lock
    lock_key = f"lock:cache:{key}"
    got_lock = await cache_lock(lock_key, ttl=3)

    if got_lock:
        try:
            result = await callback()
            await cache_set(key, result, ttl)
            return result
        finally:
            await cache_delete(lock_key)

    # 3. fallback attente
    await asyncio.sleep(0.1)

    return await cache_get(key)