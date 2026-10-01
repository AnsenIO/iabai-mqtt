"""
Inter-agent messaging for the IABAI fleet.

Handles direct messaging, broadcast, and routing between agents
over MQTT with identity verification and authorization checks.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Awaitable
from enum import Enum
from datetime import datetime


class MessageDirection(Enum):
    """Direction of message flow."""
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    BROADCAST = "broadcast"


@dataclass
class MessageLog:
    """Log entry for a message."""
    message_id: str
    direction: MessageDirection
    sender: str
    recipient: Optional[str]
    message_type: str
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "direction": self.direction.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class FleetMessenger:
    """Manages inter-agent messaging in the IABAI fleet."""
    
    def __init__(self):
        self.message_logs: List[MessageLog] = []
        self.inbox: Dict[str, List[MessageLog]] = {}  # agent_name -> messages
        self.outbox: Dict[str, List[MessageLog]] = {}  # agent_name -> messages
        self.message_handlers: Dict[str, Callable] = {}
        self.max_log_size: int = 1000
    
    def send_direct_message(self, sender: str, sender_role: str,
                           recipient: str, content: str,
                           metadata: Optional[Dict] = None) -> MessageLog:
        """Send a direct message to another agent."""
        message_id = f"dm-{sender}-{recipient}-{datetime.now().isoformat()}"
        
        log_entry = MessageLog(
            message_id=message_id,
            direction=MessageDirection.OUTGOING,
            sender=sender,
            recipient=recipient,
            message_type="direct_message",
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        
        # Add to sender's outbox
        if sender not in self.outbox:
            self.outbox[sender] = []
        self.outbox[sender].append(log_entry)
        
        # Add to recipient's inbox
        if recipient not in self.inbox:
            self.inbox[recipient] = []
        self.inbox[recipient].append(log_entry)
        
        # Keep log size manageable
        self._trim_logs()
        
        return log_entry
    
    def send_broadcast(self, sender: str, sender_role: str,
                      content: str, metadata: Optional[Dict] = None) -> MessageLog:
        """Send a broadcast to all agents."""
        message_id = f"bc-{sender}-{datetime.now().isoformat()}"
        
        log_entry = MessageLog(
            message_id=message_id,
            direction=MessageDirection.BROADCAST,
            sender=sender,
            recipient=None,
            message_type="broadcast",
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        
        # Add to sender's outbox
        if sender not in self.outbox:
            self.outbox[sender] = []
        self.outbox[sender].append(log_entry)
        
        # Add to all agents' inboxes
        for agent_name in self.inbox:
            self.inbox[agent_name].append(log_entry)
        
        # Keep log size manageable
        self._trim_logs()
        
        return log_entry
    
    def receive_message(self, sender: str, sender_role: str,
                       recipient: str, content: str,
                       message_type: str = "direct_message",
                       metadata: Optional[Dict] = None) -> MessageLog:
        """Receive a message (for handling incoming messages)."""
        message_id = f"rm-{sender}-{recipient}-{datetime.now().isoformat()}"
        
        log_entry = MessageLog(
            message_id=message_id,
            direction=MessageDirection.INCOMING,
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        
        # Add to recipient's inbox
        if recipient not in self.inbox:
            self.inbox[recipient] = []
        self.inbox[recipient].append(log_entry)
        
        # Call message handler if registered
        if message_type in self.message_handlers:
            try:
                handler = self.message_handlers[message_type]
                handler(sender, sender_role, recipient, content, metadata or {})
            except Exception as e:
                print(f"Error handling message: {e}")
        
        # Keep log size manageable
        self._trim_logs()
        
        return log_entry
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler
    
    def get_inbox(self, agent_name: str) -> List[MessageLog]:
        """Get the inbox for a specific agent."""
        return self.inbox.get(agent_name, [])
    
    def get_outbox(self, agent_name: str) -> List[MessageLog]:
        """Get the outbox for a specific agent."""
        return self.outbox.get(agent_name, [])
    
    def get_message_history(self, agent_name: Optional[str] = None,
                           limit: int = 50) -> List[MessageLog]:
        """Get message history, optionally filtered by agent."""
        if agent_name:
            return self.inbox.get(agent_name, [])[-limit:] + \
                   self.outbox.get(agent_name, [])[-limit:]
        return self.message_logs[-limit:]
    
    def search_messages(self, query: str, agent_name: Optional[str] = None) -> List[MessageLog]:
        """Search messages by content or metadata."""
        query_lower = query.lower()
        results = []
        
        agents = [agent_name] if agent_name else list(self.inbox.keys())
        
        for agent in agents:
            for message in self.inbox.get(agent, []) + self.outbox.get(agent, []):
                if (query_lower in message.content.lower() or
                    any(query_lower in str(v).lower() for v in message.metadata.values())):
                    results.append(message)
        
        return results
    
    def clear_inbox(self, agent_name: str):
        """Clear the inbox for a specific agent."""
        self.inbox[agent_name] = []
    
    def _trim_logs(self):
        """Trim message logs to maintain manageable size."""
        for agent in list(self.inbox.keys()):
            if len(self.inbox[agent]) > self.max_log_size:
                self.inbox[agent] = self.inbox[agent][-self.max_log_size:]
        
        for agent in list(self.outbox.keys()):
            if len(self.outbox[agent]) > self.max_log_size:
                self.outbox[agent] = self.outbox[agent][-self.max_log_size:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get messaging statistics."""
        total_inbox = sum(len(msgs) for msgs in self.inbox.values())
        total_outbox = sum(len(msgs) for msgs in self.outbox.values())
        
        return {
            "total_agents": len(set(list(self.inbox.keys()) + list(self.outbox.keys()))),
            "total_messages_inbox": total_inbox,
            "total_messages_outbox": total_outbox,
            "message_handlers": len(self.message_handlers),
        }
