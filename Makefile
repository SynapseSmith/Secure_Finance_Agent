# Makefile for Secure Finance Agent

.PHONY: help install test lint format clean docker-up docker-down

help:
	@echo "사용 가능한 명령어:"
	@echo "  make install       - 의존성 설치"
	@echo "  make test          - 테스트 실행"
	@echo "  make lint          - 린팅 검사"
	@echo "  make format        - 코드 포맷팅"
	@echo "  make clean         - 임시 파일 삭제"
	@echo "  make docker-up     - Docker 서비스 시작"
	@echo "  make docker-down   - Docker 서비스 종료"
	@echo "  make dev           - 개발 서버 실행"

install:
	poetry install

test:
	poetry run pytest -v --cov=src --cov-report=html

test-watch:
	poetry run ptw -- -v

lint:
	poetry run black --check src/
	poetry run ruff check src/
	poetry run mypy src/

format:
	poetry run black src/
	poetry run ruff check --fix src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/ .coverage coverage.xml

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

dev:
	poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

prod:
	poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

migrate:
	poetry run alembic upgrade head

migrate-create:
	@read -p "마이그레이션 이름: " name; \
	poetry run alembic revision --autogenerate -m "$$name"

security-check:
	poetry run bandit -r src/
	poetry run safety check

benchmark:
	poetry run python scripts/benchmark_llm.py

setup-keys:
	@echo "JWT Secret Key:"
	@python -c "import secrets; print(secrets.token_urlsafe(32))"
	@echo "\nEncryption Key:"
	@python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
