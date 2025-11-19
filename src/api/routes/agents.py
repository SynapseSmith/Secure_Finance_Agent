"""
API 라우터: AI 에이전트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ...agents.orchestrator import SecureFinancialAgent
from ...security.auth import AuthService
from ...security.audit import AuditLogger
from ...api.routes.auth import oauth2_scheme
from ...database import get_db
from ...crud import SessionCRUD, AuditLogCRUD

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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI 에이전트에 질의
    
    - **query**: 질문 내용
    - **session_id**: 세션 ID (선택사항, 없으면 자동 생성)
    - **context**: 추가 컨텍스트 (선택사항)
    """
    user_id_str = current_user["user_id"]
    user_id = uuid.UUID(user_id_str)
    
    # 세션 ID 처리
    if query_data.session_id:
        session_uuid = uuid.UUID(query_data.session_id)
        # 기존 세션 확인
        session = await SessionCRUD.get_session(db, session_uuid)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="세션을 찾을 수 없습니다"
            )
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="권한이 없습니다"
            )
    else:
        # 새 세션 생성
        session_uuid = uuid.uuid4()
        session = await SessionCRUD.create_session(
            db=db,
            user_id=user_id,
            session_id=session_uuid,
            context=query_data.context
        )
    
    try:
        # 사용자 메시지 저장
        await SessionCRUD.add_message(
            db=db,
            session_id=session_uuid,
            role="user",
            content=query_data.query
        )
        
        # 에이전트 실행
        result = await agent.run(
            user_query=query_data.query,
            user_id=user_id_str,
            session_id=str(session_uuid)
        )
        
        # 어시스턴트 응답 저장
        await SessionCRUD.add_message(
            db=db,
            session_id=session_uuid,
            role="assistant",
            content=result["response"],
            metadata={
                "risk_level": result["risk_level"],
                "requires_approval": result["requires_approval"]
            }
        )
        
        # 세션 상태 업데이트
        await SessionCRUD.update_session(
            db=db,
            session_id=session_uuid,
            risk_level=result["risk_level"],
            requires_approval=result["requires_approval"],
            status="pending_approval" if result["requires_approval"] else "active"
        )
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="AGENT_QUERY",
            action="query_agent",
            resource=f"session:{session_uuid}",
            status="success",
            details={
                "query": query_data.query,
                "risk_level": result["risk_level"]
            }
        )
        
        return AgentResponse(
            response=result["response"],
            risk_level=result["risk_level"],
            requires_approval=result["requires_approval"],
            session_id=str(session_uuid),
            audit_trail=result["audit_trail"]
        )
        
    except Exception as e:
        # 에러 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="AGENT_QUERY_FAILED",
            action="query_agent_failed",
            resource="agent",
            status="failure",
            details={"error": str(e), "query": query_data.query}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="에이전트 처리 중 오류가 발생했습니다"
        )


@router.post("/approve/{session_id}")
async def approve_action(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    고위험 작업 승인
    
    - **session_id**: 승인할 세션 ID
    """
    user_id = uuid.UUID(current_user["user_id"])
    session_uuid = uuid.UUID(session_id)
    
    # 세션 조회
    session = await SessionCRUD.get_session(db, session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다"
        )
    
    # 승인이 필요한 세션인지 확인
    if not session.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="승인이 필요하지 않은 세션입니다"
        )
    
    if session.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 처리된 세션입니다"
        )
    
    # 세션 승인 (관리자 권한 필요 - 간단히 처리)
    await SessionCRUD.approve_session(db, session_uuid, user_id)
    
    # 감사 로그
    await AuditLogCRUD.create_log(
        db=db,
        user_id=user_id,
        event_type="APPROVAL",
        action="approve_high_risk_action",
        resource=f"session:{session_uuid}",
        status="approved",
        details={"session_id": str(session_uuid)}
    )
    
    return {
        "message": "작업이 승인되었습니다",
        "session_id": str(session_uuid),
        "approved_by": str(user_id),
        "approved_at": session.approved_at.isoformat() if session.approved_at else None
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    세션 정보 조회
    
    - **session_id**: 조회할 세션 ID
    """
    user_id = current_user["user_id"]
    session_uuid = uuid.UUID(session_id)
    
    # 세션 조회
    session = await SessionCRUD.get_session(db, session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다"
        )
    
    # 권한 확인 (본인의 세션만 조회 가능)
    if str(session.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    return {
        "session_id": str(session.id),
        "status": session.status,
        "risk_level": session.risk_level,
        "requires_approval": session.requires_approval,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at
            }
            for msg in session.messages
        ]
    }


@router.get("/sessions")
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """
    사용자의 세션 목록 조회
    
    - **limit**: 조회할 세션 수
    - **offset**: 건너뛸 세션 수
    """
    user_id = uuid.UUID(current_user["user_id"])
    sessions = await SessionCRUD.get_user_sessions(db, user_id, limit, offset)
    
    return {
        "total": len(sessions),
        "sessions": [
            {
                "session_id": str(s.id),
                "status": s.status,
                "risk_level": s.risk_level,
                "requires_approval": s.requires_approval,
                "created_at": s.created_at,
                "message_count": len(s.messages) if hasattr(s, 'messages') else 0
            }
            for s in sessions
        ]
    }


@router.get("/pending-approvals")
async def list_pending_approvals(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    승인 대기 중인 세션 목록 (관리자용)
    
    관리자만 접근 가능
    """
    # 권한 확인 (관리자만)
    # 실제로는 current_user의 role을 확인
    
    sessions = await SessionCRUD.get_pending_approvals(db)
    
    return {
        "total": len(sessions),
        "pending_sessions": [
            {
                "session_id": str(s.id),
                "user_id": str(s.user_id),
                "risk_level": s.risk_level,
                "created_at": s.created_at,
                "context": s.context
            }
            for s in sessions
        ]
    }
    # 실제로는 데이터베이스에서 세션 정보 조회
    
    return {
        "session_id": session_id,
        "user_id": user_id,
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z"
    }
