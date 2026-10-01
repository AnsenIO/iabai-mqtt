"""
IABAI MQTT - Inter-agent communication library for the IABAI fleet.

Provides a clean, typed interface for agents to publish/subscribe to MQTT topics
on the gx10 broker. Includes topic management, message serialization, and
built-in health monitoring.

Usage:
    from iabai_mqtt import AgentClient
    
    client = AgentClient(agent_name="fabia")
    await client.connect()
    await client.publish("iabai/fleet/status", {"status": "online"})
    await client.subscribe("iabai/agents/*/tasks", handler=my_handler)
"""

__version__ = "0.1.0"
__author__ = "IABAI Fleet"

from iabai_mqtt.client import AgentClient
from iabai_mqtt.topics import TopicManager, TopicPattern
from iabai_mqtt.messages import MessageSerializer, MessageType

__all__ = [
    "AgentClient",
    "TopicManager",
    "TopicPattern",
    "MessageSerializer",
    "MessageType",
]
