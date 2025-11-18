# 멀티스테이지 빌드로 보안 강화
FROM python:3.11-slim as builder

# 보안 업데이트
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install --no-cache-dir poetry==1.8.0

WORKDIR /app

# 의존성만 먼저 설치 (캐싱 최적화)
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# 최종 이미지
FROM python:3.11-slim

# 보안: 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 필요한 런타임 라이브러리만 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 빌더에서 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser ./src ./src
COPY --chown=appuser:appuser ./alembic ./alembic
COPY --chown=appuser:appuser ./alembic.ini ./

# 로그 디렉토리 생성
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# 비root 사용자로 전환
USER appuser

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
