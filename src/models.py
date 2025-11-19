"""
데이터베이스 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid

from .database import Base


class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String(50), default="user")  # user, admin, analyst
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # 관계
    sessions = relationship("AgentSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
    )


class TokenBlacklist(Base):
    """토큰 블랙리스트 (로그아웃된 토큰)"""
    __tablename__ = "token_blacklist"
    
    id = Column(Integer, primary_key=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_token_blacklist_token', 'token'),
        Index('idx_token_blacklist_expires', 'expires_at'),
    )


class AgentSession(Base):
    """에이전트 세션"""
    __tablename__ = "agent_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # 세션 정보
    status = Column(String(50), default="active")  # active, pending_approval, completed, cancelled
    risk_level = Column(String(20), nullable=True)  # low, medium, high, critical
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # 메타데이터
    context = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # 관계
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    messages = relationship("SessionMessage", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_session_user', 'user_id'),
        Index('idx_session_status', 'status'),
        Index('idx_session_created', 'created_at'),
    )


class SessionMessage(Base):
    """세션 메시지 (대화 기록)"""
    __tablename__ = "session_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False, index=True)
    
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    session = relationship("AgentSession", back_populates="messages")
    
    __table_args__ = (
        Index('idx_message_session', 'session_id'),
        Index('idx_message_created', 'created_at'),
    )


class AuditLog(Base):
    """감사 로그"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # 이벤트 정보
    event_type = Column(String(100), nullable=False, index=True)  # LOGIN, LOGOUT, QUERY, etc.
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)  # success, failure, pending
    
    # 상세 정보
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # 관계
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_event', 'event_type'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_status', 'status'),
    )


class Document(Base):
    """문서 (RAG용)"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # 문서 정보
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(String(1000), nullable=True)
    file_type = Column(String(50), nullable=True)  # pdf, docx, txt, etc.
    
    # 벡터 검색용 (pgvector)
    embedding = Column(ARRAY(Float), nullable=True)  # 임베딩 벡터
    
    # 메타데이터
    metadata = Column(JSON, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    
    # 처리 상태
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_document_user', 'user_id'),
        Index('idx_document_status', 'status'),
        Index('idx_document_created', 'created_at'),
    )


class DocumentChunk(Base):
    """문서 청크 (RAG용)"""
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    
    # 청크 정보
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float), nullable=True)  # 임베딩 벡터
    
    # 메타데이터
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index('idx_chunk_document', 'document_id'),
        Index('idx_chunk_index', 'chunk_index'),
    )


class ComplianceCheck(Base):
    """규제 준수 체크 기록"""
    __tablename__ = "compliance_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # 규제 정보
    regulation_type = Column(String(100), nullable=False)  # GDPR, KYC, AML, etc.
    check_type = Column(String(100), nullable=False)
    result = Column(String(50), nullable=False)  # pass, fail, warning
    
    # 상세 정보
    details = Column(JSON, nullable=True)
    recommendations = Column(ARRAY(Text), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_compliance_session', 'session_id'),
        Index('idx_compliance_user', 'user_id'),
        Index('idx_compliance_type', 'regulation_type'),
        Index('idx_compliance_result', 'result'),
    )
