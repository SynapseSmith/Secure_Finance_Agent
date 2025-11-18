# 🏦 보안 중심 금융 AI 에이전트 시스템

금융권을 위한 엔터프라이즈급 AI 에이전트 플랫폼입니다. 최신 AI 기술과 강력한 보안 기능을 결합하여 규제 준수 환경에서 안전하게 사용할 수 있습니다.

## ✨ 주요 특징

### 🤖 AI 기능
- **LangGraph 기반 에이전트 오케스트레이션**: 복잡한 워크플로우 관리
- **Claude 3.5 Sonnet**: 금융 도메인 특화 언어 모델
- **멀티 에이전트 협업**: 분석, 리스크 평가, 규제 준수 체크
- **RAG (검색 증강 생성)**: 금융 문서 및 규정 검색

### 🔒 보안 기능
- **다층 보안 아키텍처**: 인증, 인가, 암호화
- **JWT 기반 인증**: 액세스/리프레시 토큰
- **AES-256-GCM 암호화**: 민감 데이터 보호
- **HashiCorp Vault 통합**: 시크릿 관리
- **전면적 감사 로깅**: 모든 작업 추적
- **API 속도 제한**: DDoS 방어

### 📊 규제 준수
- **GDPR 준수**: 개인정보 보호
- **KYC/AML 지원**: 고객 확인 및 자금세탁 방지
- **데이터 보존 정책**: 7년 (금융 규제)
- **PII 비식별화**: 개인정보 자동 마스킹

### 🏗️ 인프라
- **마이크로서비스 아키텍처**: Docker Compose
- **PostgreSQL + pgvector**: 벡터 검색 지원
- **Qdrant**: 엔터프라이즈급 벡터 데이터베이스
- **Redis**: 고속 캐싱
- **Prometheus + Grafana**: 실시간 모니터링

## 📋 기술 스택

### Core
- **Python 3.11+**
- **FastAPI**: 고성능 API 프레임워크
- **LangGraph 0.2+**: 에이전트 워크플로우
- **LangChain 0.3+**: LLM 통합

### AI/ML
- **Claude 3.5 Sonnet** (Anthropic)
- **GPT-4 Turbo** (OpenAI) - 선택사항
- **Qdrant**: 벡터 데이터베이스
- **pgvector**: PostgreSQL 벡터 확장

### 보안
- **python-jose**: JWT 인증
- **cryptography**: 암호화
- **passlib**: 비밀번호 해싱
- **hvac**: Vault 클라이언트

### 모니터링
- **OpenTelemetry**: 분산 추적
- **Prometheus**: 메트릭 수집
- **Grafana**: 시각화
- **structlog**: 구조화된 로깅

## 🚀 빠른 시작

### 1. 사전 요구사항
```bash
# Docker 및 Docker Compose 설치 필요
docker --version
docker-compose --version

# Python 3.11+ 설치
python --version
```

### 2. 환경 설정
```bash
# 프로젝트 클론
cd secure-finance-agent

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 필수 값들을 설정하세요:
# - ANTHROPIC_API_KEY 또는 OPENAI_API_KEY
# - JWT_SECRET_KEY (랜덤 256비트 키)
# - ENCRYPTION_KEY (32바이트 키)
# - 데이터베이스 비밀번호들
```

### 3. 의존성 설치
```bash
# Poetry 사용 (권장)
poetry install

# 또는 pip 사용
pip install -r requirements.txt
```

### 4. 인프라 시작
```bash
# Docker Compose로 모든 서비스 시작
docker-compose up -d

# 서비스 상태 확인
docker-compose ps
```

### 5. 데이터베이스 마이그레이션
```bash
# Alembic 마이그레이션 실행
alembic upgrade head
```

### 6. 애플리케이션 실행
```bash
# 개발 모드
poetry run uvicorn src.main:app --reload

# 또는 Docker 컨테이너로 실행 (이미 docker-compose에 포함)
docker-compose up agent-api
```

### 7. 접속 확인
- API 문서: http://localhost:8000/api/docs
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Vault: http://localhost:8200

## 📚 사용 예제

### API 호출 예제

```python
import httpx

# 로그인
response = httpx.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "user@example.com", "password": "password"}
)
access_token = response.json()["access_token"]

# 에이전트에 질문
response = httpx.post(
    "http://localhost:8000/api/v1/agents/query",
    headers={"Authorization": f"Bearer {access_token}"},
    json={
        "query": "현재 포트폴리오의 리스크 분석을 해주세요",
        "session_id": "unique-session-id"
    }
)

result = response.json()
print(result["response"])
print(f"위험도: {result['risk_level']}")
```

### Python SDK 예제

