"""
Evaluation & Arbitration Layer

Implements quality assurance and conflict resolution for agent outputs.
Updated: Now uses OpenAI instead of Gemini for consistency.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import os
import json

from openai import OpenAI


class EvaluationAction(str, Enum):
    """Actions to take based on evaluation"""
    ACCEPT = "accept"
    RETRY = "retry"
    ARBITRATE = "arbitrate"
    ESCALATE = "escalate"


@dataclass
class Evaluation:
    """
    Result of evaluating an agent's response
    """
    passed: bool
    score: float  # 0.0 to 1.0
    reason: str
    action: EvaluationAction
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "[OK] PASSED" if self.passed else "[X] FAILED"
        return f"{status} | Score: {self.score:.2f} | Action: {self.action.value}"


@dataclass
class FinalDecision:
    """
    Final decision after arbitration
    """
    decision: str
    reasoning: str
    confidence: float
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CriticAgent:
    """
    Evaluates quality of agent responses

    Checks for:
    - Accuracy: Tra loi dung cau hoi khong?
    - Completeness: Day du thong tin khong?
    - Relevance: Lien quan den query khong?
    - Hallucination: Co thong tin sai lech khong?
    - Coherence: Mach lac khong?
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.evaluation_history: List[Dict] = []

    def evaluate(
        self,
        user_query: str,
        agent_response: str,
        context: Dict[str, Any],
        agent_name: str = "unknown"
    ) -> Evaluation:
        """
        Evaluate agent response quality

        Args:
            user_query: Original user question
            agent_response: Agent's response
            context: Execution context (tools used, data retrieved, etc.)
            agent_name: Name of agent being evaluated

        Returns:
            Evaluation result with score and action
        """
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            user_query,
            agent_response,
            context
        )

        try:
            # Call OpenAI for evaluation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI response quality evaluator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent evaluation
                response_format={"type": "json_object"}
            )

            # Parse evaluation
            eval_result = json.loads(response.choices[0].message.content)

            overall_score = eval_result.get("overall_score", 0.5)
            hallucination = eval_result.get("hallucination_detected", False)
            issues = eval_result.get("issues", [])
            suggestions = eval_result.get("suggestions", [])
            reasoning = eval_result.get("reasoning", "")

            # Determine action
            action = self._determine_action(overall_score, hallucination, issues)

            # Create evaluation
            evaluation = Evaluation(
                passed=(overall_score >= 0.7 and not hallucination),
                score=overall_score,
                reason=reasoning,
                action=action,
                suggestions=suggestions,
                metadata={
                    "accuracy": eval_result.get("accuracy_score", 0.0),
                    "completeness": eval_result.get("completeness_score", 0.0),
                    "relevance": eval_result.get("relevance_score", 0.0),
                    "coherence": eval_result.get("coherence_score", 0.0),
                    "hallucination": hallucination,
                    "issues": issues
                }
            )

            # Record evaluation
            self.evaluation_history.append({
                "agent": agent_name,
                "query": user_query,
                "score": overall_score,
                "passed": evaluation.passed,
                "action": action.value
            })

            return evaluation

        except Exception as e:
            # Default to accepting on evaluation error
            return Evaluation(
                passed=True,
                score=0.7,
                reason=f"Evaluation error: {str(e)}. Defaulting to accept.",
                action=EvaluationAction.ACCEPT,
                suggestions=["Manual review recommended"]
            )

    def _build_evaluation_prompt(
        self,
        user_query: str,
        agent_response: str,
        context: Dict
    ) -> str:
        """Build prompt for evaluation"""
        return f"""
Ban la mot chuyen gia danh gia chat luong cau tra loi cua AI agent.

**USER QUERY:**
{user_query}

**AGENT RESPONSE:**
{agent_response}

**EXECUTION CONTEXT:**
{self._format_context(context)}

Hay danh gia cau tra loi theo cac tieu chi sau (scale 0.0 - 1.0):

1. **Accuracy** (Do chinh xac):
   - Agent co tra loi dung cau hoi khong?
   - Thong tin co chinh xac khong?

2. **Completeness** (Do day du):
   - Cau tra loi co day du thong tin can thiet khong?
   - Co thieu sot gi quan trong khong?

3. **Relevance** (Do lien quan):
   - Cau tra loi co lien quan truc tiep den cau hoi khong?
   - Co thong tin thua/khong can thiet khong?

4. **Hallucination** (Ao giac):
   - Agent co bia ra thong tin khong co trong context khong?
   - Co dua ra con so/du lieu khong chinh xac khong?

5. **Coherence** (Mach lac):
   - Cau tra loi co logic, de hieu khong?
   - Co mau thuan noi tai khong?

Tra ve danh gia duoi dang JSON voi:
{{
    "accuracy_score": 0.0-1.0,
    "completeness_score": 0.0-1.0,
    "relevance_score": 0.0-1.0,
    "hallucination_detected": true/false,
    "coherence_score": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "issues": ["danh sach van de phat hien"],
    "suggestions": ["de xuat cai thien"],
    "reasoning": "Giai thich chi tiet danh gia"
}}
"""

    def _format_context(self, context: Dict) -> str:
        """Format context for prompt"""
        parts = []

        if "tools_used" in context:
            parts.append(f"Tools used: {', '.join(context['tools_used'])}")

        if "data_sources" in context:
            parts.append(f"Data sources: {', '.join(context['data_sources'])}")

        if "execution_time" in context:
            parts.append(f"Execution time: {context['execution_time']:.2f}s")

        return "\n".join(parts) if parts else "No context available"

    def _determine_action(
        self,
        score: float,
        hallucination: bool,
        issues: List[str]
    ) -> EvaluationAction:
        """Determine what action to take based on evaluation"""
        # Critical issues -> Retry
        if hallucination:
            return EvaluationAction.RETRY

        # Low score -> Retry
        if score < 0.5:
            return EvaluationAction.RETRY

        # Medium score -> May need arbitration
        if score < 0.7:
            if len(issues) > 2:
                return EvaluationAction.RETRY
            return EvaluationAction.ARBITRATE

        # Good score -> Accept
        return EvaluationAction.ACCEPT

    def get_stats(self) -> Dict:
        """Get evaluation statistics"""
        if not self.evaluation_history:
            return {"total": 0}

        total = len(self.evaluation_history)
        passed = sum(1 for e in self.evaluation_history if e["passed"])
        avg_score = sum(e["score"] for e in self.evaluation_history) / total

        actions = {}
        for e in self.evaluation_history:
            action = e["action"]
            actions[action] = actions.get(action, 0) + 1

        return {
            "total_evaluations": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total,
            "avg_score": avg_score,
            "actions": actions
        }


