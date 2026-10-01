"""
MQTT Topic management for IABAI fleet communication.

Provides standardized topic patterns and utilities for agent communication.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class TopicNamespace(Enum):
    """Standard topic namespaces for IABAI fleet."""
    AGENTS = "iabai/agents"
    FLEET = "iabai/fleet"
    SHARED = "iabai/shared"
    TASKS = "iabai/tasks"
    EVENTS = "iabai/events"
    STATUS = "iabai/status"
    DOCS = "iabai/docs"
    CONFIG = "iabai/config"


class TopicPattern:
    """Represents an MQTT topic pattern with wildcards."""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.parts = pattern.split('/')
        
    def __str__(self):
        return self.pattern
        
    def __repr__(self):
        return f"TopicPattern('{self.pattern}')"
    
    def matches(self, topic: str) -> bool:
        """Check if a topic matches this pattern."""
        pattern_parts = self.pattern.split('/')
        topic_parts = topic.split('/')
        
        if len(pattern_parts) != len(topic_parts):
            return False
            
        for p, t in zip(pattern_parts, topic_parts):
            if p == '#':
                return True
            if p == '+':
                continue
            if p != t:
                return False
                
        return True


class TopicManager:
    """Manages MQTT topic patterns for the IABAI fleet."""
    
    # Agent topics
    AGENT_STATUS = TopicPattern("iabai/agents/{agent}/status")
    AGENT_TASKS = TopicPattern("iabai/agents/{agent}/tasks")
    AGENT_EVENTS = TopicPattern("iabai/agents/{agent}/events")
    AGENT_CONFIG = TopicPattern("iabai/agents/{agent}/config")
    
    # Fleet-wide topics
    FLEET_STATUS = TopicPattern("iabai/fleet/status")
    FLEET_TASKS = TopicPattern("iabai/fleet/tasks")
    FLEET_EVENTS = TopicPattern("iabai/fleet/events")
    FLEET_BROADCAST = TopicPattern("iabai/fleet/#")
    
    # Shared topics
    SHARED_CONFIG = TopicPattern("iabai/shared/config")
    SHARED_DATA = TopicPattern("iabai/shared/data")
    SHARED_DOCS = TopicPattern("iabai/shared/docs")
    
    # Task topics
    TASK_QUEUE = TopicPattern("iabai/tasks/queue")
    TASK_RESULTS = TopicPattern("iabai/tasks/results")
    TASK_EVENTS = TopicPattern("iabai/tasks/events")
    
    # Status topics
    SYSTEM_STATUS = TopicPattern("iabai/status/system")
    HEALTH_CHECK = TopicPattern("iabai/status/health")
    
    # Document topics
    DOCS_PUBLISH = TopicPattern("iabai/docs/publish")
    DOCS_SUBSCRIBE = TopicPattern("iabai/docs/subscribe")
    
    # Config topics
    CONFIG_UPDATE = TopicPattern("iabai/config/update")
    CONFIG_QUERY = TopicPattern("iabai/config/query")
    
    @classmethod
    def format_agent_status(cls, agent_name: str) -> str:
        """Format agent status topic."""
        return cls.AGENT_STATUS.pattern.format(agent=agent_name)
    
    @classmethod
    def format_agent_tasks(cls, agent_name: str) -> str:
        """Format agent tasks topic."""
        return cls.AGENT_TASKS.pattern.format(agent=agent_name)
    
    @classmethod
    def format_agent_events(cls, agent_name: str) -> str:
        """Format agent events topic."""
        return cls.AGENT_EVENTS.pattern.format(agent=agent_name)
    
    @classmethod
    def format_fleet_broadcast(cls, topic: Optional[str] = None) -> str:
        """Format fleet broadcast topic."""
        if topic:
            return f"iabai/fleet/{topic}"
        return "iabai/fleet/#"
    
    @classmethod
    def get_all_agent_topics(cls, agent_name: str) -> List[str]:
        """Get all topics for an agent."""
        return [
            cls.format_agent_status(agent_name),
            cls.format_agent_tasks(agent_name),
            cls.format_agent_events(agent_name),
            cls.format_agent_config(agent_name),
        ]
    
    @classmethod
    def get_fleet_wildcards(cls) -> List[str]:
        """Get all fleet-wide wildcard patterns."""
        return [
            str(cls.FLEET_BROADCAST),
            "iabai/agents/+/#",
            "iabai/fleet/+",
            "iabai/shared/+",
            "iabai/tasks/+",
            "iabai/status/+",
        ]
    
    @classmethod
    def validate_topic(cls, topic: str) -> bool:
        """Validate that a topic follows IABAI naming conventions."""
        allowed_prefixes = [
            "iabai/agents/",
            "iabai/fleet/",
            "iabai/shared/",
            "iabai/tasks/",
            "iabai/events/",
            "iabai/status/",
            "iabai/docs/",
            "iabai/config/",
        ]
        
        return any(topic.startswith(prefix) for prefix in allowed_prefixes)
    
    @classmethod
    def get_topic_stats(cls) -> Dict[str, Any]:
        """Get statistics about defined topic patterns."""
        patterns = [
            ("Agent Status", cls.AGENT_STATUS),
            ("Agent Tasks", cls.AGENT_TASKS),
            ("Agent Events", cls.AGENT_EVENTS),
            ("Fleet Status", cls.FLEET_STATUS),
            ("Fleet Tasks", cls.FLEET_TASKS),
            ("Fleet Events", cls.FLEET_EVENTS),
            ("Shared Config", cls.SHARED_CONFIG),
            ("Shared Data", cls.SHARED_DATA),
            ("Task Queue", cls.TASK_QUEUE),
            ("Task Results", cls.TASK_RESULTS),
            ("System Status", cls.SYSTEM_STATUS),
            ("Health Check", cls.HEALTH_CHECK),
        ]
        
        return {
            "total_patterns": len(patterns),
            "patterns": [
                {"name": name, "pattern": str(pattern)}
                for name, pattern in patterns
            ]
        }
