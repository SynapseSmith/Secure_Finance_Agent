"""
보안 레이어: 인증, 인가, 암호화
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
import structlog

from ..config import settings

logger = structlog.get_logger()

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """인증 서비스"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """액세스 토큰 생성"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.info("액세스 토큰 생성", user_id=data.get("sub"))
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """리프레시 토큰 생성"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> dict:
        """토큰 검증"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="잘못된 토큰 타입"
                )
            
            return payload
            
        except JWTError as e:
            logger.warning("토큰 검증 실패", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰"
            )


class EncryptionService:
    """데이터 암호화 서비스"""
    
    def __init__(self):
        # Fernet 암호화 (AES-256-GCM 기반)
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())
    
    def encrypt(self, data: str) -> str:
        """데이터 암호화"""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error("복호화 실패", error=str(e))
            raise ValueError("데이터 복호화에 실패했습니다")
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """딕셔너리 특정 필드 암호화"""
        encrypted = data.copy()
        for field in fields:
            if field in encrypted:
                encrypted[field] = self.encrypt(str(encrypted[field]))
        return encrypted
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """딕셔너리 특정 필드 복호화"""
        decrypted = data.copy()
        for field in fields:
            if field in decrypted:
                decrypted[field] = self.decrypt(decrypted[field])
        return decrypted


class PIIAnonymizer:
    """개인정보 비식별화"""
    
    @staticmethod
    def anonymize_email(email: str) -> str:
        """이메일 마스킹"""
        if "@" not in email:
            return "***"
        
        local, domain = email.split("@")
        if len(local) <= 3:
            masked_local = local[0] + "***"
        else:
            masked_local = local[:2] + "***" + local[-1]
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def anonymize_phone(phone: str) -> str:
        """전화번호 마스킹"""
        if len(phone) < 8:
            return "***-****"
        
        return phone[:3] + "-****-" + phone[-4:]
    
    @staticmethod
    def anonymize_ssn(ssn: str) -> str:
        """주민등록번호 마스킹"""
        if len(ssn) < 8:
            return "******-*******"
        
        return ssn[:6] + "-*******"
    
    @staticmethod
    def anonymize_account(account: str) -> str:
        """계좌번호 마스킹"""
        if len(account) < 8:
            return "****-****"
        
        return account[:4] + "-****-" + account[-4:]
