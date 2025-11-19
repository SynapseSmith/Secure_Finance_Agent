"""
Redis 캐시 및 세션 관리
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import structlog
from datetime import timedelta, datetime

from ..config import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis 클라이언트"""
    
    def __init__(self):
        """초기화"""
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Redis 연결"""
        try:
            self.redis = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Redis 연결 성공")
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise
    
    async def disconnect(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis 연결 종료")
    
    async def get(self, key: str) -> Optional[str]:
        """값 조회"""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET 실패 [{key}]: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ):
        """값 저장"""
        try:
            if expire:
                await self.redis.setex(key, expire, value)
            else:
                await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET 실패 [{key}]: {e}")
    
    async def delete(self, key: str):
        """값 삭제"""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE 실패 [{key}]: {e}")
    
    async def exists(self, key: str) -> bool:
        """키 존재 확인"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 실패 [{key}]: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """값 증가"""
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR 실패 [{key}]: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int):
        """만료 시간 설정"""
        try:
            await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE 실패 [{key}]: {e}")


class CacheService:
    """캐시 서비스"""
    
    def __init__(self, redis_client: RedisClient):
        """초기화"""
        self.redis = redis_client
        self.default_ttl = 3600  # 1시간
    
    async def get_json(self, key: str) -> Optional[dict]:
        """JSON 형태로 값 조회"""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"JSON 파싱 실패 [{key}]")
                return None
        return None
    
    async def set_json(
        self,
        key: str,
        value: dict,
        ttl: Optional[int] = None
    ):
        """JSON 형태로 값 저장"""
        try:
            json_value = json.dumps(value)
            await self.redis.set(key, json_value, ttl or self.default_ttl)
        except Exception as e:
            logger.error(f"JSON 저장 실패 [{key}]: {e}")
    
    async def cache_user_data(self, user_id: str, user_data: dict, ttl: int = 1800):
        """사용자 데이터 캐싱 (30분)"""
        key = f"user:{user_id}"
        await self.set_json(key, user_data, ttl)
    
    async def get_cached_user_data(self, user_id: str) -> Optional[dict]:
        """캐시된 사용자 데이터 조회"""
        key = f"user:{user_id}"
        return await self.get_json(key)
    
    async def invalidate_user_cache(self, user_id: str):
        """사용자 캐시 무효화"""
        key = f"user:{user_id}"
        await self.redis.delete(key)
    
    async def cache_session_data(self, session_id: str, session_data: dict, ttl: int = 7200):
        """세션 데이터 캐싱 (2시간)"""
        key = f"session:{session_id}"
        await self.set_json(key, session_data, ttl)
    
    async def get_cached_session_data(self, session_id: str) -> Optional[dict]:
        """캐시된 세션 데이터 조회"""
        key = f"session:{session_id}"
        return await self.get_json(key)
    
    async def invalidate_session_cache(self, session_id: str):
        """세션 캐시 무효화"""
        key = f"session:{session_id}"
        await self.redis.delete(key)


class RateLimitService:
    """속도 제한 서비스"""
    
    def __init__(self, redis_client: RedisClient):
        """초기화"""
        self.redis = redis_client
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int = 60,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        속도 제한 확인
        
        Args:
            identifier: 식별자 (user_id, IP 등)
            limit: 제한 횟수
            window: 시간 창 (초)
        
        Returns:
            (허용 여부, 남은 횟수)
        """
        key = f"ratelimit:{identifier}"
        
        try:
            current = await self.redis.increment(key)
            
            if current == 1:
                # 첫 요청이면 만료 시간 설정
                await self.redis.expire(key, window)
            
            remaining = max(0, limit - current)
            allowed = current <= limit
            
            return allowed, remaining
            
        except Exception as e:
            logger.error(f"속도 제한 확인 실패 [{identifier}]: {e}")
            return True, limit  # 에러 시 허용


class SessionStore:
    """세션 저장소"""
    
    def __init__(self, redis_client: RedisClient):
        """초기화"""
        self.redis = redis_client
        self.session_ttl = 86400  # 24시간
    
    async def create_session(
        self,
        session_id: str,
        user_id: str,
        metadata: Optional[dict] = None
    ):
        """세션 생성"""
        key = f"session_store:{session_id}"
        session_data = {
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": str(datetime.utcnow())
        }
        
        json_data = json.dumps(session_data)
        await self.redis.set(key, json_data, self.session_ttl)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """세션 조회"""
        key = f"session_store:{session_id}"
        value = await self.redis.get(key)
        
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def update_session(
        self,
        session_id: str,
        updates: dict
    ):
        """세션 업데이트"""
        session = await self.get_session(session_id)
        if session:
            session["metadata"].update(updates)
            key = f"session_store:{session_id}"
            json_data = json.dumps(session)
            await self.redis.set(key, json_data, self.session_ttl)
    
    async def delete_session(self, session_id: str):
        """세션 삭제"""
        key = f"session_store:{session_id}"
        await self.redis.delete(key)
    
    async def extend_session(self, session_id: str, ttl: Optional[int] = None):
        """세션 만료 시간 연장"""
        key = f"session_store:{session_id}"
        await self.redis.expire(key, ttl or self.session_ttl)


# 전역 인스턴스
_redis_client: Optional[RedisClient] = None
_cache_service: Optional[CacheService] = None
_rate_limit_service: Optional[RateLimitService] = None
_session_store: Optional[SessionStore] = None


async def init_redis():
    """Redis 초기화"""
    global _redis_client, _cache_service, _rate_limit_service, _session_store
    
    _redis_client = RedisClient()
    await _redis_client.connect()
    
    _cache_service = CacheService(_redis_client)
    _rate_limit_service = RateLimitService(_redis_client)
    _session_store = SessionStore(_redis_client)
    
    logger.info("Redis 서비스 초기화 완료")


async def close_redis():
    """Redis 연결 종료"""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()


def get_redis_client() -> RedisClient:
    """Redis 클라이언트 가져오기"""
    if _redis_client is None:
        raise RuntimeError("Redis가 초기화되지 않았습니다")
    return _redis_client


def get_cache_service() -> CacheService:
    """캐시 서비스 가져오기"""
    if _cache_service is None:
        raise RuntimeError("캐시 서비스가 초기화되지 않았습니다")
    return _cache_service


def get_rate_limit_service() -> RateLimitService:
    """속도 제한 서비스 가져오기"""
    if _rate_limit_service is None:
        raise RuntimeError("속도 제한 서비스가 초기화되지 않았습니다")
    return _rate_limit_service


def get_session_store() -> SessionStore:
    """세션 저장소 가져오기"""
    if _session_store is None:
        raise RuntimeError("세션 저장소가 초기화되지 않았습니다")
    return _session_store
