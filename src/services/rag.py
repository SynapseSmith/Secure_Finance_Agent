"""
RAG (Retrieval Augmented Generation) 서비스
"""
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import AnthropicEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import structlog
import uuid

from ..config import settings
from ..crud import DocumentCRUD

logger = structlog.get_logger()


class RAGService:
    """RAG 서비스"""
    
    def __init__(self):
        """초기화"""
        # 임베딩 모델 초기화
        if settings.LLM_PROVIDER == "anthropic":
            # Anthropic은 자체 임베딩이 없으므로 OpenAI 사용
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
        
        # Qdrant 클라이언트
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        
        # 컬렉션 이름
        self.collection_name = "financial_documents"
        
        # 텍스트 분할기
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        # 컬렉션 초기화
        self._init_collection()
    
    def _init_collection(self):
        """Qdrant 컬렉션 초기화"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-small dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Qdrant 컬렉션 생성: {self.collection_name}")
        except Exception as e:
            logger.error(f"컬렉션 초기화 실패: {e}")
    
    async def process_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict:
        """
        문서 처리 (청크 분할 및 임베딩)
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            user_id: 사용자 ID
        
        Returns:
            처리 결과
        """
        try:
            # 문서 조회
            document = await DocumentCRUD.get_document(db, document_id)
            if not document:
                raise ValueError("문서를 찾을 수 없습니다")
            
            if document.user_id != user_id:
                raise ValueError("권한이 없습니다")
            
            # 문서 상태 업데이트
            await DocumentCRUD.update_document_status(db, document_id, "processing")
            
            # 텍스트 청크 분할
            chunks = self.text_splitter.split_text(document.content)
            logger.info(f"문서를 {len(chunks)}개 청크로 분할")
            
            # 각 청크 임베딩 및 저장
            points = []
            for idx, chunk in enumerate(chunks):
                # 임베딩 생성
                embedding = await self.embeddings.aembed_query(chunk)
                
                # PostgreSQL에 청크 저장
                await DocumentCRUD.create_chunk(
                    db=db,
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk,
                    embedding=embedding,
                    metadata={
                        "document_title": document.title,
                        "user_id": str(user_id)
                    }
                )
                
                # Qdrant에 저장할 포인트 생성
                point_id = str(uuid.uuid4())
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "document_id": str(document_id),
                            "chunk_index": idx,
                            "content": chunk,
                            "title": document.title,
                            "user_id": str(user_id)
                        }
                    )
                )
            
            # Qdrant에 벡터 업로드
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            # 문서 상태 업데이트
            await DocumentCRUD.update_document_status(db, document_id, "completed")
            
            logger.info(f"문서 처리 완료: {document_id}")
            
            return {
                "document_id": str(document_id),
                "chunks_count": len(chunks),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"문서 처리 실패: {e}")
            await DocumentCRUD.update_document_status(db, document_id, "failed")
            raise
    
    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        limit: int = 5
    ) -> List[Dict]:
        """
        벡터 검색
        
        Args:
            query: 검색 쿼리
            user_id: 사용자 ID
            limit: 반환할 결과 수
        
        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리 임베딩
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Qdrant 검색
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter={
                    "must": [
                        {
                            "key": "user_id",
                            "match": {"value": str(user_id)}
                        }
                    ]
                },
                limit=limit
            )
            
            # 결과 포맷팅
            results = []
            for result in search_results:
                results.append({
                    "document_id": result.payload["document_id"],
                    "title": result.payload["title"],
                    "content": result.payload["content"],
                    "score": result.score,
                    "chunk_index": result.payload["chunk_index"]
                })
            
            logger.info(f"검색 완료: {len(results)}개 결과")
            
            return results
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            raise
    
    async def delete_document_vectors(
        self,
        document_id: uuid.UUID
    ):
        """
        문서의 벡터 삭제
        
        Args:
            document_id: 문서 ID
        """
        try:
            # Qdrant에서 문서 관련 벡터 삭제
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector={
                    "filter": {
                        "must": [
                            {
                                "key": "document_id",
                                "match": {"value": str(document_id)}
                            }
                        ]
                    }
                }
            )
            
            logger.info(f"문서 벡터 삭제: {document_id}")
            
        except Exception as e:
            logger.error(f"벡터 삭제 실패: {e}")
            raise
    
    async def get_context_for_query(
        self,
        query: str,
        user_id: uuid.UUID,
        max_chunks: int = 3
    ) -> str:
        """
        쿼리에 대한 컨텍스트 생성
        
        Args:
            query: 사용자 쿼리
            user_id: 사용자 ID
            max_chunks: 최대 청크 수
        
        Returns:
            컨텍스트 문자열
        """
        results = await self.search(query, user_id, limit=max_chunks)
        
        if not results:
            return ""
        
        context_parts = []
        for idx, result in enumerate(results, 1):
            context_parts.append(
                f"[문서 {idx}: {result['title']}]\n{result['content']}"
            )
        
        return "\n\n".join(context_parts)


# 싱글톤 인스턴스
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """RAG 서비스 인스턴스 가져오기"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
