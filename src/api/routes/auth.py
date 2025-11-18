"""
API 라우터: 인증
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from ...security.auth import AuthService
from ...security.audit import AuditLogger
from ...config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
auth_service = AuthService()
audit_logger = AuditLogger()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


@router.post("/register", response_model=dict)
async def register(user: UserCreate):
    """사용자 등록"""
    # 실제로는 데이터베이스에 사용자 생성
    hashed_password = auth_service.get_password_hash(user.password)
    
    await audit_logger.log_security_event(
        event_type="USER_REGISTRATION",
        user_id=user.email,
        action="register",
        resource="user",
        status="success",
        details={"email": user.email}
    )
    
    return {
        "message": "사용자가 성공적으로 등록되었습니다",
        "email": user.email
    }


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """로그인"""
    # 실제로는 데이터베이스에서 사용자 확인
    # user = await get_user_from_db(form_data.username)
    # if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
    #     raise HTTPException(...)
    
    # 토큰 생성
    access_token = auth_service.create_access_token(
        data={"sub": form_data.username}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": form_data.username}
    )
    
    await audit_logger.log_security_event(
        event_type="LOGIN",
        user_id=form_data.username,
        action="login",
        resource="auth",
        status="success",
        details={}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh):
    """토큰 갱신"""
    try:
        payload = auth_service.verify_token(token_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        # 새로운 토큰 생성
        access_token = auth_service.create_access_token(data={"sub": user_id})
        refresh_token = auth_service.create_refresh_token(data={"sub": user_id})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신 실패"
        )


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """로그아웃"""
    payload = auth_service.verify_token(token)
    user_id = payload.get("sub")
    
    # 실제로는 토큰을 블랙리스트에 추가
    
    await audit_logger.log_security_event(
        event_type="LOGOUT",
        user_id=user_id,
        action="logout",
        resource="auth",
        status="success",
        details={}
    )
    
    return {"message": "로그아웃 되었습니다"}
