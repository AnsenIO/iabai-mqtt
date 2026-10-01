"""
FleetClient - Main orchestration client for the IABAI fleet.

Ties together identity, authorization, project tracking, task management,
and inter-agent messaging into a single client for fleet orchestration.

Usage:
    from iabai_mqtt import AgentIdentity, Role, FleetClient
    
    # Create orchestrator identity
    mairead = AgentIdentity(name="Mairead", role=Role.ORCHESTRATOR)
    
    # Connect to fleet
    client = FleetClient(identity=mairead, broker="gx10", port=1883)
    await client.connect()
    
    # Create project
    await client.projects.create("project-x", "New initiative")
    
    # Add and assign tasks
    await client.tasks.add("project-x", "Analyze data", assignee="Hermione")
    await client.tasks.update_status("project-x", "task-1", "in_progress")
    
    # Validate completion (orchestrator only)
    await client.tasks.validate("project-x", "task-1", validator="Mairead")
    
    # Address another agent
    await client.messaging.send("Hermione", "Please update the status")
    
    # Monitor fleet
    stats = await client.get_fleet_stats()
"""

import asyncio
import json
import logging
from typing import Optional, Dict, List, Any, Callable, Awaitable
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from iabai_mqtt.identity import AgentIdentity, Role
from iabai_mqtt.auth import AuthorizationManager, Permission, AgentPermissions
from iabai_mqtt.projects import ProjectTracker, Project, ProjectStatus
from iabai_mqtt.tasks import TaskManager, TaskStatus, Task
from iabai_mqtt.messaging import FleetMessenger, MessageLog
from iabai_mqtt.messages import FleetMessage, MessageHeader, MessageType

logger = logging.getLogger(__name__)