```python
from src.agents.orchestrator import SecureFinancialAgent

# 에이전트 초기화
agent = SecureFinancialAgent()

# 질의 실행
result = await agent.run(
    user_query="최근 3개월간 거래 내역을 분석해주세요",
    user_id="user123",
    session_id="session456"
)

print(result["response"])
print(f"승인 필요: {result['requires_approval']}")
print(f"감사 추적: {result['audit_trail']}")
```

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│                  (Web/Mobile/Desktop App)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                     API Gateway Layer                        │
│           FastAPI + Security Middleware + Rate Limit         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Authentication Layer                       │
│              JWT + OAuth 2.0 + Vault Integration            │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                Agent Orchestration Layer                     │
│         LangGraph + Claude 3.5 + Multi-Agent System         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Financial   │  │     Risk     │  │   Compliance    │  │
│  │   Analysis   │  │  Assessment  │  │     Checker     │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      Data Layer                              │
│   PostgreSQL + pgvector │ Redis │ Qdrant │ Vault           │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Monitoring & Logging                        │
│      OpenTelemetry │ Prometheus │ Grafana │ Audit Logs     │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 보안 가이드

### 필수 보안 설정

1. **환경 변수 보호**
   - `.env` 파일을 절대 git에 커밋하지 마세요
   - 프로덕션에서는 Vault 또는 AWS Secrets Manager 사용

2. **JWT 시크릿 키 생성**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **암호화 키 생성**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. **HTTPS 사용**
   - 프로덕션에서는 반드시 HTTPS 사용
   - Let's Encrypt로 무료 SSL 인증서 발급

5. **API 키 관리**
   - API 키는 주기적으로 로테이션 (기본 90일)
   - 최소 권한 원칙 적용

### 감사 로그 확인

```bash
# 오늘의 감사 로그 확인
cat logs/audit/audit_$(date +%Y-%m-%d).jsonl | jq .

# 특정 사용자의 활동 조회
cat logs/audit/*.jsonl | jq 'select(.user_id=="user123")'

# 보안 이벤트만 필터링
cat logs/audit/*.jsonl | jq 'select(.event_type=="SECURITY")'
```

## 📊 모니터링

### Grafana 대시보드

1. **시스템 메트릭**
   - CPU, 메모리, 디스크 사용량
   - API 응답 시간
   - 에러율

2. **비즈니스 메트릭**
   - 에이전트 쿼리 수
   - 리스크 레벨 분포
   - 규제 준수 체크 결과

3. **보안 메트릭**
   - 인증 실패 횟수
   - API 속도 제한 위반
   - 의심스러운 활동

### 알림 설정

```yaml
# Prometheus 알림 규칙 예제
groups:
  - name: security_alerts
    rules:
      - alert: HighFailedLoginRate
        expr: rate(failed_login_total[5m]) > 10
        annotations:
          summary: "로그인 실패율이 높습니다"
      
      - alert: HighRiskOperation
        expr: high_risk_operations_total > 100
        annotations:
          summary: "고위험 작업이 많이 발생했습니다"
```

## 🧪 테스트

```bash
# 전체 테스트 실행
poetry run pytest

# 커버리지 포함
poetry run pytest --cov=src --cov-report=html

# 특정 테스트만 실행
poetry run pytest tests/test_agents.py -v

# 보안 테스트
poetry run pytest tests/security/ -v
```

## 📈 성능 최적화

### 데이터베이스 최적화
- 인덱스 생성
- 커넥션 풀 설정
- 쿼리 최적화

### 캐싱 전략
- Redis 활용
- LRU 캐시
- API 응답 캐싱

### 벡터 검색 최적화
- Qdrant 인덱스 튜닝
- 배치 쿼리
- 근사 최근접 이웃 (ANN)

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🆘 지원

- 📧 Email: support@example.com
- 💬 Discord: [커뮤니티 링크]
- 📖 문서: [상세 문서 링크]

## 🗺️ 로드맵

### Phase 1 (현재)
- ✅ 기본 에이전트 시스템
- ✅ 보안 레이어
- ✅ 감사 로깅

### Phase 2 (진행 중)
- 🔄 멀티 테넌시 지원
- 🔄 고급 RAG 기능
- 🔄 실시간 위협 탐지

### Phase 3 (계획)
- 📅 AI 설명가능성 (XAI)
- 📅 페더레이티드 러닝
- 📅 블록체인 통합

## 🙏 감사의 말

- LangChain 팀
- Anthropic (Claude)
- FastAPI 커뮤니티
- 오픈소스 기여자들

---

**⚠️ 주의사항**: 이 시스템은 실제 금융 환경에 배포하기 전에 반드시 보안 감사와 규제 검토를 거쳐야 합니다.
