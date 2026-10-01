"""
MQTT Agent Client Examples for IABAI fleet communication.

Shows how to use the iabai_mqtt library for inter-agent communication.
"""

import asyncio
import json
import logging
from datetime import datetime

# Import the library
from iabai_mqtt import AgentClient, TopicManager, MessageSerializer, MessageType
from iabai_mqtt.client import AgentConfig
from iabai_mqtt.messages import AgentMessage, MessageHeader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleAgent:
    """Example agent that demonstrates MQTT communication patterns."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.client = AgentClient(
            config=AgentConfig(
                broker_host="gx10",
                broker_port=1883,
                agent_name=agent_name,
                client_id=f"example-{agent_name}",
            )
        )
        self.is_running = False
        
    async def setup(self):
        """Set up the agent with handlers and subscriptions."""
        # Register connection handlers
        self.client.on_connect(self._on_connect)
        self.client.on_disconnect(self._on_disconnect)
        
        # Subscribe to relevant topics
        await self.client.subscribe(
            TopicManager.format_agent_tasks(self.agent_name),
            self._handle_tasks
        )
        
        await self.client.subscribe(
            TopicManager.format_agent_events(self.agent_name),
            self._handle_events
        )
        
        # Subscribe to fleet-wide topics
        await self.client.subscribe(
            TopicManager.FLEET_BROADCAST.pattern,
            self._handle_fleet_broadcast
        )
        
        # Connect to broker
        await self.client.connect()
        
        # Send initial heartbeat
        heartbeat = AgentMessage.create_heartbeat(self.agent_name)
        await self.client.publish(
            TopicManager.format_agent_status(self.agent_name),
            json.loads(heartbeat.to_json())
        )
        
        self.is_running = True
        logger.info(f"{self.agent_name} is running")
        
    async def _on_connect(self, client: AgentClient):
        """Handle connection event."""
        logger.info(f"Agent {self.agent_name} connected to MQTT broker")
        
    async def _on_disconnect(self, client: AgentClient):
        """Handle disconnection event."""
        logger.warning(f"Agent {self.agent_name} disconnected from MQTT broker")
        
    async def _handle_tasks(self, topic: str, data: dict):
        """Handle incoming task messages."""
        logger.info(f"Received task on {topic}: {data}")
        
        # Process the task
        if "command" in data:
            result = await self._execute_task(data["command"])
            
            # Send result back
            result_msg = AgentMessage.create_task_result(
                self.agent_name,
                data.get("task_id", "unknown"),
                result,
                success=True
            )
            await self.client.publish(
                TopicManager.format_agent_status(self.agent_name),
                json.loads(result_msg.to_json())
            )
            
    async def _handle_events(self, topic: str, data: dict):
        """Handle incoming event messages."""
        logger.info(f"Received event on {topic}: {data}")
        
    async def _handle_fleet_broadcast(self, topic: str, data: dict):
        """Handle fleet-wide broadcast messages."""
        logger.info(f"Received fleet broadcast on {topic}: {data}")
        
    async def _execute_task(self, command: str) -> dict:
        """Execute a task command."""
        logger.info(f"Executing task: {command}")
        
        # Simulate task execution
        return {
            "status": "completed",
            "command": command,
            "result": f"Task {command} completed successfully",
            "timestamp": datetime.now().isoformat(),
        }
    
    async def send_status_update(self, status: dict):
        """Send a status update to the fleet."""
        status_msg = AgentMessage(
            header=MessageHeader(
                message_id=f"status-{self.agent_name}-{datetime.now().isoformat()}",
                message_type=MessageType.STATUS_UPDATE,
                timestamp=datetime.now().isoformat(),
                sender=self.agent_name,
                priority=5,
            ),
            payload=status,
        )
        
        await self.client.publish(
            TopicManager.format_agent_status(self.agent_name),
            json.loads(status_msg.to_json())
        )
        
    async def send_fleet_broadcast(self, message: str):
        """Send a broadcast to the entire fleet."""
        broadcast_msg = AgentMessage.create_broadcast(
            self.agent_name,
            "general",
            message
        )
        
        await self.client.publish(
            TopicManager.FLEET_BROADCAST.pattern,
            json.loads(broadcast_msg.to_json())
        )
        
    async def cleanup(self):
        """Clean up resources."""
        self.is_running = False
        await self.client.disconnect()
        logger.info(f"Agent {self.agent_name} cleaned up")


async def main():
    """Run the example."""
    # Create and start the example agent
    agent = ExampleAgent("example-agent")
    
    try:
        await agent.setup()
        
        # Send a status update
        await agent.send_status_update({
            "status": "running",
            "uptime": 0,
            "tasks_completed": 0,
        })
        
        # Wait for a bit
        await asyncio.sleep(5)
        
        # Send a fleet broadcast
        await agent.send_fleet_broadcast("Example agent is online and ready")
        
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
