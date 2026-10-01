"""
Message serialization and deserialization for IABAI MQTT communication.

Provides standardized message formats and utilities for agent communication.
"""

import json
import logging
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Standard message types for IABAI fleet communication."""
    # Agent lifecycle
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"
    OFFLINE = "offline"
    
    # Task management
    TASK_ASSIGN = "task_assign"
    TASK_STATUS = "task_status"
    TASK_RESULT = "task_result"
    TASK_CANCEL = "task_cancel"
    
    # Fleet coordination
    BROADCAST = "broadcast"
    QUERY = "query"
    RESPONSE = "response"
    
    # System
    CONFIG_UPDATE = "config_update"
    HEALTH_CHECK = "health_check"
    ERROR = "error"
    
    # Documentation
    DOC_PUBLISH = "doc_publish"
    DOC_REQUEST = "doc_request"


@dataclass
class MessageHeader:
    """Standard message header for IABAI MQTT communication."""
    message_id: str
    message_type: MessageType
    timestamp: str
    sender: str
    recipient: Optional[str] = None
    correlation_id: Optional[str] = None
    priority: int = 0  # 0-10, higher = more urgent
    ttl: Optional[int] = None  # Time-to-live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert header to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "recipient": self.recipient,
            "correlation_id": self.correlation_id,
            "priority": self.priority,
            "ttl": self.ttl,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageHeader":
        """Create header from dictionary."""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            timestamp=data["timestamp"],
            sender=data["sender"],
            recipient=data.get("recipient"),
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 0),
            ttl=data.get("ttl"),
        )


@dataclass
class AgentMessage:
    """Standard message format for IABAI MQTT communication."""
    header: MessageHeader
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        data = {
            "header": self.header.to_dict(),
            "payload": self.payload,
            "metadata": self.metadata,
        }
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        """Deserialize message from JSON string."""
        data = json.loads(json_str)
        return cls(
            header=MessageHeader.from_dict(data["header"]),
            payload=data["payload"],
            metadata=data.get("metadata", {}),
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if not self.header.ttl:
            return False
            
        try:
            message_time = datetime.fromisoformat(self.header.timestamp)
            now = datetime.now()
            elapsed = (now - message_time).total_seconds()
            return elapsed > self.header.ttl
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def create_heartbeat(cls, agent_name: str) -> "AgentMessage":
        """Create a heartbeat message."""
        header = MessageHeader(
            message_id=f"hb-{agent_name}-{datetime.now().isoformat()}",
            message_type=MessageType.HEARTBEAT,
            timestamp=datetime.now().isoformat(),
            sender=agent_name,
            priority=1,
        )
        return cls(
            header=header,
            payload={"status": "online", "timestamp": datetime.now().isoformat()},
        )
    
    @classmethod
    def create_task_result(cls, agent_name: str, task_id: str, result: Any, success: bool = True) -> "AgentMessage":
        """Create a task result message."""
        header = MessageHeader(
            message_id=f"tr-{agent_name}-{task_id}-{datetime.now().isoformat()}",
            message_type=MessageType.TASK_RESULT,
            timestamp=datetime.now().isoformat(),
            sender=agent_name,
            correlation_id=task_id,
            priority=5,
        )
        return cls(
            header=header,
            payload={
                "task_id": task_id,
                "result": result,
                "success": success,
                "completed_at": datetime.now().isoformat(),
            },
        )
    
    @classmethod
    def create_broadcast(cls, agent_name: str, topic: str, message: str) -> "AgentMessage":
        """Create a broadcast message."""
        header = MessageHeader(
            message_id=f"bc-{agent_name}-{datetime.now().isoformat()}",
            message_type=MessageType.BROADCAST,
            timestamp=datetime.now().isoformat(),
            sender=agent_name,
            priority=3,
        )
        return cls(
            header=header,
            payload={
                "topic": topic,
                "message": message,
                "broadcast_at": datetime.now().isoformat(),
            },
        )
    
    @classmethod
    def create_error(cls, agent_name: str, error_message: str, context: Optional[Dict] = None) -> "AgentMessage":
        """Create an error message."""
        header = MessageHeader(
            message_id=f"err-{agent_name}-{datetime.now().isoformat()}",
            message_type=MessageType.ERROR,
            timestamp=datetime.now().isoformat(),
            sender=agent_name,
            priority=10,
        )
        return cls(
            header=header,
            payload={
                "error": error_message,
                "context": context or {},
                "reported_at": datetime.now().isoformat(),
            },
        )
