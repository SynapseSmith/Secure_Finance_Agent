"""
보안 중심 금융 AI 에이전트 시스템
FastAPI 메인 애플리케이션
"""
from contextlib import asynccontextmanager  # 비동기 컨텍스트 관리자
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import structlog

from .config import settings
from .security.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from .security.audit import AuditLogger
from .api.routes import agents, auth, health, documents
from .database import init_db
from .services.redis import init_redis, close_redis

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    # 시작 시
    logger.info("애플리케이션 시작", environment=settings.ENVIRONMENT)
    
    # 데이터베이스 초기화
    await init_db()
    
    # Redis 초기화
    await init_redis()
    
    yield
    
    # 종료 시
    logger.info("애플리케이션 종료")
    await close_redis()


app = FastAPI(
    title="금융 AI 에이전트 시스템",
    description="보안 중심의 엔터프라이즈 AI 에이전트 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

# 보안 미들웨어
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, rate_limit=settings.API_RATE_LIMIT_PER_MINUTE)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS 설정 (엄격하게)
if settings.API_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.API_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,
    )

# 라우터 등록
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])

# Prometheus 메트릭 엔드포인트
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리 및 감사 로깅"""
    audit_logger = AuditLogger()
    
    await audit_logger.log_security_event(
        event_type="ERROR",
        user_id=getattr(request.state, "user_id", "anonymous"),
        action="exception_occurred",
        resource=str(request.url),
        status="failure",
        details={"error": str(exc), "type": type(exc).__name__},
        ip_address=request.client.host if request.client else None,
    )
    
    logger.error("애플리케이션 예외 발생", 
                 error=str(exc), 
                 path=str(request.url),
                 method=request.method)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error" if settings.ENVIRONMENT == "production" else str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
