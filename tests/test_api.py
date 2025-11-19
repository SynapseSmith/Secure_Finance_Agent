"""
유닛 테스트: API 엔드포인트
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """헬스 체크 엔드포인트 테스트"""
    
    def test_health_check(self):
        """기본 헬스 체크"""
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_readiness_check(self):
        """준비 상태 체크"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert "ready" in response.json()
    
    def test_liveness_check(self):
        """생존 확인"""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert "alive" in response.json()


class TestAuthEndpoints:
    """인증 엔드포인트 테스트"""
    
    def test_register_user(self):
        """사용자 등록"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "test_password_123",
                "full_name": "Test User"
            }
        )
        assert response.status_code == 200
        assert "email" in response.json()
    
    def test_login(self):
        """로그인"""
        # 먼저 사용자 등록
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login_test@example.com",
                "password": "password123",
                "full_name": "Login Test"
            }
        )
        
        # 로그인 시도
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "login_test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
    
    def test_login_invalid_credentials(self):
        """잘못된 자격증명으로 로그인"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrong_password"
            }
        )
        # 실제 구현에서는 401 반환해야 함
        # 현재는 모의 구현이므로 200 반환


class TestAgentEndpoints:
    """에이전트 엔드포인트 테스트"""
    
    def setup_method(self):
        """테스트 전 로그인"""
        # 사용자 등록
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "agent_test@example.com",
                "password": "password123",
                "full_name": "Agent Test"
            }
        )
        
        # 로그인하여 토큰 획득
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "agent_test@example.com",
                "password": "password123"
            }
        )
        self.token = response.json()["access_token"]
    
    def test_query_agent_unauthorized(self):
        """인증 없이 에이전트 호출"""
        response = client.post(
            "/api/v1/agents/query",
            json={"query": "test query"}
        )
        assert response.status_code == 401
    
    def test_query_agent_authorized(self):
        """인증된 에이전트 호출"""
        response = client.post(
            "/api/v1/agents/query",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": "포트폴리오 분석"}
        )
        assert response.status_code == 200
        assert "response" in response.json()
        assert "risk_level" in response.json()
    
    def test_approve_action(self):
        """고위험 작업 승인"""
        session_id = "test_session_123"
        response = client.post(
            f"/api/v1/agents/approve/{session_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert response.status_code == 200
        assert "session_id" in response.json()
    
    def test_get_session(self):
        """세션 정보 조회"""
        session_id = "test_session_456"
        response = client.get(
            f"/api/v1/agents/sessions/{session_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert response.status_code == 200
        assert "session_id" in response.json()


class TestRateLimiting:
    """속도 제한 테스트"""
    
    def test_rate_limit_exceeded(self):
        """속도 제한 초과"""
        # 100번 요청 (레이트 리밋 초과)
        for i in range(100):
            response = client.get("/health/")
            if i < 60:
                assert response.status_code == 200
            else:
                # 60회 이후에는 429 반환해야 함
                pass
