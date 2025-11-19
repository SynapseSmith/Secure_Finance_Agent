"""
API 라우터: 문서 관리 (RAG)
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ...security.auth import AuthService
from ...api.routes.auth import oauth2_scheme
from ...database import get_db
from ...crud import DocumentCRUD, AuditLogCRUD
from ...services.rag import get_rag_service

router = APIRouter()
auth_service = AuthService()


class DocumentCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = None


class DocumentResponse(BaseModel):
    id: str
    title: str
    status: str
    file_type: Optional[str]
    tags: Optional[List[str]]
    created_at: str
    
    class Config:
        from_attributes = True


class DocumentSearchRequest(BaseModel):
    query: str
    limit: int = 5


class DocumentSearchResponse(BaseModel):
    results: List[dict]


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


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    문서 업로드
    
    - **file**: 업로드할 파일 (txt, pdf, docx)
    """
    user_id = uuid.UUID(current_user["user_id"])
    
    # 파일 타입 확인
    allowed_types = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 파일 형식입니다"
        )
    
    try:
        # 파일 읽기
        content = await file.read()
        
        # 텍스트 추출 (간단히 텍스트 파일만 지원)
        if file.content_type == "text/plain":
            text_content = content.decode("utf-8")
        else:
            # PDF, DOCX는 추가 라이브러리 필요
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="현재 텍스트 파일만 지원합니다"
            )
        
        # 문서 생성
        document = await DocumentCRUD.create_document(
            db=db,
            user_id=user_id,
            title=file.filename,
            content=text_content,
            file_type=file.content_type
        )
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="DOCUMENT_UPLOAD",
            action="upload_document",
            resource=f"document:{document.id}",
            status="success",
            details={"filename": file.filename}
        )
        
        # 백그라운드에서 임베딩 처리 (비동기)
        rag_service = get_rag_service()
        await rag_service.process_document(db, document.id, user_id)
        
        return DocumentResponse(
            id=str(document.id),
            title=document.title,
            status=document.status,
            file_type=document.file_type,
            tags=document.tags,
            created_at=document.created_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 실패: {str(e)}"
        )


@router.post("/create", response_model=DocumentResponse)
async def create_document(
    doc_data: DocumentCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    문서 생성 (텍스트)
    
    - **title**: 문서 제목
    - **content**: 문서 내용
    - **tags**: 태그 (선택사항)
    """
    user_id = uuid.UUID(current_user["user_id"])
    
    try:
        # 문서 생성
        document = await DocumentCRUD.create_document(
            db=db,
            user_id=user_id,
            title=doc_data.title,
            content=doc_data.content,
            tags=doc_data.tags
        )
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="DOCUMENT_CREATE",
            action="create_document",
            resource=f"document:{document.id}",
            status="success",
            details={"title": doc_data.title}
        )
        
        # 임베딩 처리
        rag_service = get_rag_service()
        await rag_service.process_document(db, document.id, user_id)
        
        return DocumentResponse(
            id=str(document.id),
            title=document.title,
            status=document.status,
            file_type=document.file_type,
            tags=document.tags,
            created_at=document.created_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 생성 실패: {str(e)}"
        )


@router.get("/list", response_model=List[DocumentResponse])
async def list_documents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    문서 목록 조회
    
    - **limit**: 조회할 문서 수
    - **offset**: 건너뛸 문서 수
    """
    user_id = uuid.UUID(current_user["user_id"])
    
    documents = await DocumentCRUD.get_user_documents(db, user_id, limit, offset)
    
    return [
        DocumentResponse(
            id=str(doc.id),
            title=doc.title,
            status=doc.status,
            file_type=doc.file_type,
            tags=doc.tags,
            created_at=doc.created_at.isoformat()
        )
        for doc in documents
    ]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    문서 상세 조회
    
    - **document_id**: 문서 ID
    """
    user_id = uuid.UUID(current_user["user_id"])
    doc_uuid = uuid.UUID(document_id)
    
    document = await DocumentCRUD.get_document(db, doc_uuid)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    return {
        "id": str(document.id),
        "title": document.title,
        "content": document.content,
        "file_type": document.file_type,
        "status": document.status,
        "tags": document.tags,
        "chunks_count": len(document.chunks) if hasattr(document, 'chunks') else 0,
        "created_at": document.created_at.isoformat()
    }


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_data: DocumentSearchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    문서 검색 (벡터 검색)
    
    - **query**: 검색 쿼리
    - **limit**: 반환할 결과 수
    """
    user_id = uuid.UUID(current_user["user_id"])
    
    try:
        rag_service = get_rag_service()
        results = await rag_service.search(
            query=search_data.query,
            user_id=user_id,
            limit=search_data.limit
        )
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="DOCUMENT_SEARCH",
            action="search_documents",
            resource="documents",
            status="success",
            details={"query": search_data.query, "results_count": len(results)}
        )
        
        return DocumentSearchResponse(results=results)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 실패: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    문서 삭제
    
    - **document_id**: 문서 ID
    """
    user_id = uuid.UUID(current_user["user_id"])
    doc_uuid = uuid.UUID(document_id)
    
    document = await DocumentCRUD.get_document(db, doc_uuid)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문서를 찾을 수 없습니다"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다"
        )
    
    try:
        # 벡터 삭제
        rag_service = get_rag_service()
        await rag_service.delete_document_vectors(doc_uuid)
        
        # DB에서 삭제
        await db.delete(document)
        await db.commit()
        
        # 감사 로그
        await AuditLogCRUD.create_log(
            db=db,
            user_id=user_id,
            event_type="DOCUMENT_DELETE",
            action="delete_document",
            resource=f"document:{doc_uuid}",
            status="success",
            details={"title": document.title}
        )
        
        return {"message": "문서가 삭제되었습니다"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 삭제 실패: {str(e)}"
        )
