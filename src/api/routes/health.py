"""
API 라우터: 헬스 체크
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()


@router.get("/")
async def health_check():
    """기본 헬스 체크"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "finance-agent-api"
        }
    )


@router.get("/ready")
async def readiness_check():
    """준비 상태 확인 (Kubernetes용)"""
    # 실제로는 데이터베이스, Redis 등 연결 체크
    return JSONResponse(
        status_code=200,
        content={"ready": True}
    )


@router.get("/live")
async def liveness_check():
    """생존 확인 (Kubernetes용)"""
    return JSONResponse(
        status_code=200,
        content={"alive": True}
    )
