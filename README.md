# IABAI MQTT - Inter-Agent Communication Library

A clean, typed Python library for inter-agent communication over MQTT in the IABAI fleet architecture.

## Features

- **Typed interfaces** for agent-to-agent communication
- **Standardized topic patterns** for fleet-wide coordination
- **Message serialization** with headers and metadata
- **Connection management** with automatic reconnection
- **Built-in heartbeat** and health monitoring
- **Fleet broadcast** support for system-wide announcements

## Quick Start

```python
from iabai_mqtt import AgentClient, TopicManager, AgentMessage
import asyncio

async def main():
    # Create client
    client = AgentClient(
        config=AgentConfig(
            broker_host="gx10",
            broker_port=1883,
            agent_name="my-agent",
        )
    )
    
    # Connect
    await client.connect()
    
    # Subscribe to topics
    await client.subscribe(
        TopicManager.format_agent_tasks("my-agent"),
        handler=my_task_handler
    )
    
    # Publish messages
    heartbeat = AgentMessage.create_heartbeat("my-agent")
    await client.publish(
        TopicManager.format_agent_status("my-agent"),
        heartbeat.to_json()
    )
    
    # Clean up
    await client.disconnect()

asyncio.run(main())
```

## Topic Structure

| Pattern | Description |
|---|---|
| `iabai/agents/{agent}/status` | Agent heartbeat and health |
| `iabai/agents/{agent}/tasks` | Task execution and results |
| `iabai/agents/{agent}/events` | Agent-specific events |
| `iabai/fleet/status` | Fleet-wide status |
| `iabai/fleet/tasks` | Fleet-wide task coordination |
| `iabai/fleet/events` | Fleet-wide events |
| `iabai/shared/config` | Shared configuration |
| `iabai/tasks/queue` | Task queue |
| `iabai/tasks/results` | Task results |
| `iabai/status/health` | System health checks |

## Installation

```bash
pip install -r requirements.txt
```

## Usage Patterns

### Agent Heartbeat
```python
heartbeat = AgentMessage.create_heartbeat("fabia")
await client.publish(
    TopicManager.format_agent_status("fabia"),
    heartbeat.to_json()
)
```

### Task Assignment
```python
task = AgentMessage(
    header=MessageHeader(
        message_id="task-001",
        message_type=MessageType.TASK_ASSIGN,
        timestamp=datetime.now().isoformat(),
        sender="coordinator",
        recipient="fabia",
        priority=5,
    ),
    payload={"command": "analyze_data", "params": {"file": "data.csv"}},
)
await client.publish(
    TopicManager.format_agent_tasks("fabia"),
    task.to_json()
)
```

### Fleet Broadcast
```python
broadcast = AgentMessage.create_broadcast(
    "fabia",
    "maintenance",
    "System update in 10 minutes"
)
await client.publish(
    TopicManager.FLEET_BROADCAST.pattern,
    broadcast.to_json()
)
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run example
python examples/agent_example.py
```

## License

MIT
