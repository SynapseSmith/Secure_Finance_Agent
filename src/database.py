"""
데이터베이스 초기화 및 설정
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import structlog

from .config import settings

logger = structlog.get_logger()

# 비동기 엔진 생성
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG_MODE,
    pool_size=20,
    max_overflow=40,
)

# 세션 팩토리
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def init_db():
    """데이터베이스 초기화"""
    logger.info("데이터베이스 초기화 시작")
    
    async with engine.begin() as conn:
        # pgvector 확장 설치
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("데이터베이스 초기화 완료")


async def get_db() -> AsyncSession:
    """데이터베이스 세션 의존성"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
