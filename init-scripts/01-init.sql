-- PostgreSQL 초기화 스크립트

-- pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 세션 테이블
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(50),
    risk_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- 쿼리 로그 테이블
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    user_id INTEGER REFERENCES users(id),
    query_text TEXT,
    response_text TEXT,
    risk_level VARCHAR(50),
    requires_approval BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 문서 테이블 (벡터 검색용)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    embedding vector(1536),  -- OpenAI 임베딩 차원
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 검색을 위한 인덱스
CREATE INDEX IF NOT EXISTS documents_embedding_idx 
ON documents USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 감사 로그 테이블
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100),
    user_id INTEGER,
    action VARCHAR(255),
    resource VARCHAR(255),
    status VARCHAR(50),
    ip_address INET,
    details JSONB
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);

-- 샘플 관리자 사용자 생성 (개발용)
-- 비밀번호: admin123 (bcrypt 해시)
INSERT INTO users (email, hashed_password, full_name, is_active, is_verified)
VALUES ('admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5Y3TZ.eUqm4S2', 'Admin User', TRUE, TRUE)
ON CONFLICT (email) DO NOTHING;
