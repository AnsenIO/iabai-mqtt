"""
Message serialization for IABAI fleet orchestration.

Provides standardized message formats for fleet-wide communication
with identity, authorization, and routing information.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class MessageType(Enum):
    """Types of messages in the IABAI fleet."""
    # Agent lifecycle
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"
    AGENT_REGISTER = "agent_register"
    AGENT_DEREGISTER = "agent_deregister"
    
    # Project management
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"
    PROJECT_INFO_REQUEST = "project_info_request"
    
    # Task management
    TASK_CREATE = "task_create"
    TASK_ASSIGN = "task_assign"
    TASK_STATUS_UPDATE = "task_status_update"
    TASK_VALIDATE = "task_validate"
    TASK_INFO_ADD = "task_info_add"
    TASK_INFO_REQUEST = "task_info_request"
    
    # Messaging
    DIRECT_MESSAGE = "direct_message"
    BROADCAST = "broadcast"
    QUERY = "query"
    RESPONSE = "response"
    
    # Authorization
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    
    # System
    HEALTH_CHECK = "health_check"
    ERROR = "error"


@dataclass
class MessageHeader:
    """Header for fleet messages with identity and routing info."""
    message_id: str
    message_type: MessageType
    timestamp: str
    sender: str  # Agent name
    sender_role: str  # Role of sender
    recipient: Optional[str] = None  # Agent name or None for broadcast
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    priority: int = 0  # 0-10
    ttl: Optional[int] = None  # Time-to-live in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "sender_role": self.sender_role,
            "recipient": self.recipient,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "priority": self.priority,
            "ttl": self.ttl,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageHeader':
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            timestamp=data["timestamp"],
            sender=data["sender"],
            sender_role=data["sender_role"],
            recipient=data.get("recipient"),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            priority=data.get("priority", 0),
            ttl=data.get("ttl"),
            metadata=data.get("metadata", {}),
        )
    
    @property
    def is_expired(self) -> bool:
        if not self.ttl:
            return False
        try:
            message_time = datetime.fromisoformat(self.timestamp)
            now = datetime.now()
            return (now - message_time).total_seconds() > self.ttl
        except (ValueError, TypeError):
            return False


@dataclass
class FleetMessage:
    """Complete fleet message with header, payload, and metadata."""
    header: MessageHeader
    payload: Dict[str, Any]
    signature: Optional[str] = None  # For authenticated messages
    routing: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        import json
        return json.dumps({
            "header": self.header.to_dict(),
            "payload": self.payload,
            "signature": self.signature,
            "routing": self.routing,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'FleetMessage':
        import json
        data = json.loads(json_str)
        return cls(
            header=MessageHeader.from_dict(data["header"]),
            payload=data["payload"],
            signature=data.get("signature"),
            routing=data.get("routing", {}),
        )
    
    @classmethod
    def create_heartbeat(cls, agent_name: str, sender_role: str) -> 'FleetMessage':
        """Create a heartbeat message."""
        header = MessageHeader(
            message_id=f"hb-{agent_name}-{datetime.now().isoformat()}",
            message_type=MessageType.HEARTBEAT,
            timestamp=datetime.now().isoformat(),
            sender=agent_name,
            sender_role=sender_role,
            priority=1,
        )
        return cls(
            header=header,
            payload={"status": "online", "timestamp": datetime.now().isoformat()},
        )
    
    @classmethod
    def create_direct_message(cls, sender: str, sender_role: str,
                             recipient: str, content: str,
                             metadata: Optional[Dict] = None) -> 'FleetMessage':
        """Create a direct message to another agent."""
        header = MessageHeader(
            message_id=f"dm-{sender}-{datetime.now().isoformat()}",
            message_type=MessageType.DIRECT_MESSAGE,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
            recipient=recipient,
            priority=5,
            metadata=metadata or {},
        )
        return cls(
            header=header,
            payload={"content": content, "sent_at": datetime.now().isoformat()},
        )
    
    @classmethod
    def create_task_assign(cls, sender: str, sender_role: str,
                          task_id: str, assignee: str,
                          project_name: str) -> 'FleetMessage':
        """Create a task assignment message."""
        header = MessageHeader(
            message_id=f"ta-{sender}-{task_id}-{datetime.now().isoformat()}",
            message_type=MessageType.TASK_ASSIGN,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
            recipient=assignee,
            correlation_id=task_id,
            priority=7,
        )
        return cls(
            header=header,
            payload={
                "task_id": task_id,
                "project_name": project_name,
                "assigned_by": sender,
                "assigned_at": datetime.now().isoformat(),
            },
        )
    
    @classmethod
    def create_task_status_update(cls, sender: str, sender_role: str,
                                 task_id: str, new_status: str,
                                 project_name: str) -> 'FleetMessage':
        """Create a task status update message."""
        header = MessageHeader(
            message_id=f"tsu-{sender}-{task_id}-{datetime.now().isoformat()}",
            message_type=MessageType.TASK_STATUS_UPDATE,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
            correlation_id=task_id,
            priority=5,
        )
        return cls(
            header=header,
            payload={
                "task_id": task_id,
                "project_name": project_name,
                "new_status": new_status,
                "updated_by": sender,
                "updated_at": datetime.now().isoformat(),
            },
        )
    
    @classmethod
    def create_task_validate(cls, sender: str, sender_role: str,
                            task_id: str, project_name: str,
                            notes: str = "") -> 'FleetMessage':
        """Create a task validation message."""
        header = MessageHeader(
            message_id=f"tv-{sender}-{task_id}-{datetime.now().isoformat()}",
            message_type=MessageType.TASK_VALIDATE,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
            correlation_id=task_id,
            priority=8,
        )
        return cls(
            header=header,
            payload={
                "task_id": task_id,
                "project_name": project_name,
                "validated_by": sender,
                "notes": notes,
                "validated_at": datetime.now().isoformat(),
            },
        )
    
    @classmethod
    def create_project_create(cls, sender: str, sender_role: str,
                             project_name: str, description: str = "",
                             tags: List[str] = None) -> 'FleetMessage':
        """Create a project creation message."""
        header = MessageHeader(
            message_id=f"pc-{sender}-{project_name}-{datetime.now().isoformat()}",
            message_type=MessageType.PROJECT_CREATE,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
            priority=6,
        )
        return cls(
            header=header,
            payload={
                "project_name": project_name,
                "description": description,
                "tags": tags or [],
                "created_by": sender,
                "created_at": datetime.now().isoformat(),
            },
        )
    
    @classmethod
    def create_broadcast(cls, sender: str, sender_role: str,
                        content: str, metadata: Optional[Dict] = None) -> 'FleetMessage':
        """Create a fleet-wide broadcast message."""
        header = MessageHeader(
            message_id=f"bc-{sender}-{datetime.now().isoformat()}",
            message_type=MessageType.BROADCAST,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
            priority=4,
            metadata=metadata or {},
        )
        return cls(
            header=header,
            payload={"content": content, "broadcast_at": datetime.now().isoformat()},
        )
    
    @classmethod
    def create_error(cls, sender: str, sender_role: str,
                    error_message: str, context: Optional[Dict] = None) -> 'FleetMessage':
        """Create an error message."""
        header = MessageHeader(
            message_id=f"err-{sender}-{datetime.now().isoformat()}",
            message_type=MessageType.ERROR,
            timestamp=datetime.now().isoformat(),
            sender=sender,
            sender_role=sender_role,
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
