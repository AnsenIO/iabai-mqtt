"""
Authorization management for the IABAI fleet.

Handles permission checks, role hierarchy, and dynamic authorization
rules that can be updated at runtime.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Any
from enum import Enum
from datetime import datetime

from iabai_mqtt.identity import Role


class Permission(Enum):
    """Granular permissions for fleet operations."""
    # Project permissions
    CREATE_PROJECT = "create_project"
    READ_PROJECT = "read_project"
    UPDATE_PROJECT = "update_project"
    DELETE_PROJECT = "delete_project"
    
    # Task permissions
    CREATE_TASK = "create_task"
    READ_TASK = "read_task"
    UPDATE_TASK_STATUS = "update_task_status"
    ASSIGN_TASK = "assign_task"
    VALIDATE_TASK = "validate_task"
    DELETE_TASK = "delete_task"
    
    # Messaging permissions
    SEND_MESSAGE = "send_message"
    READ_MESSAGE = "read_message"
    BROADCAST = "broadcast"
    
    # Admin permissions
    MANAGE_PERMISSIONS = "manage_permissions"
    MANAGE_AGENTS = "manage_agents"
    
    @property
    def category(self) -> str:
        """Get the permission category."""
        if self in (Permission.CREATE_PROJECT, Permission.READ_PROJECT,
                    Permission.UPDATE_PROJECT, Permission.DELETE_PROJECT):
            return "project"
        elif self in (Permission.CREATE_TASK, Permission.READ_TASK,
                      Permission.UPDATE_TASK_STATUS, Permission.ASSIGN_TASK,
                      Permission.VALIDATE_TASK, Permission.DELETE_TASK):
            return "task"
        elif self in (Permission.SEND_MESSAGE, Permission.READ_MESSAGE,
                      Permission.BROADCAST):
            return "messaging"
        else:
            return "admin"


@dataclass
class PermissionRule:
    """A dynamic authorization rule."""
    name: str
    permission: Permission
    condition: str  # Expression or logic rule
    roles: List[str]  # Roles this rule applies to
    description: str = ""
    enabled: bool = True
    
    def matches(self, actor_role: str, target: Optional[str] = None) -> bool:
        """Check if this rule matches the given actor and target."""
        if not self.enabled:
            return False
        return actor_role in self.roles


@dataclass
class AgentPermissions:
    """Permissions for a specific agent."""
    agent_name: str
    role: str
    permissions: Set[Permission] = field(default_factory=set)
    custom_rules: List[PermissionRule] = field(default_factory=list)
    project_scopes: Dict[str, Set[Permission]] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and datetime.now() > self.expires_at)
    
    def has_permission(self, permission: Permission, target: Optional[str] = None) -> bool:
        """Check if this agent has a specific permission."""
        if self.is_expired:
            return False
        
        # Check direct permissions
        if permission in self.permissions:
            return True
        
        # Check project-specific permissions
        if target and target in self.project_scopes:
            if permission in self.project_scopes[target]:
                return True
        
        # Check custom rules
        for rule in self.custom_rules:
            if rule.permission == permission and rule.matches(self.role, target):
                return True
        
        return False
    
    def add_permission(self, permission: Permission):
        """Add a permission to this agent."""
        self.permissions.add(permission)
    
    def add_project_scope(self, project_name: str, permissions: Set[Permission]):
        """Add project-specific permissions."""
        self.project_scopes[project_name] = permissions
    
    def add_custom_rule(self, rule: PermissionRule):
        """Add a custom authorization rule."""
        self.custom_rules.append(rule)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize permissions to dictionary."""
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "permissions": [p.value for p in self.permissions],
            "custom_rules": [
                {
                    "name": r.name,
                    "permission": r.permission.value,
                    "condition": r.condition,
                    "roles": r.roles,
                    "description": r.description,
                    "enabled": r.enabled,
                }
                for r in self.custom_rules
            ],
            "project_scopes": {
                proj: [p.value for p in perms]
                for proj, perms in self.project_scopes.items()
            },
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class AuthorizationManager:
    """Manages permissions and authorization for the IABAI fleet."""
    
    def __init__(self):
        self.agent_permissions: Dict[str, AgentPermissions] = {}
        self.role_permissions: Dict[str, Set[Permission]] = {}
        self.custom_rules: List[PermissionRule] = []
        
        # Initialize default role permissions
        self._init_default_permissions()
    
    def _init_default_permissions(self):
        """Initialize default permissions for each role."""
        self.role_permissions[Role.ORCHESTRATOR.value] = {
            Permission.CREATE_PROJECT, Permission.READ_PROJECT,
            Permission.UPDATE_PROJECT, Permission.DELETE_PROJECT,
            Permission.CREATE_TASK, Permission.READ_TASK,
            Permission.UPDATE_TASK_STATUS, Permission.ASSIGN_TASK,
            Permission.VALIDATE_TASK, Permission.DELETE_TASK,
            Permission.SEND_MESSAGE, Permission.READ_MESSAGE,
            Permission.BROADCAST, Permission.MANAGE_PERMISSIONS,
            Permission.MANAGE_AGENTS,
        }
        
        self.role_permissions[Role.MANAGER.value] = {
            Permission.CREATE_PROJECT, Permission.READ_PROJECT,
            Permission.UPDATE_PROJECT,
            Permission.CREATE_TASK, Permission.READ_TASK,
            Permission.UPDATE_TASK_STATUS, Permission.ASSIGN_TASK,
            Permission.SEND_MESSAGE, Permission.READ_MESSAGE,
            Permission.BROADCAST,
        }
        
        self.role_permissions[Role.WORKER.value] = {
            Permission.READ_PROJECT, Permission.READ_TASK,
            Permission.UPDATE_TASK_STATUS, Permission.CREATE_TASK,
            Permission.SEND_MESSAGE, Permission.READ_MESSAGE,
        }
        
        self.role_permissions[Role.OBSERVER.value] = {
            Permission.READ_PROJECT, Permission.READ_TASK,
            Permission.READ_MESSAGE,
        }
    
    def register_agent(self, agent_name: str, role: str, 
                       expires_at: Optional[datetime] = None) -> AgentPermissions:
        """Register an agent with default permissions for their role."""
        permissions = self.role_permissions.get(role, set())
        
        agent_perms = AgentPermissions(
            agent_name=agent_name,
            role=role,
            permissions=permissions.copy(),
            expires_at=expires_at,
        )
        
        self.agent_permissions[agent_name.lower()] = agent_perms
        return agent_perms
    
    def has_permission(self, agent_name: str, permission: Permission,
                       target: Optional[str] = None) -> bool:
        """Check if an agent has a specific permission."""
        agent_perms = self.agent_permissions.get(agent_name.lower())
        if not agent_perms:
            return False
        
        return agent_perms.has_permission(permission, target)
    
    def add_custom_rule(self, rule: PermissionRule):
        """Add a custom authorization rule."""
        self.custom_rules.append(rule)
        # Apply to all agents with matching roles
        for agent_perms in self.agent_permissions.values():
            if agent_perms.role in rule.roles:
                agent_perms.add_custom_rule(rule)
    
    def grant_custom_permission(self, agent_name: str, permission: Permission):
        """Grant a custom permission to an agent."""
        if agent_name.lower() in self.agent_permissions:
            self.agent_permissions[agent_name.lower()].add_permission(permission)
    
    def revoke_permission(self, agent_name: str, permission: Permission):
        """Revoke a permission from an agent."""
        if agent_name.lower() in self.agent_permissions:
            self.agent_permissions[agent_name.lower()].permissions.discard(permission)
    
    def get_agent_permissions(self, agent_name: str) -> Optional[AgentPermissions]:
        """Get permissions for a specific agent."""
        return self.agent_permissions.get(agent_name.lower())
    
    def update_role_permissions(self, role: str, permissions: Set[Permission]):
        """Update permissions for a role (affects all agents with that role)."""
        self.role_permissions[role] = permissions.copy()
        
        # Update all agents with this role
        for agent_perms in self.agent_permissions.values():
            if agent_perms.role == role:
                agent_perms.permissions = permissions.copy()
    
    def get_all_agents(self) -> Dict[str, AgentPermissions]:
        """Get all registered agents and their permissions."""
        return self.agent_permissions.copy()
    
    def get_role_hierarchy(self) -> Dict[str, List[str]]:
        """Get the role hierarchy."""
        return {
            Role.ORCHESTRATOR.value: [Role.MANAGER.value, Role.WORKER.value, Role.OBSERVER.value],
            Role.MANAGER.value: [Role.WORKER.value, Role.OBSERVER.value],
            Role.WORKER.value: [Role.OBSERVER.value],
            Role.OBSERVER.value: [],
        }
