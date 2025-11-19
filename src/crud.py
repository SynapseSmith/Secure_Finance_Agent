"""
데이터베이스 CRUD 작업
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from .models import (
    User, TokenBlacklist, AgentSession, SessionMessage,
    AuditLog, Document, DocumentChunk, ComplianceCheck
)
from .security.auth import AuthService

auth_service = AuthService()


class UserCRUD:
    """사용자 CRUD"""
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        role: str = "user"
    ) -> User:
        """사용자 생성"""
        hashed_password = auth_service.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """ID로 사용자 조회"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_last_login(db: AsyncSession, user_id: uuid.UUID):
        """마지막 로그인 시간 업데이트"""
        user = await UserCRUD.get_user_by_id(db, user_id)
        if user:
            user.last_login = datetime.utcnow()
            await db.commit()
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """사용자 인증"""
        user = await UserCRUD.get_user_by_email(db, email)
        if not user:
            return None
        if not auth_service.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user


class TokenBlacklistCRUD:
    """토큰 블랙리스트 CRUD"""
    
    @staticmethod
    async def add_token(
        db: AsyncSession,
        token: str,
        user_id: uuid.UUID,
        expires_at: datetime
    ):
        """토큰을 블랙리스트에 추가"""
        blacklist_entry = TokenBlacklist(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(blacklist_entry)
        await db.commit()
    
    @staticmethod
    async def is_token_blacklisted(db: AsyncSession, token: str) -> bool:
        """토큰이 블랙리스트에 있는지 확인"""
        result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.token == token)
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def cleanup_expired_tokens(db: AsyncSession):
        """만료된 토큰 정리"""
        await db.execute(
            select(TokenBlacklist).where(
                TokenBlacklist.expires_at < datetime.utcnow()
            )
        )
        await db.commit()


class SessionCRUD:
    """에이전트 세션 CRUD"""
    
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        context: Optional[dict] = None
    ) -> AgentSession:
        """세션 생성"""
        session = AgentSession(
            id=session_id or uuid.uuid4(),
            user_id=user_id,
            context=context
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: uuid.UUID
    ) -> Optional[AgentSession]:
        """세션 조회"""
        result = await db.execute(
            select(AgentSession)
            .options(selectinload(AgentSession.messages))
            .where(AgentSession.id == session_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        **kwargs
    ):
        """세션 업데이트"""
        session = await SessionCRUD.get_session(db, session_id)
        if session:
            for key, value in kwargs.items():
                setattr(session, key, value)
            session.updated_at = datetime.utcnow()
            await db.commit()
    
    @staticmethod
    async def add_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> SessionMessage:
        """메시지 추가"""
        message = SessionMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    
    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[AgentSession]:
        """사용자의 세션 목록 조회"""
        result = await db.execute(
            select(AgentSession)
            .where(AgentSession.user_id == user_id)
            .order_by(AgentSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_pending_approvals(
        db: AsyncSession,
        limit: int = 50
    ) -> List[AgentSession]:
        """승인 대기 중인 세션 목록"""
        result = await db.execute(
            select(AgentSession)
            .where(
                and_(
                    AgentSession.status == "pending_approval",
                    AgentSession.requires_approval == True
                )
            )
            .order_by(AgentSession.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def approve_session(
        db: AsyncSession,
        session_id: uuid.UUID,
        approver_id: uuid.UUID
    ):
        """세션 승인"""
        session = await SessionCRUD.get_session(db, session_id)
        if session:
            session.status = "active"
            session.approved_by = approver_id
            session.approved_at = datetime.utcnow()
            await db.commit()


class AuditLogCRUD:
    """감사 로그 CRUD"""
    
    @staticmethod
    async def create_log(
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        event_type: str,
        action: str,
        resource: str,
        status: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """감사 로그 생성"""
        log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            action=action,
            resource=resource,
            status=status,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log
    
    @staticmethod
    async def get_user_logs(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """사용자의 감사 로그 조회"""
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_logs_by_event_type(
        db: AsyncSession,
        event_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """이벤트 타입별 로그 조회"""
        query = select(AuditLog).where(AuditLog.event_type == event_type)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()


class DocumentCRUD:
    """문서 CRUD"""
    
    @staticmethod
    async def create_document(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        content: str,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[List[str]] = None
    ) -> Document:
        """문서 생성"""
        document = Document(
            user_id=user_id,
            title=title,
            content=content,
            file_path=file_path,
            file_type=file_type,
            metadata=metadata,
            tags=tags
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document
    
    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: uuid.UUID
    ) -> Optional[Document]:
        """문서 조회"""
        result = await db.execute(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_documents(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Document]:
        """사용자의 문서 목록"""
        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_document_status(
        db: AsyncSession,
        document_id: uuid.UUID,
        status: str
    ):
        """문서 상태 업데이트"""
        document = await DocumentCRUD.get_document(db, document_id)
        if document:
            document.status = status
            if status == "completed":
                document.processed_at = datetime.utcnow()
            await db.commit()
    
    @staticmethod
    async def create_chunk(
        db: AsyncSession,
        document_id: uuid.UUID,
        chunk_index: int,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[dict] = None
    ) -> DocumentChunk:
        """문서 청크 생성"""
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
            metadata=metadata
        )
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)
        return chunk
    
    @staticmethod
    async def search_documents(
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        limit: int = 10
    ) -> List[Document]:
        """문서 검색 (제목 및 내용)"""
        result = await db.execute(
            select(Document)
            .where(
                and_(
                    Document.user_id == user_id,
                    or_(
                        Document.title.ilike(f"%{query}%"),
                        Document.content.ilike(f"%{query}%")
                    )
                )
            )
            .limit(limit)
        )
        return result.scalars().all()


class ComplianceCRUD:
    """규제 준수 CRUD"""
    
    @staticmethod
    async def create_check(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        regulation_type: str,
        check_type: str,
        result: str,
        details: Optional[dict] = None,
        recommendations: Optional[List[str]] = None
    ) -> ComplianceCheck:
        """규제 준수 체크 생성"""
        check = ComplianceCheck(
            session_id=session_id,
            user_id=user_id,
            regulation_type=regulation_type,
            check_type=check_type,
            result=result,
            details=details,
            recommendations=recommendations
        )
        db.add(check)
        await db.commit()
        await db.refresh(check)
        return check
    
    @staticmethod
    async def get_session_checks(
        db: AsyncSession,
        session_id: uuid.UUID
    ) -> List[ComplianceCheck]:
        """세션의 규제 준수 체크 조회"""
        result = await db.execute(
            select(ComplianceCheck)
            .where(ComplianceCheck.session_id == session_id)
            .order_by(ComplianceCheck.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_failed_checks(
        db: AsyncSession,
        days: int = 30
    ) -> List[ComplianceCheck]:
        """실패한 규제 준수 체크 조회"""
        start_date = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(ComplianceCheck)
            .where(
                and_(
                    ComplianceCheck.result == "fail",
                    ComplianceCheck.created_at >= start_date
                )
            )
            .order_by(ComplianceCheck.created_at.desc())
        )
        return result.scalars().all()