class ArbitrationAgent:
    """
    Resolves conflicts between multiple agent responses

    Scenarios:
    1. AnalysisAgent says "MUA", ScreenerAgent says "BAN"
    2. Multiple discovery suggestions
    3. Different price predictions
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.arbitration_history: List[Dict] = []

    def arbitrate(
        self,
        user_query: str,
        conflicting_results: List[Dict],
        context: Optional[Dict] = None
    ) -> FinalDecision:
        """
        Arbitrate between conflicting results

        Args:
            user_query: Original user question
            conflicting_results: List of results from different agents
                Format: [
                    {"agent": "AnalysisAgent", "result": "...", "confidence": 0.8},
                    {"agent": "ScreenerAgent", "result": "...", "confidence": 0.7}
                ]
            context: Additional context

        Returns:
            Final decision with reasoning
        """
        # Check if there's an obvious winner
        if self._has_clear_winner(conflicting_results):
            return self._select_winner(conflicting_results)

        # Use AI for arbitration
        return self._ai_arbitrate(user_query, conflicting_results, context)

    def _has_clear_winner(self, results: List[Dict]) -> bool:
        """Check if one result is clearly better"""
        if len(results) < 2:
            return True

        # Sort by confidence
        sorted_results = sorted(
            results,
            key=lambda r: r.get("confidence", 0.0),
            reverse=True
        )

        # If top confidence is significantly higher
        top_conf = sorted_results[0].get("confidence", 0.0)
        second_conf = sorted_results[1].get("confidence", 0.0)

        return top_conf - second_conf > 0.3

    def _select_winner(self, results: List[Dict]) -> FinalDecision:
        """Select the result with highest confidence"""
        winner = max(results, key=lambda r: r.get("confidence", 0.0))

        return FinalDecision(
            decision=winner.get("result", ""),
            reasoning=f"Selected {winner.get('agent')} due to highest confidence",
            confidence=winner.get("confidence", 0.0),
            sources=[winner.get("agent", "unknown")]
        )

    def _ai_arbitrate(
        self,
        user_query: str,
        results: List[Dict],
        context: Optional[Dict]
    ) -> FinalDecision:
        """Use AI to arbitrate between conflicting results"""
        prompt = self._build_arbitration_prompt(user_query, results, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI arbitrator that resolves conflicts between agent responses. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            arb_result = json.loads(response.choices[0].message.content)

            decision = FinalDecision(
                decision=arb_result.get("final_decision", ""),
                reasoning=arb_result.get("reasoning", ""),
                confidence=arb_result.get("confidence", 0.5),
                sources=arb_result.get("supporting_agents", [])
            )

            # Record arbitration
            self.arbitration_history.append({
                "query": user_query,
                "num_conflicts": len(results),
                "decision": decision.decision,
                "confidence": decision.confidence
            })

            return decision

        except Exception as e:
            # Fallback: select highest confidence
            return self._select_winner(results)

    def _build_arbitration_prompt(
        self,
        user_query: str,
        results: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """Build prompt for arbitration"""
        results_text = "\n\n".join([
            f"**{r.get('agent', 'Unknown')}** (Confidence: {r.get('confidence', 0.0):.2f}):\n{r.get('result', 'N/A')}"
            for r in results
        ])

        return f"""
