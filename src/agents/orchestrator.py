"""
LangGraph 기반 AI 에이전트 오케스트레이터
금융 도메인에 특화된 에이전트 워크플로우
"""
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

from ..config import settings
from ..security.audit import AuditLogger
from .tools import FinancialAnalysisTool, RiskAssessmentTool, ComplianceCheckerTool


class AgentState(TypedDict):
    """에이전트 상태 관리"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: str
    session_id: str
    risk_level: str  # low, medium, high, critical
    requires_approval: bool
    compliance_checked: bool
    audit_trail: list


class SecureFinancialAgent:
    """보안 강화 금융 AI 에이전트"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
        
        # LLM 초기화 (Claude 3.5 Sonnet)
        self.llm = ChatAnthropic(
            model=settings.MODEL_NAME,
            temperature=0.1,  # 금융에서는 낮은 temperature 사용
            max_tokens=4096,
            api_key=settings.ANTHROPIC_API_KEY
        )
        
        # 도구 초기화
        self.tools = [
            FinancialAnalysisTool(),
            RiskAssessmentTool(),
            ComplianceCheckerTool(),
        ]
        self.tool_executor = ToolExecutor(self.tools)
        
        # 그래프 빌드
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("classify_request", self._classify_request)
        workflow.add_node("risk_assessment", self._assess_risk)
        workflow.add_node("compliance_check", self._check_compliance)
        workflow.add_node("process_query", self._process_query)
        workflow.add_node("approval_required", self._require_approval)
        workflow.add_node("generate_response", self._generate_response)
        
        # 엣지 설정 (조건부 라우팅)
        workflow.set_entry_point("classify_request")
        
        workflow.add_conditional_edges(
            "classify_request",
            self._should_assess_risk,
            {
                "assess": "risk_assessment",
                "skip": "compliance_check"
            }
        )
        
        workflow.add_edge("risk_assessment", "compliance_check")
        
        workflow.add_conditional_edges(
            "compliance_check",
            self._should_require_approval,
            {
                "approve": "approval_required",
                "proceed": "process_query"
            }
        )
        
        workflow.add_edge("approval_required", "process_query")
        workflow.add_edge("process_query", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _classify_request(self, state: AgentState) -> AgentState:
        """요청 분류 및 초기 분석"""
        last_message = state["messages"][-1]
        
        classification_prompt = f"""
        다음 금융 관련 요청을 분류하세요:
        {last_message.content}
        
        분류 카테고리:
        - QUERY: 일반 정보 조회
        - TRANSACTION: 거래 실행
        - ANALYSIS: 데이터 분석
        - ADVISORY: 투자 자문
        
        위험도 (low/medium/high/critical)와 분류를 JSON으로 반환하세요.
        """
        
        response = await self.llm.ainvoke([HumanMessage(content=classification_prompt)])
        
        # 감사 로그
        await self.audit_logger.log_agent_action(
            user_id=state["user_id"],
            session_id=state["session_id"],
            action="classify_request",
            details={"classification": response.content}
        )
        
        state["messages"].append(AIMessage(content=response.content))
        return state
    
    async def _assess_risk(self, state: AgentState) -> AgentState:
        """리스크 평가"""
        risk_tool = next(t for t in self.tools if isinstance(t, RiskAssessmentTool))
        
        risk_result = await risk_tool.arun(
            query=state["messages"][-1].content,
            user_id=state["user_id"]
        )
        
        state["risk_level"] = risk_result.get("risk_level", "medium")
        state["audit_trail"].append({
            "step": "risk_assessment",
            "result": risk_result
        })
        
        return state
    
    async def _check_compliance(self, state: AgentState) -> AgentState:
        """규제 준수 검사"""
        compliance_tool = next(t for t in self.tools if isinstance(t, ComplianceCheckerTool))
        
        compliance_result = await compliance_tool.arun(
            query=state["messages"][-1].content,
            user_id=state["user_id"]
        )
        
        state["compliance_checked"] = compliance_result.get("compliant", False)
        state["audit_trail"].append({
            "step": "compliance_check",
            "result": compliance_result
        })
        
        return state
    
    async def _require_approval(self, state: AgentState) -> AgentState:
        """승인 대기 상태"""
        state["requires_approval"] = True
        
        await self.audit_logger.log_security_event(
            event_type="APPROVAL_REQUIRED",
            user_id=state["user_id"],
            action="high_risk_operation",
            resource="financial_transaction",
            status="pending",
            details={"risk_level": state["risk_level"]}
        )
        
        return state
    
    async def _process_query(self, state: AgentState) -> AgentState:
        """실제 쿼리 처리"""
        last_message = state["messages"][-1]
        
        # LLM에 컨텍스트와 함께 전달
        context = f"""
        사용자 ID: {state['user_id']}
        세션 ID: {state['session_id']}
        위험도: {state['risk_level']}
        규제 준수: {state['compliance_checked']}
        
        사용자 질문: {last_message.content}
        
        금융 전문가로서 정확하고 규제를 준수하는 답변을 제공하세요.
        """
        
        response = await self.llm.ainvoke([HumanMessage(content=context)])
        state["messages"].append(response)
        
        return state
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """최종 응답 생성 및 감사 로그"""
        await self.audit_logger.log_agent_action(
            user_id=state["user_id"],
            session_id=state["session_id"],
            action="generate_response",
            details={
                "risk_level": state["risk_level"],
                "compliance_checked": state["compliance_checked"],
                "audit_trail": state["audit_trail"]
            }
        )
        
        return state
    
    def _should_assess_risk(self, state: AgentState) -> str:
        """리스크 평가 필요 여부 판단"""
        last_message = state["messages"][-1].content.lower()
        
        # 거래, 투자 관련 키워드 체크
        high_risk_keywords = ["거래", "매수", "매도", "투자", "송금", "이체"]
        if any(keyword in last_message for keyword in high_risk_keywords):
            return "assess"
        return "skip"
    
    def _should_require_approval(self, state: AgentState) -> str:
        """승인 필요 여부 판단"""
        if state["risk_level"] in ["high", "critical"] or not state.get("compliance_checked"):
            return "approve"
        return "proceed"
    
    async def run(self, user_query: str, user_id: str, session_id: str) -> dict:
        """에이전트 실행"""
        initial_state = AgentState(
            messages=[HumanMessage(content=user_query)],
            user_id=user_id,
            session_id=session_id,
            risk_level="low",
            requires_approval=False,
            compliance_checked=False,
            audit_trail=[]
        )
        
        result = await self.graph.ainvoke(initial_state)
        
        return {
            "response": result["messages"][-1].content,
            "risk_level": result["risk_level"],
            "requires_approval": result["requires_approval"],
            "audit_trail": result["audit_trail"]
        }