class FleetClient:
    """Main orchestration client for the IABAI fleet."""
    
    def __init__(self, identity: AgentIdentity, broker: str = "gx10", 
                 port: int = 1883, username: Optional[str] = None,
                 password: Optional[str] = None):
        self.identity = identity
        self.broker_host = broker
        self.broker_port = port
        self.username = username or identity.username
        self.password = password or identity.password
        
        # Initialize subsystems
        self.auth = AuthorizationManager()
        self.projects = ProjectTracker()
        self.tasks = TaskManager()
        self.messaging = FleetMessenger()
        
        # MQTT client
        self.mqtt_client = None
        self.is_connected = False
        self._reconnect_task = None
        
        # Register this agent with auth manager
        self.auth.register_agent(identity.name, identity.role.value)
        
        # Message handlers
        self._setup_message_handlers()
    
    def _setup_message_handlers(self):
        """Set up message handlers for different message types."""
        self.messaging.register_handler("direct_message", self._handle_direct_message)
        self.messaging.register_handler("broadcast", self._handle_broadcast)
        self.messaging.register_handler("task_assign", self._handle_task_assign)
        self.messaging.register_handler("task_status_update", self._handle_task_status_update)
        self.messaging.register_handler("task_validate", self._handle_task_validate)
        self.messaging.register_handler("project_create", self._handle_project_create)
    
    def _handle_direct_message(self, sender: str, sender_role: str,
                              recipient: str, content: str, metadata: Dict):
        """Handle incoming direct messages."""
        logger.info(f"Direct message from {sender}: {content}")
    
    def _handle_broadcast(self, sender: str, sender_role: str,
                         recipient: str, content: str, metadata: Dict):
        """Handle incoming broadcasts."""
        logger.info(f"Broadcast from {sender}: {content}")
    
    def _handle_task_assign(self, sender: str, sender_role: str,
                           recipient: str, content: str, metadata: Dict):
        """Handle incoming task assignments."""
        logger.info(f"Task assignment from {sender}: {content}")
    
    def _handle_task_status_update(self, sender: str, sender_role: str,
                                  recipient: str, content: str, metadata: Dict):
        """Handle incoming task status updates."""
        logger.info(f"Task status update from {sender}: {content}")
    
    def _handle_task_validate(self, sender: str, sender_role: str,
                             recipient: str, content: str, metadata: Dict):
        """Handle incoming task validation."""
        logger.info(f"Task validation from {sender}: {content}")
    
    def _handle_project_create(self, sender: str, sender_role: str,
                              recipient: str, content: str, metadata: Dict):
        """Handle incoming project creation."""
        logger.info(f"Project creation from {sender}: {content}")
    
    async def connect(self):
        """Connect to the MQTT broker."""
        if self.is_connected:
            return
        
        if mqtt is None:
            raise ImportError("paho-mqtt is required. Install with: pip install paho-mqtt")
        
        self.mqtt_client = mqtt.Client(
            client_id=self.identity.client_id,
            clean_session=True,
        )
        
        # Set up callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        # Connect with credentials if available
        if self.username and self.password:
            self.mqtt_client.username_pw_set(self.username, self.password)
        
        try:
            self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
            self.mqtt_client.loop_start()
            await asyncio.sleep(1)
            self.is_connected = True
            
            # Send heartbeat
            heartbeat = FleetMessage.create_heartbeat(self.identity.name, self.identity.role.value)
            await self.publish(self.identity.get_status_topic(), heartbeat)
            
            logger.info(f"FleetClient connected: {self.identity.name} ({self.identity.role.value})")
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from the MQTT broker."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.is_connected = False
            logger.info(f"FleetClient disconnected: {self.identity.name}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        logger.info(f"MQTT connected: {self.identity.name}")
        self.is_connected = True
        
        # Subscribe to relevant topics
        topics = [
            (self.identity.get_status_topic(), 1),
            (self.identity.get_tasks_topic(), 1),
            (self.identity.get_events_topic(), 1),
            (f"iabai/fleet/#", 1),
        ]
        
        for topic, qos in topics:
            client.subscribe(topic, qos)
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        logger.warning(f"MQTT disconnected: {self.identity.name}")
        self.is_connected = False
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        topic = msg.topic
        payload = msg.payload.decode('utf-8') if msg.payload else ""
        
        logger.debug(f"Received message on {topic}: {payload[:100]}...")
        
        try:
            data = json.loads(payload) if payload else {}
            message_type = data.get("message_type", "")
            
            # Route to appropriate handler
            if message_type in self.messaging.message_handlers:
                self.messaging.message_handlers[message_type](
                    data.get("sender", "unknown"),
                    data.get("sender_role", "unknown"),
                    data.get("recipient", ""),
                    data.get("content", payload),
                    data.get("metadata", {}),
                )
        except json.JSONDecodeError:
            logger.error(f"Failed to decode message: {payload}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def publish(self, topic: str, message: FleetMessage, qos: int = 1,
                     retain: bool = False) -> bool:
        """Publish a message to a topic."""
        if not self.is_connected:
            logger.warning(f"Not connected, cannot publish to {topic}")
            return False
        
        payload = message.to_json()
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.mqtt_client.publish, topic, payload, qos, retain
            )
            logger.debug(f"Published to {topic}: {payload[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return False
    
    async def subscribe(self, topic: str, handler: Callable, qos: int = 1):
        """Subscribe to a topic."""
        if self.mqtt_client and self.is_connected:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.mqtt_client.subscribe, topic, qos
                )
                logger.info(f"Subscribed to {topic}")
            except Exception as e:
                logger.error(f"Subscribe failed: {e}")
    
    async def unsubscribe(self, topic: str):
        """Unsubscribe from a topic."""
        if self.mqtt_client and self.is_connected:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.mqtt_client.unsubscribe, topic
                )
                logger.info(f"Unsubscribed from {topic}")
            except Exception as e:
                logger.error(f"Unsubscribe failed: {e}")
    
    # Project operations
    async def create_project(self, name: str, description: str = "",
                            tags: List[str] = None) -> Optional[Project]:
        """Create a new project (requires CREATE_PROJECT permission)."""
        if not self._check_permission(Permission.CREATE_PROJECT):
            logger.warning(f"{self.identity.name} cannot create projects")
            return None
        
        project = self.projects.create_project(
            name=name,
            description=description,
            created_by=self.identity.name,
            tags=tags,
        )
        
        # Broadcast project creation
        broadcast_msg = FleetMessage.create_project_create(
            sender=self.identity.name,
            sender_role=self.identity.role.value,
            project_name=name,
            description=description,
            tags=tags,
        )
        await self.publish("iabai/fleet/projects", broadcast_msg)
        
        logger.info(f"Project created: {name} by {self.identity.name}")
        return project
    
    async def update_project(self, name: str, updates: Dict[str, Any]) -> bool:
        """Update a project (requires UPDATE_PROJECT permission)."""
        if not self._check_permission(Permission.UPDATE_PROJECT):
            return False
        
        project = self.projects.get_project(name)
        if project:
            self.projects.update_project(name, updates)
            return True
        return False
    
    async def get_project(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        return self.projects.get_project(name)
    
    async def get_all_projects(self) -> Dict[str, Project]:
        """Get all projects."""
        return self.projects.get_all_projects()
    
    async def search_projects(self, query: str) -> List[Project]:
        """Search projects."""
        return self.projects.search_projects(query)
    
    # Task operations
    async def add_task(self, project_name: str, title: str, description: str = "",
                      assignee: Optional[str] = None, priority: int = 0) -> Optional[Task]:
        """Add a task to a project (requires CREATE_TASK permission)."""
        if not self._check_permission(Permission.CREATE_TASK):
            logger.warning(f"{self.identity.name} cannot create tasks")
            return None
        
        task = self.tasks.create_task(
            project_name=project_name,
            title=title,
            description=description,
            created_by=self.identity.name,
            priority=priority,
        )
        
        # Add to project
        self.projects.add_task_to_project(project_name, task.id, task.to_dict())
        
        # If assignee is provided, assign the task
        if assignee and self.identity.role.can_assign:
            await self.assign_task(project_name, task.id, assignee)
        
        logger.info(f"Task created: {task.id} in {project_name} by {self.identity.name}")
        return task
    
    async def assign_task(self, project_name: str, task_id: str,
                         assignee: str) -> bool:
        """Assign a task to an agent (requires ASSIGN_TASK permission)."""
        if not self.identity.role.can_assign:
            logger.warning(f"{self.identity.name} cannot assign tasks")
            return False
        
        if not self._check_permission(Permission.ASSIGN_TASK):
            logger.warning(f"{self.identity.name} cannot assign tasks")
            return False
        
        success = self.tasks.assign_task(task_id, assignee, self.identity.name)
        
        if success:
            # Send assignment message
            assign_msg = FleetMessage.create_task_assign(
                sender=self.identity.name,
                sender_role=self.identity.role.value,
                task_id=task_id,
                assignee=assignee,
                project_name=project_name,
            )
            await self.publish(f"iabai/agents/{assignee.lower()}/tasks", assign_msg)
            
            logger.info(f"Task {task_id} assigned to {assignee} by {self.identity.name}")
        
        return success
    
    async def update_task_status(self, project_name: str, task_id: str,
                                new_status: str) -> bool:
        """Update task status (requires UPDATE_TASK_STATUS permission)."""
        if not self._check_permission(Permission.UPDATE_TASK_STATUS):
            logger.warning(f"{self.identity.name} cannot update task status")
            return False
        
        status_map = {
            "pending": TaskStatus.PENDING,
            "assigned": TaskStatus.ASSIGNED,
            "in_progress": TaskStatus.IN_PROGRESS,
            "blocked": TaskStatus.BLOCKED,
            "needs_review": TaskStatus.NEEDS_REVIEW,
            "completed": TaskStatus.COMPLETED,
            "cancelled": TaskStatus.CANCELLED,
        }
        
        task_status = status_map.get(new_status.lower())
        if not task_status:
            logger.error(f"Invalid status: {new_status}")
            return False
        
        success = self.tasks.update_task_status(task_id, task_status, self.identity.name)
        
        if success:
            # Send status update message
            status_msg = FleetMessage.create_task_status_update(
                sender=self.identity.name,
                sender_role=self.identity.role.value,
                task_id=task_id,
                new_status=new_status,
                project_name=project_name,
            )
            await self.publish("iabai/fleet/tasks", status_msg)
            
            logger.info(f"Task {task_id} status updated to {new_status} by {self.identity.name}")
        
        return success
    
    async def validate_task(self, project_name: str, task_id: str,
                          validator: Optional[str] = None,
                          notes: str = "") -> bool:
        """Validate task completion (orchestrator only)."""
        if not self.identity.role.can_validate:
            logger.warning(f"{self.identity.name} cannot validate tasks")
            return False
        
        validator = validator or self.identity.name
        
        success = self.tasks.validate_task(task_id, validator, notes)
        
        if success:
            # Send validation message
            validate_msg = FleetMessage.create_task_validate(
                sender=validator,
                sender_role=self.identity.role.value,
                task_id=task_id,
                project_name=project_name,
                notes=notes,
            )
            await self.publish("iabai/fleet/tasks", validate_msg)
            
            logger.info(f"Task {task_id} validated by {validator}")
        
        return success
    
    async def add_task_info(self, task_id: str, info: str) -> bool:
        """Add information to a task (requires READ_TASK permission)."""
        if not self._check_permission(Permission.READ_TASK):
            return False
        
        return self.tasks.add_task_info(task_id, info, self.identity.name)
    
    # Messaging operations
    async def send_message(self, recipient: str, content: str,
                          metadata: Optional[Dict] = None) -> MessageLog:
        """Send a direct message to another agent."""
        if not self._check_permission(Permission.SEND_MESSAGE):
            logger.warning(f"{self.identity.name} cannot send messages")
            raise PermissionError(f"{self.identity.name} cannot send messages")
        
        log = self.messaging.send_direct_message(
            sender=self.identity.name,
            sender_role=self.identity.role.value,
            recipient=recipient,
            content=content,
            metadata=metadata,
        )
        
        # Send via MQTT if connected
        if self.is_connected:
            message = FleetMessage.create_direct_message(
                sender=self.identity.name,
                sender_role=self.identity.role.value,
                recipient=recipient,
                content=content,
                metadata=metadata,
            )
            await self.publish(f"iabai/agents/{recipient.lower()}/events", message)
        
        return log
    
    async def broadcast(self, content: str, metadata: Optional[Dict] = None) -> MessageLog:
        """Send a broadcast to the fleet."""
        if not self._check_permission(Permission.BROADCAST):
            logger.warning(f"{self.identity.name} cannot broadcast")
            raise PermissionError(f"{self.identity.name} cannot broadcast")
        
        log = self.messaging.send_broadcast(
            sender=self.identity.name,
            sender_role=self.identity.role.value,
            content=content,
            metadata=metadata,
        )
        
        # Broadcast via MQTT if connected
        if self.is_connected:
            message = FleetMessage.create_broadcast(
                sender=self.identity.name,
                sender_role=self.identity.role.value,
                content=content,
                metadata=metadata,
            )
            await self.publish("iabai/fleet/events", message)
        
        return log
    
    # Authorization
    def _check_permission(self, permission: Permission, target: Optional[str] = None) -> bool:
        """Check if the current agent has a specific permission."""
        return self.auth.has_permission(self.identity.name, permission, target)
    
    def grant_permission(self, agent_name: str, permission: Permission):
        """Grant a permission to an agent (orchestrator only)."""
        if not self.identity.role.can_manage_permissions:
            raise PermissionError(f"{self.identity.name} cannot manage permissions")
        
        self.auth.grant_custom_permission(agent_name, permission)
    
    def revoke_permission(self, agent_name: str, permission: Permission):
        """Revoke a permission from an agent (orchestrator only)."""
        if not self.identity.role.can_manage_permissions:
            raise PermissionError(f"{self.identity.name} cannot manage permissions")
        
        self.auth.revoke_permission(agent_name, permission)
    
    # Fleet operations
    async def get_fleet_stats(self) -> Dict[str, Any]:
        """Get fleet-wide statistics."""
        project_stats = self.projects.get_project_stats()
        task_stats = self.tasks.get_task_stats()
        messaging_stats = self.messaging.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "projects": project_stats,
            "tasks": task_stats,
            "messaging": messaging_stats,
            "agent_identity": {
                "name": self.identity.name,
                "role": self.identity.role.value,
                "connected": self.is_connected,
            },
        }
    
    async def get_agent_status(self, agent_name: str) -> Optional[AgentPermissions]:
        """Get the status/permissions of another agent."""
        return self.auth.get_agent_permissions(agent_name)
    
    async def get_all_agents(self) -> Dict[str, AgentPermissions]:
        """Get all registered agents."""
        return self.auth.get_all_agents()
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            "connected": self.is_connected,
            "agent": self.identity.name,
            "role": self.identity.role.value,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "projects": len(self.projects.get_all_projects()),
            "tasks": len(self.tasks.tasks),
            "messaging": self.messaging.get_stats(),
        }
