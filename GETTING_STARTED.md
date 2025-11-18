# 시작하기

## 설치

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
docker-compose up -d
docker-compose ps
```

### 확인
```bash
curl http://localhost:8000/health
```

## 개발 환경

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

### 로컬 실행
```bash
poetry run uvicorn src.main:app --reload
```

## API 사용

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

### 3. 에이전트 질의
```bash
curl -X POST "http://localhost:8000/api/v1/agents/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "포트폴리오 리스크 분석"}'
```

## Python 사용

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

## 모니터링

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

## 문제 해결

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
lsof -i :8000
# docker-compose.yml에서 포트 변경
```
