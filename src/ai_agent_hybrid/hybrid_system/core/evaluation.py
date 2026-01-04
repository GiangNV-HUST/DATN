"""
Evaluation & Arbitration Layer

Implements quality assurance and conflict resolution for agent outputs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import os

import google.generativeai as genai


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
        status = "✅ PASSED" if self.passed else "❌ FAILED"
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
    - Accuracy: Trả lời đúng câu hỏi không?
    - Completeness: Đầy đủ thông tin không?
    - Relevance: Liên quan đến query không?
    - Hallucination: Có thông tin sai lệch không?
    - Coherence: Mạch lạc không?
    """

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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
            # Call Gemini for evaluation
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for consistent evaluation
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "accuracy_score": {"type": "number"},
                            "completeness_score": {"type": "number"},
                            "relevance_score": {"type": "number"},
                            "hallucination_detected": {"type": "boolean"},
                            "coherence_score": {"type": "number"},
                            "overall_score": {"type": "number"},
                            "issues": {"type": "array", "items": {"type": "string"}},
                            "suggestions": {"type": "array", "items": {"type": "string"}},
                            "reasoning": {"type": "string"}
                        }
                    }
                )
            )

            # Parse evaluation
            import json
            eval_result = json.loads(response.text)

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
Bạn là một chuyên gia đánh giá chất lượng câu trả lời của AI agent.

**USER QUERY:**
{user_query}

**AGENT RESPONSE:**
{agent_response}

**EXECUTION CONTEXT:**
{self._format_context(context)}

Hãy đánh giá câu trả lời theo các tiêu chí sau (scale 0.0 - 1.0):

1. **Accuracy** (Độ chính xác):
   - Agent có trả lời đúng câu hỏi không?
   - Thông tin có chính xác không?

2. **Completeness** (Độ đầy đủ):
   - Câu trả lời có đầy đủ thông tin cần thiết không?
   - Có thiếu sót gì quan trọng không?

3. **Relevance** (Độ liên quan):
   - Câu trả lời có liên quan trực tiếp đến câu hỏi không?
   - Có thông tin thừa/không cần thiết không?

4. **Hallucination** (Ảo giác):
   - Agent có bịa ra thông tin không có trong context không?
   - Có đưa ra con số/dữ liệu không chính xác không?

5. **Coherence** (Mạch lạc):
   - Câu trả lời có logic, dễ hiểu không?
   - Có mâu thuẫn nội tại không?

Trả về đánh giá dưới dạng JSON với:
- accuracy_score: 0.0-1.0
- completeness_score: 0.0-1.0
- relevance_score: 0.0-1.0
- hallucination_detected: true/false
- coherence_score: 0.0-1.0
- overall_score: 0.0-1.0 (trung bình)
- issues: [danh sách vấn đề phát hiện]
- suggestions: [đề xuất cải thiện]
- reasoning: "Giải thích chi tiết đánh giá"
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
        # Critical issues → Retry
        if hallucination:
            return EvaluationAction.RETRY

        # Low score → Retry
        if score < 0.5:
            return EvaluationAction.RETRY

        # Medium score → May need arbitration
        if score < 0.7:
            if len(issues) > 2:
                return EvaluationAction.RETRY
            return EvaluationAction.ARBITRATE

        # Good score → Accept
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
    1. AnalysisAgent says "MUA", ScreenerAgent says "BÁN"
    2. Multiple discovery suggestions
    3. Different price predictions
    """

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-preview-04-17',
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "final_decision": {"type": "string"},
                            "reasoning": {"type": "string"},
                            "confidence": {"type": "number"},
                            "supporting_agents": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                )
            )

            import json
            arb_result = json.loads(response.text)

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
Bạn là chuyên gia trọng tài giải quyết mâu thuẫn giữa các AI agents.

**USER QUERY:**
{user_query}

**CONFLICTING RESULTS:**
{results_text}

**CONTEXT:**
{self._format_context(context) if context else "No additional context"}

Nhiệm vụ của bạn:
1. Phân tích từng kết quả và độ tin cậy
2. Xác định kết quả nào chính xác hơn
3. Tổng hợp thành quyết định cuối cùng
4. Giải thích lý do chi tiết

Trả về JSON với:
- final_decision: Quyết định cuối cùng (câu trả lời đầy đủ)
- reasoning: Giải thích tại sao chọn quyết định này
- confidence: Độ tin cậy của quyết định (0.0-1.0)
- supporting_agents: Danh sách agents hỗ trợ quyết định này
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


# Global instances
critic_agent = CriticAgent()
arbitration_agent = ArbitrationAgent()
