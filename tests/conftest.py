"""
테스트 설정 및 픽스처
"""
import pytest
import os
from cryptography.fernet import Fernet


@pytest.fixture(scope="session")
def test_env():
    """테스트 환경 변수 설정"""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG_MODE"] = "true"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing_only"
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["POSTGRES_PASSWORD"] = "test_password"
    os.environ["REDIS_PASSWORD"] = "test_password"
    os.environ["QDRANT_API_KEY"] = "test_api_key"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["MODEL_NAME"] = "claude-3-5-sonnet-20241022"
    

@pytest.fixture
def test_user():
    """테스트 사용자 데이터"""
    return {
        "email": "testuser@example.com",
        "password": "test_password_123",
        "full_name": "Test User"
    }


@pytest.fixture
def test_session():
    """테스트 세션 데이터"""
    return {
        "session_id": "test_session_123",
        "user_id": "test_user_456"
    }


@pytest.fixture
def sample_financial_data():
    """샘플 금융 데이터"""
    return {
        "portfolio": {
            "stocks": [
                {"symbol": "AAPL", "shares": 100, "price": 180.50},
                {"symbol": "GOOGL", "shares": 50, "price": 140.30}
            ],
            "bonds": [
                {"type": "treasury", "amount": 50000, "rate": 0.045}
            ],
            "cash": 100000
        },
        "risk_profile": "moderate",
        "investment_horizon": "long-term"
    }
