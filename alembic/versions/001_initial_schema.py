"""초기 데이터베이스 스키마 생성

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """업그레이드"""
    # pgvector 확장 설치
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # users 테이블
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('role', sa.String(50), default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True)
    )
    
    # 인덱스 생성
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_user_active', 'users', ['is_active'])
    
    # token_blacklist 테이블
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token', sa.Text(), nullable=False, unique=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('blacklisted_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    
    op.create_index('idx_token_blacklist_token', 'token_blacklist', ['token'])
    op.create_index('idx_token_blacklist_expires', 'token_blacklist', ['expires_at'])
    
    # agent_sessions 테이블
    op.create_table(
        'agent_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), default=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('context', postgresql.JSON(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'])
    )
    
    op.create_index('idx_session_user', 'agent_sessions', ['user_id'])
    op.create_index('idx_session_status', 'agent_sessions', ['status'])
    op.create_index('idx_session_created', 'agent_sessions', ['created_at'])
    
    # session_messages 테이블
    op.create_table(
        'session_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['agent_sessions.id'])
    )
    
    op.create_index('idx_message_session', 'session_messages', ['session_id'])
    op.create_index('idx_message_created', 'session_messages', ['created_at'])
    
    # audit_logs 테이블
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_event', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_status', 'audit_logs', ['status'])
    
    # documents 테이블
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    
    op.create_index('idx_document_user', 'documents', ['user_id'])
    op.create_index('idx_document_status', 'documents', ['status'])
    op.create_index('idx_document_created', 'documents', ['created_at'])
    
    # document_chunks 테이블
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'])
    )
    
    op.create_index('idx_chunk_document', 'document_chunks', ['document_id'])
    op.create_index('idx_chunk_index', 'document_chunks', ['chunk_index'])
    
    # compliance_checks 테이블
    op.create_table(
        'compliance_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('regulation_type', sa.String(100), nullable=False),
        sa.Column('check_type', sa.String(100), nullable=False),
        sa.Column('result', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('recommendations', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['agent_sessions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    
    op.create_index('idx_compliance_session', 'compliance_checks', ['session_id'])
    op.create_index('idx_compliance_user', 'compliance_checks', ['user_id'])
    op.create_index('idx_compliance_type', 'compliance_checks', ['regulation_type'])
    op.create_index('idx_compliance_result', 'compliance_checks', ['result'])


def downgrade() -> None:
    """다운그레이드"""
    op.drop_table('compliance_checks')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('audit_logs')
    op.drop_table('session_messages')
    op.drop_table('agent_sessions')
    op.drop_table('token_blacklist')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector')
