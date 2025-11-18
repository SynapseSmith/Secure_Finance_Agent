"""
보안 미들웨어
요청/응답 필터링 및 보안 헤더 추가
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import structlog
from collections import defaultdict
from datetime import datetime, timedelta

from ..config import settings

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 추가 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """속도 제한 미들웨어"""
    
    def __init__(self, app, rate_limit: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit  # 분당 요청 수
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        
        # 현재 시간
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # 오래된 요청 제거
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_ago
        ]
        
        # 요청 수 확인
        if len(self.requests[client_ip]) >= self.rate_limit:
            logger.warning(
                "속도 제한 초과",
                client_ip=client_ip,
                request_count=len(self.requests[client_ip])
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}
            )
        
        # 요청 기록
        self.requests[client_ip].append(now)
        
        response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청 로깅 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 요청 정보
        client_ip = request.client.host if request.client else "unknown"
        
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.url.path,
            client_ip=client_ip
        )
        
        response = await call_next(request)
        
        # 응답 시간 계산
        process_time = time.time() - start_time
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API 키 검증 미들웨어"""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 제외 경로 체크
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # API 키 확인
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "API 키가 필요합니다"}
            )
        
        # API 키 검증 (실제로는 데이터베이스에서 확인)
        # if not await self.validate_api_key(api_key):
        #     return JSONResponse(
        #         status_code=401,
        #         content={"detail": "유효하지 않은 API 키"}
        #     )
        
        return await call_next(request)
