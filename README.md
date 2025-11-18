# Secure Finance Agent

보안을 중요시하는 금융 업무에서 사용할 수 있는 AI 에이전트 시스템입니다.

## 주요 기능

- LangGraph로 구현한 에이전트 워크플로우
- 리스크 평가 및 규제 준수 자동 체크
- JWT 인증 및 데이터 암호화
- 모든 작업 감사 로그 기록
- Docker Compose로 간편한 배포

## 기술 스택

**백엔드**
- Python 3.11 / FastAPI
- LangGraph / LangChain
- Claude 3.5 Sonnet

**데이터베이스**
- PostgreSQL + pgvector
- Qdrant (벡터 검색)
- Redis (캐싱)

**보안**
- JWT 인증
- AES-256 암호화
- HashiCorp Vault

**모니터링**
- Prometheus
- Grafana

## 시작하기

### 환경 설정
```bash
cp .env.example .env
# .env 파일에서 필수 항목 설정:
# - ANTHROPIC_API_KEY
# - JWT_SECRET_KEY
# - ENCRYPTION_KEY
```

### 실행
```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f agent-api
```

### 접속
- API: http://localhost:8000/api/docs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

## 사용 예제

```python
import httpx

# 로그인
response = httpx.post(
    "http://localhost:8000/api/v1/auth/login",
    data={"username": "user@example.com", "password": "password"}
)
token = response.json()["access_token"]

# 에이전트 질의
response = httpx.post(
    "http://localhost:8000/api/v1/agents/query",
    headers={"Authorization": f"Bearer {token}"},
    json={"query": "포트폴리오 리스크 분석해줘"}
)

result = response.json()
print(result["response"])
```

## 아키텍처

```
Client
  ↓
FastAPI (인증/보안)
  ↓
LangGraph Agent
  ├─ Financial Analysis
  ├─ Risk Assessment
  └─ Compliance Check
  ↓
PostgreSQL / Qdrant / Redis
  ↓
Prometheus / Grafana
```

## 보안

### 키 생성
```bash
# JWT Secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 감사 로그
```bash
# 오늘 로그 확인
cat logs/audit/audit_$(date +%Y-%m-%d).jsonl
```

## 테스트

```bash
poetry run pytest
```

## 프로젝트 구조

```
src/
├── main.py              # FastAPI 앱
├── config.py            # 설정
├── agents/              # 에이전트 로직
│   ├── orchestrator.py
│   └── tools.py
├── security/            # 보안 레이어
│   ├── auth.py
│   ├── audit.py
│   └── middleware.py
└── api/routes/          # API 엔드포인트
```

## 라이선스

MIT
