import os
import json
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# ========================
# 🔥 INIT REDIS (PRO)
# ========================
redis_client = None

def init_redis():
    global redis_client

    try:
        redis_url = os.getenv("REDIS_URL")

        if not redis_url:
            logger.warning("⚠️ REDIS_URL not set → cache disabled")
            redis_client = None
            return

        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

        logger.info("✅ Redis client initialized")

    except Exception as e:
        logger.warning(f"⚠️ Redis init failed: {e}")
        redis_client = None


# appeler au démarrage (important)
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
        return None

    try:
        data = await redis_client.get(key)

        if data is None:
            return None

        return json.loads(data)

    except Exception as e:
        logger.warning(f"⚠️ Redis GET error [{key}]: {e}")
        return None


# ========================
# 🔥 SAFE SET
# ========================
async def cache_set(key: str, value, ttl: int = 60):
    if not redis_client:
        return

    try:
        await redis_client.set(
            key,
            json.dumps(value),
            ex=ttl
        )

    except Exception as e:
        logger.warning(f"⚠️ Redis SET error [{key}]: {e}")


# ========================
# 🔥 SAFE DELETE
# ========================
async def cache_delete(key: str):
    if not redis_client:
        return

    try:
        await redis_client.delete(key)

    except Exception as e:
        logger.warning(f"⚠️ Redis DELETE error [{key}]: {e}")


# ========================
# 🔒 LOCK (CRITIQUE)
# ========================
async def cache_lock(key: str, ttl: int = 5) -> bool:
    """
    Empêche double requêtes (anti spam / double click)
    """
    if not redis_client:
        return True  # fallback → autorise (évite blocage total)

    try:
        result = await redis_client.set(key, "1", ex=ttl, nx=True)
        return result is True

    except Exception as e:
        logger.warning(f"⚠️ Redis LOCK error [{key}]: {e}")
        return True  # fallback safe


# ========================
# 🔁 CACHE WRAPPER (PRO)
# ========================
async def cache_or_execute(key: str, ttl: int, callback):
    """
    🔥 Pattern PRO :
    - tente cache
    - sinon exécute
    - stocke
    """

    # 1. cache
    cached = await cache_get(key)
    if cached is not None:
        return cached

    # 2. exécution
    result = await callback()

    # 3. stockage
    await cache_set(key, result, ttl)

    return result