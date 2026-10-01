"""
IABAI Fleet Orchestration Example

Demonstrates the fleet orchestration workflow:
1. Create agent identities (Mairead as orchestrator, agents as workers)
2. Connect to the fleet
3. Create a project
4. Add and assign tasks
5. Update task statuses
6. Validate task completion
7. Address agents via messaging
8. Monitor fleet statistics
"""

import asyncio
from iabai_mqtt import AgentIdentity, Role, FleetClient
from iabai_mqtt.tasks import TaskStatus


async def main():
    # 1. Create agent identities
    print("=" * 60)
    print("IABAI Fleet Orchestration Example")
    print("=" * 60)
    
    # Mairead as orchestrator
    mairead = AgentIdentity(
        name="Mairead",
        role=Role.ORCHESTRATOR,
        username="mairead",
        metadata={"description": "Fleet orchestrator - oversees all agents and assigns tasks"},
    )
    
    # Hermione as worker
    hermine = AgentIdentity(
        name="Hermione",
        role=Role.WORKER,
        username="hermine",
        metadata={"description": "Data analysis agent"},
    )
    
    # Lyra as manager
    lyra = AgentIdentity(
        name="Lyra",
        role=Role.MANAGER,
        username="lyra",
        metadata={"description": "Project manager - assigns tasks within domain"},
    )
    
    print(f"\n1. Agent Identities Created:")
    print(f"   - {mairead.name}: {mairead.role.value} (can assign: {mairead.role.can_assign}, can validate: {mairead.role.can_validate})")
    print(f"   - {hermine.name}: {hermine.role.value} (can assign: {hermine.role.can_assign}, can validate: {hermine.role.can_validate})")
    print(f"   - {lyra.name}: {lyra.role.value} (can assign: {lyra.role.can_assign}, can validate: {lyra.role.can_validate})")
    
    # 2. Connect to fleet (without MQTT for demo)
    print(f"\n2. Connecting to fleet...")
    
    # For demo, we'll use the components directly without MQTT
    from iabai_mqtt import AuthorizationManager, ProjectTracker, TaskManager, FleetMessenger
    
    # Initialize components
    auth = AuthorizationManager()
    projects = ProjectTracker()
    tasks = TaskManager()
    messenger = FleetMessenger()
    
    # Register agents
    auth.register_agent(mairead.name, mairead.role.value)
    auth.register_agent(hermine.name, hermine.role.value)
    auth.register_agent(lyra.name, lyra.role.value)
    
    # Grant permissions
    auth.grant_custom_permission(mairead.name, "CREATE_PROJECT")
    auth.grant_custom_permission(mairead.name, "ASSIGN_TASK")
    auth.grant_custom_permission(mairead.name, "VALIDATE_TASK")
    auth.grant_custom_permission(lyra.name, "CREATE_PROJECT")
    auth.grant_custom_permission(lyra.name, "ASSIGN_TASK")
    
    print(f"   - Fleet initialized with {len(auth.agent_permissions)} agents")
    
    # 3. Create a project
    print(f"\n3. Creating project...")
    project = projects.create_project(
        name="SME-Automation-Pilot",
        description="Free 90-day automation pilot for SME customers",
        created_by="Mairead",
        tags=["automation", "SME", "pilot"],
    )
    project.add_member("Mairead")
    project.add_member("Hermione")
    project.add_member("Lyra")
    
    print(f"   - Project '{project.name}' created")
    print(f"   - Status: {project.status.value}")
    print(f"   - Members: {', '.join(project.members)}")
    print(f"   - Tags: {', '.join(project.tags)}")
    
    # 4. Add and assign tasks
    print(f"\n4. Adding tasks...")
    
    task1 = tasks.create_task(
        project_name="SME-Automation-Pilot",
        title="Analyze customer data",
        description="Collect and analyze data from pilot customers",
        created_by="Mairead",
        priority=8,
    )
    tasks.assign_task(task1.id, "Hermione", "Mairead")
    projects.add_task_to_project("SME-Automation-Pilot", task1.id, task1.to_dict())
    
    task2 = tasks.create_task(
        project_name="SME-Automation-Pilot",
        title="Design automation workflows",
        description="Create automation workflows for common SME pain points",
        created_by="Mairead",
        priority=7,
    )
    tasks.assign_task(task2.id, "Lyra", "Mairead")
    projects.add_task_to_project("SME-Automation-Pilot", task2.id, task2.to_dict())
    
    task3 = tasks.create_task(
        project_name="SME-Automation-Pilot",
        title="Set up monitoring dashboard",
        description="Create real-time monitoring for pilot progress",
        created_by="Mairead",
        priority=5,
    )
    projects.add_task_to_project("SME-Automation-Pilot", task3.id, task3.to_dict())
    
    print(f"   - Task '{task1.id}' created and assigned to {task1.assignee}")
    print(f"   - Task '{task2.id}' created and assigned to {task2.assignee}")
    print(f"   - Task '{task3.id}' created (pending assignment)")
    
    # 5. Update task statuses
    print(f"\n5. Updating task statuses...")
    
    tasks.update_task_status(task1.id, TaskStatus.ASSIGNED, "Hermione")
    tasks.update_task_status(task1.id, TaskStatus.IN_PROGRESS, "Hermione")
    tasks.update_task_status(task2.id, TaskStatus.ASSIGNED, "Lyra")
    tasks.update_task_status(task2.id, TaskStatus.IN_PROGRESS, "Lyra")
    
    print(f"   - '{task1.id}' → in_progress (by Hermione)")
    print(f"   - '{task2.id}' → in_progress (by Lyra)")
    
    # 6. Add information to tasks
    print(f"\n6. Adding information to tasks...")
    
    tasks.add_task_info(task1.id, "Customer data collected: 15 SMEs", "Hermione")
    tasks.add_task_info(task1.id, "Initial analysis shows invoice automation as top priority", "Hermione")
    
    print(f"   - Added info to '{task1.id}'")
    
    # 7. Validate task completion
    print(f"\n7. Validating task completion...")
    
    tasks.update_task_status(task1.id, TaskStatus.NEEDS_REVIEW, "Hermione")
    validation_success = tasks.validate_task(task1.id, "Mairead", "Good work - data is comprehensive")
    
    if validation_success:
        print(f"   - '{task1.id}' validated by Mairead")
    
    # 8. Send messages
    print(f"\n8. Sending messages...")
    
    msg1 = messenger.send_direct_message(
        sender="Mairead",
        sender_role="ORCHESTRATOR",
        recipient="Lyra",
        content="Please prioritize the automation workflow design. We need it by Friday.",
    )
    
    msg2 = messenger.send_broadcast(
        sender="Mairead",
        sender_role="ORCHESTRATOR",
        content="Update on SME-Automation-Pilot: Task 1 is complete. Moving to phase 2.",
    )
    
    print(f"   - Direct message to Lyra")
    print(f"   - Broadcast to fleet")
    
    # 9. Fleet statistics
    print(f"\n9. Fleet Statistics:")
    
    project_stats = projects.get_project_stats()
    task_stats = tasks.get_task_stats()
    messaging_stats = messenger.get_stats()
    
    print(f"   - Projects: {project_stats['total_projects']}")
    print(f"   - Tasks: {task_stats['total']} (completed: {task_stats['by_status'].get('completed', 0)})")
    print(f"   - Messaging: {messaging_stats['total_messages_inbox']} inbox, {messaging_stats['total_messages_outbox']} outbox")
    
    # 10. Show project details
    print(f"\n10. Project Details:")
    
    project = projects.get_project("SME-Automation-Pilot")
    project_tasks = tasks.get_project_tasks("SME-Automation-Pilot")
    
    print(f"   - Name: {project.name}")
    print(f"   - Status: {project.status.value}")
    print(f"   - Progress: {project.progress:.1f}%")
    print(f"   - Tasks:")
    for task in project_tasks:
        print(f"     * {task.id}: {task.title} ({task.status.value}) - assigned to {task.assignee or 'unassigned'}")
    
    # 11. Show task history
    print(f"\n11. Task History (task1):")
    
    for entry in task1.history:
        print(f"   - {entry['action']}: {entry.get('by', entry.get('to', ''))} ({entry['timestamp']})")
    
    print(f"\n{'=' * 60}")
    print("Example complete!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
