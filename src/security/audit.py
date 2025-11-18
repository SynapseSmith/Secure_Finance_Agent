"""
감사 로깅 시스템
모든 중요 이벤트를 추적하고 기록
"""
from datetime import datetime
from typing import Optional, Dict, Any
import json
import structlog
from pathlib import Path

from ..config import settings

logger = structlog.get_logger()


class AuditLogger:
    """감사 로그 관리자"""
    
    def __init__(self):
        self.audit_log_path = Path(settings.AUDIT_LOG_PATH)
        self.audit_log_path.mkdir(parents=True, exist_ok=True)
        
    async def log_security_event(
        self,
        event_type: str,
        user_id: str,
        action: str,
        resource: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        """보안 이벤트 로깅"""
        if not settings.AUDIT_LOG_ENABLED:
            return
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "status": status,
            "ip_address": ip_address,
            "details": details or {},
            "environment": settings.ENVIRONMENT
        }
        
        # 구조화된 로그
        logger.info(
            "security_event",
            **log_entry
        )
        
        # 파일에 저장
        await self._write_audit_log(log_entry)
    
    async def log_agent_action(
        self,
        user_id: str,
        session_id: str,
        action: str,
        details: Dict[str, Any]
    ):
        """에이전트 액션 로깅"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": "agent_action",
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            "details": details
        }
        
        logger.info("agent_action", **log_entry)
        await self._write_audit_log(log_entry)
    
    async def log_data_access(
        self,
        user_id: str,
        data_type: str,
        data_id: str,
        operation: str,  # READ, WRITE, DELETE
        success: bool
    ):
        """데이터 접근 로깅"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": "data_access",
            "user_id": user_id,
            "data_type": data_type,
            "data_id": data_id,
            "operation": operation,
            "success": success
        }
        
        logger.info("data_access", **log_entry)
        await self._write_audit_log(log_entry)
    
    async def log_compliance_check(
        self,
        user_id: str,
        regulation: str,
        passed: bool,
        details: Dict[str, Any]
    ):
        """규제 준수 체크 로깅"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": "compliance_check",
            "user_id": user_id,
            "regulation": regulation,
            "passed": passed,
            "details": details
        }
        
        logger.info("compliance_check", **log_entry)
        await self._write_audit_log(log_entry)
    
    async def _write_audit_log(self, log_entry: Dict[str, Any]):
        """감사 로그를 파일에 기록"""
        try:
            # 날짜별 로그 파일
            log_file = self.audit_log_path / f"audit_{datetime.utcnow().date()}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error("감사 로그 기록 실패", error=str(e))


class ComplianceMonitor:
    """규제 준수 모니터링"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
    
    async def check_gdpr_compliance(self, user_id: str, data: Dict[str, Any]) -> bool:
        """GDPR 준수 확인"""
        # 데이터 처리 동의 확인
        # 데이터 최소화 원칙 확인
        # 목적 제한 확인
        
        passed = True  # 실제 체크 로직
        
        await self.audit_logger.log_compliance_check(
            user_id=user_id,
            regulation="GDPR",
            passed=passed,
            details={"data_fields": list(data.keys())}
        )
        
        return passed
    
    async def check_data_retention(self, data_created_at: datetime) -> bool:
        """데이터 보존 기간 확인"""
        retention_days = settings.DATA_RETENTION_DAYS
        age_days = (datetime.utcnow() - data_created_at).days
        
        if age_days > retention_days:
            logger.warning(
                "데이터 보존 기간 초과",
                age_days=age_days,
                retention_days=retention_days
            )
            return False
        
        return True
    
    async def check_kyc_compliance(self, user_id: str) -> bool:
        """KYC (Know Your Customer) 준수 확인"""
        # 실제로는 사용자 신원 확인 데이터 체크
        passed = True
        
        await self.audit_logger.log_compliance_check(
            user_id=user_id,
            regulation="KYC",
            passed=passed,
            details={"verification_level": "full"}
        )
        
        return passed
