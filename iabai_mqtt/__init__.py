"""
IABAI Fleet Orchestration Library (v0.2.0)

A fleet orchestration protocol for inter-agent communication via MQTT,
supporting identity, authorization, project tracking, and task lifecycle
management for the IABAI multi-agent system.

Architecture:
    FleetClient
        ├── AgentIdentity  — agent identity & role hierarchy
        ├── AuthorizationManager  — granular permission system
        ├── ProjectTracker  — project lifecycle & status tracking
        ├── TaskManager  — task creation, assignment, validation
        ├── FleetMessenger  — inter-agent messaging
        └── FleetMessage  — standardized message serialization

Usage:
    from iabai_mqtt import AgentIdentity, Role, FleetClient
    
    # Create orchestrator identity
    mairead = AgentIdentity(name="Mairead", role=Role.ORCHESTRATOR)
    
    # Connect to fleet
    client = FleetClient(identity=mairead, broker="gx10", port=1883)
    await client.connect()
    
    # Create project
    await client.create_project("project-x", "New initiative")
    
    # Add and assign tasks
    await client.add_task("project-x", "Analyze data", assignee="Hermione")
    await client.update_task_status("project-x", "task-1", "in_progress")
    
    # Validate completion (orchestrator only)
    await client.validate_task("project-x", "task-1", validator="Mairead")
    
    # Address another agent
    await client.send_message("Hermione", "Please update the status")
    
    # Monitor fleet
    stats = await client.get_fleet_stats()
"""

__version__ = "0.2.0"
__author__ = "IABAI Team"
__license__ = "MIT"

from iabai_mqtt.identity import AgentIdentity, Role
from iabai_mqtt.auth import AuthorizationManager, Permission, AgentPermissions
from iabai_mqtt.projects import ProjectTracker, Project, ProjectStatus
from iabai_mqtt.tasks import TaskManager, TaskStatus, Task
from iabai_mqtt.messaging import FleetMessenger, MessageLog, MessageDirection
from iabai_mqtt.messages import FleetMessage, MessageHeader, MessageType
from iabai_mqtt.fleet import FleetClient

__all__ = [
    # Identity
    "AgentIdentity",
    "Role",
    # Authorization
    "AuthorizationManager",
    "Permission",
    "AgentPermissions",
    # Projects
    "ProjectTracker",
    "Project",
    "ProjectStatus",
    # Tasks
    "TaskManager",
    "TaskStatus",
    "Task",
    # Messaging
    "FleetMessenger",
    "MessageLog",
    "MessageDirection",
    # Messages
    "FleetMessage",
    "MessageHeader",
    "MessageType",
    # Main client
    "FleetClient",
]
