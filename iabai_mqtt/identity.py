"""
Agent identity and role management for the IABAI fleet.

Each agent has a unique name, role, and optional credentials for
authentication against the MQTT broker.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import secrets


class Role(Enum):
    """Role hierarchy for the IABAI fleet."""
    ORCHESTRATOR = "orchestrator"    # Can assign tasks, validate completion, oversee all
    MANAGER = "manager"               # Can assign within domain, update status
    WORKER = "worker"                 # Can update own tasks, add information
    OBSERVER = "observer"             # Read-only access
    
    @property
    def can_assign(self) -> bool:
        return self in (Role.ORCHESTRATOR, Role.MANAGER)
    
    @property
    def can_validate(self) -> bool:
        return self == Role.ORCHESTRATOR
    
    @property
    def can_update_status(self) -> bool:
        return self in (Role.ORCHESTRATOR, Role.MANAGER, Role.WORKER)
    
    @property
    def can_create_project(self) -> bool:
        return self in (Role.ORCHESTRATOR, Role.MANAGER)
    
    @property
    def can_manage_permissions(self) -> bool:
        return self == Role.ORCHESTRATOR
    
    def can_act_on(self, target_role: 'Role') -> bool:
        """Check if this role can act on behalf of another role."""
        hierarchy = {
            Role.ORCHESTRATOR: [Role.MANAGER, Role.WORKER, Role.OBSERVER],
            Role.MANAGER: [Role.WORKER, Role.OBSERVER],
            Role.WORKER: [Role.OBSERVER],
            Role.OBSERVER: [],
        }
        return target_role in hierarchy.get(self, [])


@dataclass
class AgentIdentity:
    """Identity for an agent in the IABAI fleet."""
    name: str  # Unique: "Mairead", "Hermione", "Lyra", "Clide", "Bonnie", etc.
    role: Role
    broker_host: str = "gx10"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    nickname: Optional[str] = None  # Display name for non-authenticated agents
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.username:
            self.username = self.name
        if not self.client_id:
            self.client_id = f"iabai-{self.name.lower()}-{secrets.token_hex(4)}"
        if not self.nickname:
            self.nickname = self.name
    
    @property
    def display_name(self) -> str:
        return self.nickname or self.name
    
    @property
    def is_authenticated(self) -> bool:
        return bool(self.username and self.password)
    
    @property
    def topic_prefix(self) -> str:
        return f"iabai/agents/{self.name.lower()}"
    
    def get_status_topic(self) -> str:
        return f"{self.topic_prefix}/status"
    
    def get_tasks_topic(self) -> str:
        return f"{self.topic_prefix}/tasks"
    
    def get_events_topic(self) -> str:
        return f"{self.topic_prefix}/events"
    
    def get_config_topic(self) -> str:
        return f"{self.topic_prefix}/config"
    
    def get_all_topics(self) -> List[str]:
        return [self.get_status_topic(), self.get_tasks_topic(), 
                self.get_events_topic(), self.get_config_topic()]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.value,
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "username": self.username,
            "nickname": self.nickname,
            "client_id": self.client_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentIdentity':
        return cls(
            name=data["name"],
            role=Role(data["role"]),
            broker_host=data.get("broker_host", "gx10"),
            broker_port=data.get("broker_port", 1883),
            username=data.get("username"),
            password=data.get("password"),
            client_id=data.get("client_id"),
            nickname=data.get("nickname"),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def create_orchestrator(cls, name: str, **kwargs) -> 'AgentIdentity':
        return cls(name=name, role=Role.ORCHESTRATOR, **kwargs)
    
    @classmethod
    def create_worker(cls, name: str, **kwargs) -> 'AgentIdentity':
        return cls(name=name, role=Role.WORKER, **kwargs)
    
    @classmethod
    def create_manager(cls, name: str, **kwargs) -> 'AgentIdentity':
        return cls(name=name, role=Role.MANAGER, **kwargs)
    
    @classmethod
    def create_observer(cls, name: str, **kwargs) -> 'AgentIdentity':
        return cls(name=name, role=Role.OBSERVER, **kwargs)
    
    def __repr__(self) -> str:
        return f"AgentIdentity(name='{self.name}', role='{self.role.value}')"
