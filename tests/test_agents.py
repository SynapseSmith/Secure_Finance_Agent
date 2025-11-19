"""
통합 테스트: 에이전트 시스템
"""
import pytest
import asyncio
from src.agents.orchestrator import SecureFinancialAgent
from src.agents.tools import (
    FinancialAnalysisTool,
    RiskAssessmentTool,
    ComplianceCheckerTool
)


class TestAgentOrchestrator:
    """에이전트 오케스트레이터 테스트"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """에이전트 초기화 테스트"""
        agent = SecureFinancialAgent()
        assert agent.llm is not None
        assert agent.tools is not None
        assert agent.graph is not None
    
    @pytest.mark.asyncio
    async def test_simple_query(self):
        """단순 질의 테스트"""
        agent = SecureFinancialAgent()
        result = await agent.run(
            user_query="안녕하세요",
            user_id="test_user",
            session_id="test_session"
        )
        
        assert "response" in result
        assert "risk_level" in result
        assert result["risk_level"] in ["low", "medium", "high", "critical"]
    
    @pytest.mark.asyncio
    async def test_financial_analysis_query(self):
        """금융 분석 질의 테스트"""
        agent = SecureFinancialAgent()
        result = await agent.run(
            user_query="포트폴리오의 리스크를 분석해주세요",
            user_id="test_user",
            session_id="test_session_2"
        )
        
        assert "response" in result
        assert len(result["audit_trail"]) > 0
    
    @pytest.mark.asyncio
    async def test_high_risk_operation(self):
        """고위험 작업 테스트"""
        agent = SecureFinancialAgent()
        result = await agent.run(
            user_query="1억원을 해외로 송금하고 싶습니다",
            user_id="test_user",
            session_id="test_session_3"
        )
        
        assert result["risk_level"] in ["high", "critical"]
        # 고위험 작업은 승인이 필요할 수 있음


class TestFinancialTools:
    """금융 도구 테스트"""
    
    @pytest.mark.asyncio
    async def test_financial_analysis_tool(self):
        """금융 분석 도구 테스트"""
        tool = FinancialAnalysisTool()
        result = await tool._arun(
            query="포트폴리오 분석",
            user_id="test_user"
        )
        
        assert "status" in result
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_risk_assessment_tool(self):
        """리스크 평가 도구 테스트"""
        tool = RiskAssessmentTool()
        result = await tool._arun(
            query="고위험 투자",
            user_id="test_user"
        )
        
        assert "risk_level" in result
        assert "risk_score" in result
        assert 0 <= result["risk_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_compliance_checker_tool(self):
        """규제 준수 도구 테스트"""
        tool = ComplianceCheckerTool()
        result = await tool._arun(
            query="고객 정보 처리",
            user_id="test_user"
        )
        
        assert "compliant" in result
        assert "checks" in result
        assert isinstance(result["checks"], list)


class TestWorkflowIntegration:
    """워크플로우 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        agent = SecureFinancialAgent()
        
        # 1. 단순 질의
        result1 = await agent.run(
            user_query="오늘 시장 동향은?",
            user_id="test_user",
            session_id="workflow_test_1"
        )
        assert result1["risk_level"] == "low"
        
        # 2. 중간 리스크 질의
        result2 = await agent.run(
            user_query="주식 100주 매수 추천",
            user_id="test_user",
            session_id="workflow_test_2"
        )
        assert result2["risk_level"] in ["medium", "high"]
        
        # 3. 고위험 질의
        result3 = await agent.run(
            user_query="전 재산을 레버리지 투자",
            user_id="test_user",
            session_id="workflow_test_3"
        )
        assert result3["risk_level"] in ["high", "critical"]
