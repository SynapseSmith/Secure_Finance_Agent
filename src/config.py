"""
애플리케이션 설정 관리
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """환경변수 기반 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # 기본 설정
    ENVIRONMENT: str = Field(default="development")
    DEBUG_MODE: bool = Field(default=False)
    
    # LLM 설정
    OPENAI_API_KEY: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    LLM_PROVIDER: str = Field(default="anthropic")
    MODEL_NAME: str = Field(default="claude-3-5-sonnet-20241022")
    
    # 데이터베이스
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="finance_agent")
    POSTGRES_USER: str = Field(default="agent_user")
    POSTGRES_PASSWORD: str
    
    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str
    REDIS_DB: int = Field(default=0)
    
    # Qdrant
    QDRANT_HOST: str = Field(default="localhost")
    QDRANT_PORT: int = Field(default=6333)
    QDRANT_API_KEY: str
    QDRANT_COLLECTION: str = Field(default="finance_documents")
    
    # JWT 인증
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # 암호화
    ENCRYPTION_KEY: str
    DATA_ENCRYPTION_ALGORITHM: str = Field(default="AES-256-GCM")
    
    # Vault
    VAULT_ADDR: str = Field(default="http://localhost:8200")
    VAULT_TOKEN: str = Field(default="")
    VAULT_NAMESPACE: str = Field(default="finance_agents")
    
    # 감사 로깅
    AUDIT_LOG_ENABLED: bool = Field(default=True)
    AUDIT_LOG_PATH: str = Field(default="./logs/audit")
    LOG_LEVEL: str = Field(default="INFO")
    
    # API 보안
    API_RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    API_CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"])
    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1"])
    API_KEY_ROTATION_DAYS: int = Field(default=90)
    
    # 규제 준수
    GDPR_ENABLED: bool = Field(default=True)
    DATA_RETENTION_DAYS: int = Field(default=2555)  # 7년
    PII_ANONYMIZATION: bool = Field(default=True)
    
    # 모니터링
    PROMETHEUS_PORT: int = Field(default=9090)
    GRAFANA_PORT: int = Field(default=3000)
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://localhost:4317")
    
    @validator("API_CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @property
    def database_url(self) -> str:
        """PostgreSQL 연결 URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def redis_url(self) -> str:
        """Redis 연결 URL"""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
