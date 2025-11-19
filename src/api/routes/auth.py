"""
API 라우터: 인증
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ...security.auth import AuthService
from ...security.audit import AuditLogger
from ...config import settings
from ...database import get_db
from ...crud import UserCRUD, TokenBlacklistCRUD, AuditLogCRUD

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
auth_service = AuthService()
audit_logger = AuditLogger()
    

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


@router.post("/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """사용자 등록"""
    # 이메일 중복 확인
    existing_user = await UserCRUD.get_user_by_email(db, user.email)
    if existing_user:
        await AuditLogCRUD.create_log(
            db=db,
            user_id=None,
            event_type="USER_REGISTRATION_FAILED",
            action="register",
            resource="user",
            status="failure",
            details={"email": user.email, "reason": "email_already_exists"},
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일이 이미 사용 중입니다"
        )
    
    # 사용자 생성
    new_user = await UserCRUD.create_user(
        db=db,
        email=user.email,
        password=user.password,
        full_name=user.full_name
    )
    
    # 감사 로그
    await AuditLogCRUD.create_log(
        db=db,
        user_id=new_user.id,
        event_type="USER_REGISTRATION",
        action="register",
        resource="user",
        status="success",
        details={"email": user.email},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """로그인"""
    # 사용자 인증
    user = await UserCRUD.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        await AuditLogCRUD.create_log(
            db=db,
            user_id=None,
            event_type="LOGIN_FAILED",
            action="login",
            resource="auth",
            status="failure",
            details={"email": form_data.username},
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 마지막 로그인 시간 업데이트
    await UserCRUD.update_last_login(db, user.id)
    
    # 토큰 생성
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    # 감사 로그
    await AuditLogCRUD.create_log(
        db=db,
        user_id=user.id,
        event_type="LOGIN",
        action="login",
        resource="auth",
        status="success",
        details={},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """토큰 갱신"""
    try:
        # 리프레시 토큰 검증
        payload = auth_service.verify_token(token_data.refresh_token, "refresh")
        user_id_str = payload.get("sub")
        user_id = uuid.UUID(user_id_str)
        
        # 블랙리스트 확인
        is_blacklisted = await TokenBlacklistCRUD.is_token_blacklisted(
            db, token_data.refresh_token
        )
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 무효화되었습니다"
            )
        
        # 사용자 확인
        user = await UserCRUD.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 새로운 토큰 생성
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        refresh_token = auth_service.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user.id,
            event_type="TOKEN_REFRESH",
            action="refresh_token",
            resource="auth",
            status="success",
            details={},
            ip_address=request.client.host if request.client else None
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신 실패"
        )


@router.post("/logout")
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """로그아웃"""
    try:
        payload = auth_service.verify_token(token)
        user_id_str = payload.get("sub")
        user_id = uuid.UUID(user_id_str)
        exp = payload.get("exp")
        
        # 토큰을 블랙리스트에 추가
        expires_at = datetime.fromtimestamp(exp)
        await TokenBlacklistCRUD.add_token(
            db=db,
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="LOGOUT",
            action="logout",
            resource="auth",
            status="success",
            details={},
            ip_address=request.client.host if request.client else None
        )
        
        return {"message": "로그아웃 되었습니다"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그아웃 처리 중 오류가 발생했습니다"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """현재 사용자 정보 조회"""
    try:
        payload = auth_service.verify_token(token)
        user_id = uuid.UUID(payload.get("sub"))
        
        user = await UserCRUD.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 실패"
        )
