"""
API 라우터: AI 에이전트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import uuid

from ...agents.orchestrator import SecureFinancialAgent
from ...security.auth import AuthService
from ...security.audit import AuditLogger
from ...api.routes.auth import oauth2_scheme

router = APIRouter()
auth_service = AuthService()
audit_logger = AuditLogger()
agent = SecureFinancialAgent()


class AgentQuery(BaseModel):
    query: str
    session_id: Optional[str] = None
    context: Optional[dict] = None


class AgentResponse(BaseModel):
    response: str
    risk_level: str
    requires_approval: bool
    session_id: str
    audit_trail: list


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """현재 사용자 정보 조회"""
    try:
        payload = auth_service.verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰"
            )
        return {"user_id": user_id}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 실패"
        )


@router.post("/query", response_model=AgentResponse)
async def query_agent(
    query_data: AgentQuery,
    current_user: dict = Depends(get_current_user)
):
    """
    AI 에이전트에 질의
    
    - **query**: 질문 내용
    - **session_id**: 세션 ID (선택사항, 없으면 자동 생성)
    - **context**: 추가 컨텍스트 (선택사항)
    """
    user_id = current_user["user_id"]
    session_id = query_data.session_id or str(uuid.uuid4())
    
    try:
        # 에이전트 실행
        result = await agent.run(
            user_query=query_data.query,
            user_id=user_id,
            session_id=session_id
        )
        
        # 감사 로그
        await audit_logger.log_agent_action(
            user_id=user_id,
            session_id=session_id,
            action="query_agent",
            details={
                "query": query_data.query,
                "risk_level": result["risk_level"]
            }
        )
        
        return AgentResponse(
            response=result["response"],
            risk_level=result["risk_level"],
            requires_approval=result["requires_approval"],
            session_id=session_id,
            audit_trail=result["audit_trail"]
        )
        
    except Exception as e:
        await audit_logger.log_security_event(
            event_type="ERROR",
            user_id=user_id,
            action="query_agent_failed",
            resource="agent",
            status="failure",
            details={"error": str(e)}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="에이전트 처리 중 오류가 발생했습니다"
        )


@router.post("/approve/{session_id}")
async def approve_action(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    고위험 작업 승인
    
    - **session_id**: 승인할 세션 ID
    """
    user_id = current_user["user_id"]
    
    # 실제로는 세션 정보를 조회하고 승인 처리
    
    await audit_logger.log_security_event(
        event_type="APPROVAL",
        user_id=user_id,
        action="approve_high_risk_action",
        resource=f"session:{session_id}",
        status="approved",
        details={"session_id": session_id}
    )
    
    return {
        "message": "작업이 승인되었습니다",
        "session_id": session_id
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    세션 정보 조회
    
    - **session_id**: 조회할 세션 ID
    """
    user_id = current_user["user_id"]
    
    # 실제로는 데이터베이스에서 세션 정보 조회
    
    return {
        "session_id": session_id,
        "user_id": user_id,
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z"
    }
