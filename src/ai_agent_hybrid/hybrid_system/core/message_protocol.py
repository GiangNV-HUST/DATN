"""
Message Protocol & Communication Schema

Implements standard message format for agent-to-agent communication.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Any, List
from enum import Enum
import time
import uuid


class MessageType(str, Enum):
    """Types of messages in the system"""
    QUERY = "query"              # User query / Agent query
    RESULT = "result"            # Execution result
    HANDOFF = "handoff"          # Transfer control to another agent
    ERROR = "error"              # Error occurred
    REQUEST = "request"          # Request for data/action
    STATE_UPDATE = "state_update"  # Update shared state
    BROADCAST = "broadcast"      # Message to all agents
    EVALUATION = "evaluation"    # Evaluation result
    ARBITRATION = "arbitration"  # Arbitration decision


class MessagePriority(int, Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 3
    HIGH = 5
    CRITICAL = 10


@dataclass
class AgentMessage:
    """
    Standard message format for agent communication

    This ensures consistent communication between agents and
    enables proper tracking, routing, and debugging.
    """
    # Core fields
    type: MessageType
    from_agent: str
    payload: Dict[str, Any]

    # Optional routing
    to_agent: Optional[str] = None  # None = broadcast

    # Metadata
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None

    def __str__(self) -> str:
        return (
            f"[{self.type.value}] "
            f"{self.from_agent} → {self.to_agent or 'ALL'} | "
            f"Priority: {self.priority.value} | "
            f"ID: {self.message_id[:8]}"
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "type": self.type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "context": self.context,
            "trace_id": self.trace_id
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentMessage":
        """Create from dictionary"""
        return cls(
            type=MessageType(data["type"]),
            from_agent=data["from_agent"],
            to_agent=data.get("to_agent"),
            payload=data["payload"],
            priority=MessagePriority(data.get("priority", MessagePriority.NORMAL.value)),
            timestamp=data.get("timestamp", time.time()),
            message_id=data.get("message_id", str(uuid.uuid4())),
            context=data.get("context", {}),
            trace_id=data.get("trace_id")
        )


@dataclass
class AgentResult:
    """Result from an agent execution"""
    agent: str
    success: bool
    data: Any
    confidence: float = 1.0
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_message(self, to_agent: Optional[str] = None) -> AgentMessage:
        """Convert result to message"""
        return AgentMessage(
            type=MessageType.RESULT if self.success else MessageType.ERROR,
            from_agent=self.agent,
            to_agent=to_agent,
            payload={
                "success": self.success,
                "data": self.data,
                "confidence": self.confidence,
                "reasoning": self.reasoning,
                "metadata": self.metadata,
                "errors": self.errors
            }
        )


class MessageBus:
    """
    Central message bus for agent communication

    Handles routing, priority queuing, and message delivery.
    """

    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = {}
        self.message_history: List[AgentMessage] = []
        self.max_history = 1000

    def subscribe(self, agent_name: str, handler: callable):
        """Subscribe an agent to receive messages"""
        if agent_name not in self.subscribers:
            self.subscribers[agent_name] = []
        self.subscribers[agent_name].append(handler)

    def publish(self, message: AgentMessage):
        """Publish a message to the bus"""
        # Add to history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

        # Route message
        if message.to_agent:
            # Direct message
            self._deliver_to(message.to_agent, message)
        else:
            # Broadcast
            for agent_name in self.subscribers:
                if agent_name != message.from_agent:
                    self._deliver_to(agent_name, message)

    def _deliver_to(self, agent_name: str, message: AgentMessage):
        """Deliver message to specific agent"""
        if agent_name in self.subscribers:
            for handler in self.subscribers[agent_name]:
                try:
                    handler(message)
                except Exception:
                    pass  # Silently ignore delivery errors

    def get_history(
        self,
        agent_name: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentMessage]:
        """Get message history, optionally filtered by agent"""
        history = self.message_history
        if agent_name:
            history = [
                msg for msg in history
                if msg.from_agent == agent_name or msg.to_agent == agent_name
            ]
        return history[-limit:]


# Global message bus instance
message_bus = MessageBus()