Ban la chuyen gia trong tai giai quyet mau thuan giua cac AI agents.

**USER QUERY:**
{user_query}

**CONFLICTING RESULTS:**
{results_text}

**CONTEXT:**
{self._format_context(context) if context else "No additional context"}

Nhiem vu cua ban:
1. Phan tich tung ket qua va do tin cay
2. Xac dinh ket qua nao chinh xac hon
3. Tong hop thanh quyet dinh cuoi cung
4. Giai thich ly do chi tiet

Tra ve JSON voi:
{{
    "final_decision": "Quyet dinh cuoi cung (cau tra loi day du)",
    "reasoning": "Giai thich tai sao chon quyet dinh nay",
    "confidence": 0.0-1.0,
    "supporting_agents": ["danh sach agents ho tro quyet dinh nay"]
}}
"""

    def _format_context(self, context: Optional[Dict]) -> str:
        """Format context for prompt"""
        if not context:
            return "No context"

        parts = []
        for key, value in context.items():
            parts.append(f"{key}: {value}")

        return "\n".join(parts)

    def get_stats(self) -> Dict:
        """Get arbitration statistics"""
        if not self.arbitration_history:
            return {"total": 0}

        total = len(self.arbitration_history)
        avg_confidence = sum(
            a["confidence"] for a in self.arbitration_history
        ) / total

        return {
            "total_arbitrations": total,
            "avg_confidence": avg_confidence,
            "avg_conflicts": sum(
                a["num_conflicts"] for a in self.arbitration_history
            ) / total
        }


# Global instances (lazy initialization to avoid import-time errors)
critic_agent = None
arbitration_agent = None


def get_critic_agent():
    """Get or create CriticAgent instance (lazy initialization)"""
    global critic_agent
    if critic_agent is None:
        critic_agent = CriticAgent()
    return critic_agent


def get_arbitration_agent():
    """Get or create ArbitrationAgent instance (lazy initialization)"""
    global arbitration_agent
    if arbitration_agent is None:
        arbitration_agent = ArbitrationAgent()
    return arbitration_agent
