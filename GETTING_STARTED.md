# 시작 가이드

## 1️⃣ 빠른 시작 (5분)

### 사전 준비
```bash
# Docker 및 Docker Compose 확인
docker --version
docker-compose --version

# Git 클론 (이미 완료)
cd secure-finance-agent
```

### 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 수정 (필수!)
nano .env  # 또는 원하는 에디터 사용
```

**반드시 수정해야 할 항목:**
- `ANTHROPIC_API_KEY`: Claude API 키 (https://console.anthropic.com/)
- `JWT_SECRET_KEY`: 아래 명령으로 생성
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- `ENCRYPTION_KEY`: 아래 명령으로 생성
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- 모든 `PASSWORD` 항목들

### 실행
```bash
# 1. 인프라 시작
docker-compose up -d

# 2. 서비스 상태 확인 (모두 healthy가 될 때까지 대기)
docker-compose ps

# 3. 로그 확인
docker-compose logs -f agent-api
```

### 테스트
```bash
# 헬스 체크
curl http://localhost:8000/health

# API 문서 접속
open http://localhost:8000/api/docs
```

## 2️⃣ 개발 환경 설정 (로컬)

### Python 환경
```bash
# Poetry 설치
curl -sSL https://install.python-poetry.org | python3 -

# 의존성 설치
poetry install

# 가상환경 활성화
poetry shell
```

### 데이터베이스 마이그레이션
```bash
# Alembic 마이그레이션 실행
poetry run alembic upgrade head
```

### 로컬 서버 실행
```bash
# 개발 서버 (자동 리로드)
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 3️⃣ API 사용 예제

### 1. 사용자 등록
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "full_name": "홍길동"
  }'
```

### 2. 로그인
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepass123"
```

응답에서 `access_token`을 저장하세요.

### 3. 에이전트 질의
```bash
export TOKEN="your_access_token_here"

curl -X POST "http://localhost:8000/api/v1/agents/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "최근 포트폴리오의 리스크를 분석해주세요"
  }'
```

## 4️⃣ Python SDK 사용

```python
import httpx
import asyncio

class FinanceAgentClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.token = None
        self.client = httpx.AsyncClient()
    
    async def login(self, email: str, password: str):
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": email, "password": password}
        )
        data = response.json()
        self.token = data["access_token"]
        return self.token
    
    async def query(self, question: str):
        if not self.token:
            raise ValueError("먼저 로그인하세요")
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/agents/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": question}
        )
        return response.json()
    
    async def close(self):
        await self.client.aclose()

# 사용 예제
async def main():
    client = FinanceAgentClient("http://localhost:8000")
    
    # 로그인
    await client.login("user@example.com", "securepass123")
    
    # 질의
    result = await client.query("현재 시장 동향을 분석해주세요")
    print(f"응답: {result['response']}")
    print(f"위험도: {result['risk_level']}")
    
    await client.close()

asyncio.run(main())
```

## 5️⃣ 모니터링 대시보드

### Grafana 접속
```
URL: http://localhost:3000
ID: admin
PW: admin (첫 로그인 후 변경)
```

### Prometheus 접속
```
URL: http://localhost:9090
```

### 주요 메트릭
- `http_requests_total`: 총 요청 수
- `http_request_duration_seconds`: 응답 시간
- `agent_queries_total`: 에이전트 질의 수
- `security_events_total`: 보안 이벤트 수

## 6️⃣ 개발 워크플로우

### 1. 기능 개발
```bash
# 새 브랜치 생성
git checkout -b feature/new-feature

# 코드 작성
# ...

# 포맷팅 및 린팅
poetry run black src/
poetry run ruff check src/

# 타입 체크
poetry run mypy src/
```

### 2. 테스트
```bash
# 전체 테스트
poetry run pytest

# 커버리지 포함
poetry run pytest --cov=src --cov-report=html

# 특정 테스트만
poetry run pytest tests/test_agents.py -v
```

### 3. 커밋
```bash
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin feature/new-feature
```

## 7️⃣ 문제 해결

### Docker 컨테이너가 시작하지 않을 때
```bash
# 로그 확인
docker-compose logs

# 특정 서비스 로그
docker-compose logs agent-api

# 컨테이너 재시작
docker-compose restart agent-api
```

### 데이터베이스 연결 오류
```bash
# PostgreSQL 상태 확인
docker-compose exec postgres pg_isready

# 데이터베이스 접속
docker-compose exec postgres psql -U agent_user -d finance_agent
```

### Redis 연결 오류
```bash
# Redis 접속 테스트
docker-compose exec redis redis-cli ping
```

### 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :5432

# docker-compose.yml에서 포트 변경
```

## 8️⃣ 다음 단계

1. **커스터마이징**
   - `src/agents/tools.py`: 도구 추가
   - `src/agents/orchestrator.py`: 워크플로우 수정
   - `src/api/routes/`: API 엔드포인트 추가

2. **보안 강화**
   - `SECURITY.md` 체크리스트 확인
   - Vault 프로덕션 설정
   - SSL/TLS 인증서 설정

3. **성능 최적화**
   - 캐싱 전략 구현
   - 데이터베이스 인덱스 최적화
   - 부하 테스트 수행

4. **배포**
   - Kubernetes 설정
   - CI/CD 파이프라인
   - 모니터링 알림 설정

## 📚 추가 리소스

- [LangGraph 문서](https://langchain-ai.github.io/langgraph/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Claude API 문서](https://docs.anthropic.com/)
- [보안 베스트 프랙티스](./SECURITY.md)
