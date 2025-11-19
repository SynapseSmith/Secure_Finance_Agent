"""
유닛 테스트: 인증 시스템
"""
import pytest
from datetime import timedelta
from src.security.auth import AuthService, EncryptionService, PIIAnonymizer


class TestAuthService:
    """인증 서비스 테스트"""
    
    def setup_method(self):
        self.auth = AuthService()
    
    def test_password_hashing(self):
        """비밀번호 해싱 테스트"""
        password = "test_password_123"
        hashed = self.auth.get_password_hash(password)
        
        assert hashed != password
        assert self.auth.verify_password(password, hashed)
        assert not self.auth.verify_password("wrong_password", hashed)
    
    def test_create_access_token(self):
        """액세스 토큰 생성 테스트"""
        data = {"sub": "user@example.com", "role": "user"}
        token = self.auth.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_verify_token(self):
        """토큰 검증 테스트"""
        data = {"sub": "user@example.com"}
        token = self.auth.create_access_token(data)
        
        payload = self.auth.verify_token(token)
        assert payload["sub"] == "user@example.com"
        assert payload["type"] == "access"
    
    def test_refresh_token(self):
        """리프레시 토큰 테스트"""
        data = {"sub": "user@example.com"}
        token = self.auth.create_refresh_token(data)
        
        payload = self.auth.verify_token(token, "refresh")
        assert payload["sub"] == "user@example.com"
        assert payload["type"] == "refresh"


class TestEncryptionService:
    """암호화 서비스 테스트"""
    
    def setup_method(self):
        # 테스트용 키 생성
        from cryptography.fernet import Fernet
        import os
        os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
        
        from src.config import Settings
        settings = Settings()
        self.encryption = EncryptionService()
    
    def test_encrypt_decrypt(self):
        """암호화/복호화 테스트"""
        original = "sensitive_data_12345"
        encrypted = self.encryption.encrypt(original)
        decrypted = self.encryption.decrypt(encrypted)
        
        assert encrypted != original
        assert decrypted == original
    
    def test_encrypt_dict(self):
        """딕셔너리 암호화 테스트"""
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "account": "1234567890"
        }
        
        encrypted = self.encryption.encrypt_dict(data, ["ssn", "account"])
        
        assert encrypted["name"] == "John Doe"
        assert encrypted["ssn"] != "123-45-6789"
        assert encrypted["account"] != "1234567890"
        
        decrypted = self.encryption.decrypt_dict(encrypted, ["ssn", "account"])
        assert decrypted == data


class TestPIIAnonymizer:
    """개인정보 비식별화 테스트"""
    
    def test_anonymize_email(self):
        """이메일 마스킹 테스트"""
        result = PIIAnonymizer.anonymize_email("john.doe@example.com")
        assert "@example.com" in result
        assert "john" not in result or result.startswith("jo")
    
    def test_anonymize_phone(self):
        """전화번호 마스킹 테스트"""
        result = PIIAnonymizer.anonymize_phone("01012345678")
        assert "****" in result
        assert "5678" in result
    
    def test_anonymize_ssn(self):
        """주민등록번호 마스킹 테스트"""
        result = PIIAnonymizer.anonymize_ssn("123456-1234567")
        assert "123456" in result
        assert "*******" in result
    
    def test_anonymize_account(self):
        """계좌번호 마스킹 테스트"""
        result = PIIAnonymizer.anonymize_account("1234-5678-9012")
        assert "1234" in result
        assert "****" in result
        assert "9012" in result
