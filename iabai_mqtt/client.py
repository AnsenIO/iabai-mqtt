"""
MQTT Agent Client for IABAI fleet communication.

Provides a clean, typed interface for agents to publish/subscribe to MQTT topics
on the gx10 broker.
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the MQTT agent client."""
    broker_host: str = "gx10"
    broker_port: int = 1883
    agent_name: str = "default"
    client_id: Optional[str] = None
    keepalive: int = 60
    reconnect_delay: int = 5
    max_reconnect_attempts: int = -1  # -1 = infinite
    clean_session: bool = True
    will_topic: Optional[str] = None
    will_message: Optional[str] = None
    will_qos: int = 1
    will_retain: bool = False


class AgentClient:
    """MQTT client for IABAI agent communication."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.client_id = self.config.client_id or f"iabai-{self.config.agent_name}-{id(self)}"
        self.client = None
        self.is_connected = False
        self.subscribers: Dict[str, Callable] = {}
        self._reconnect_task: Optional[asyncio.Task] = None
        self._last_error: Optional[str] = None
        self._on_connect_callbacks: List[Callable] = []
        self._on_disconnect_callbacks: List[Callable] = []
        
    def _create_mqtt_client(self):
        """Create a new MQTT client instance."""
        if mqtt is None:
            raise ImportError("paho-mqtt is required. Install with: pip install paho-mqtt")
            
        client = mqtt.Client(
            client_id=self.client_id,
            clean_session=self.config.clean_session,
        )
        
        # Set up callbacks
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_connect_fail = self._on_connect_fail
        
        # Set last will if configured
        if self.config.will_topic:
            client.will_set(
                self.config.will_topic,
                self.config.will_message or json.dumps({"status": "offline"}),
                qos=self.config.will_qos,
                retain=self.config.will_retain
            )
            
        return client
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        logger.info(f"MQTT connected: {self.config.agent_name}")
        self.is_connected = True
        self._last_error = None
        
        # Re-subscribe to all topics
        for topic, handler in self.subscribers.items():
            client.subscribe(topic, qos=1)
            logger.debug(f"Re-subscribed to {topic}")
            
        # Call connect callbacks
        for callback in self._on_connect_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Connect callback error: {e}")
                
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        logger.warning(f"MQTT disconnected: {self.config.agent_name}")
        self.is_connected = False
        
        # Call disconnect callbacks
        for callback in self._on_disconnect_callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Disconnect callback error: {e}")
                
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message."""
        topic = msg.topic
        payload = msg.payload.decode('utf-8') if msg.payload else ""
        
        logger.debug(f"Received message on {topic}: {payload[:100]}...")
        
        # Find matching subscriber
        for sub_topic, handler in self.subscribers.items():
            if self._topic_matches(sub_topic, topic):
                try:
                    # Try to parse as JSON
                    data = json.loads(payload) if payload else {}
                    handler(topic, data)
                except json.JSONDecodeError:
                    handler(topic, payload)
                except Exception as e:
                    logger.error(f"Handler error for {topic}: {e}")
                    
    def _on_connect_fail(self, client, userdata, rc):
        """Handle MQTT connection failure."""
        self._last_error = f"Connection failed: {rc}"
        logger.error(f"MQTT connection failed: {self._last_error}")
        
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Check if a topic matches a pattern."""
        # Simple wildcard matching
        pattern_parts = pattern.split('/')
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
        
    async def connect(self):
        """Connect to the MQTT broker."""
        if self.is_connected:
            return
            
        self.client = self._create_mqtt_client()
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.connect, self.config.broker_host, self.config.broker_port, self.config.keepalive
            )
            
            # Start loop in background
            self._reconnect_task = asyncio.get_event_loop().run_in_executor(
                None, self.client.loop_start
            )
            
            # Wait for connection
            await asyncio.sleep(1)
            
            if not self.is_connected:
                raise ConnectionError("Failed to connect to MQTT broker")
                
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Failed to connect: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from the MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info(f"MQTT disconnected: {self.config.agent_name}")
            
    async def publish(self, topic: str, payload: Any, qos: int = 1, retain: bool = False) -> bool:
        """Publish a message to a topic."""
        if not self.is_connected:
            logger.warning(f"Not connected, cannot publish to {topic}")
            return False
            
        # Serialize payload
        if isinstance(payload, (dict, list)):
            message = json.dumps(payload)
        else:
            message = str(payload)
            
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.client.publish, topic, message, qos, retain
            )
            logger.debug(f"Published to {topic}: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            self._last_error = str(e)
            return False
            
    async def subscribe(self, topic: str, handler: Callable, qos: int = 1):
        """Subscribe to a topic."""
        if not self.is_connected:
            logger.warning(f"Not connected, subscription will be applied on reconnect: {topic}")
            self.subscribers[topic] = handler
            return
            
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.subscribe, topic, qos
            )
            self.subscribers[topic] = handler
            logger.info(f"Subscribed to {topic}")
        except Exception as e:
            logger.error(f"Subscribe failed: {e}")
            
    async def unsubscribe(self, topic: str):
        """Unsubscribe from a topic."""
        if self.client and self.is_connected:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.client.unsubscribe, topic
                )
                self.subscribers.pop(topic, None)
                logger.info(f"Unsubscribed from {topic}")
            except Exception as e:
                logger.error(f"Unsubscribe failed: {e}")
                
    def on_connect(self, callback: Callable):
        """Register a callback for connection events."""
        self._on_connect_callbacks.append(callback)
        
    def on_disconnect(self, callback: Callable):
        """Register a callback for disconnection events."""
        self._on_disconnect_callbacks.append(callback)
        
    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
        
    @property
    def status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            "connected": self.is_connected,
            "agent": self.config.agent_name,
            "client_id": self.client_id,
            "broker": f"{self.config.broker_host}:{self.config.broker_port}",
            "last_error": self._last_error,
            "subscribers": len(self.subscribers),
        }
