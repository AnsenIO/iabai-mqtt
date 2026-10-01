"""
Task lifecycle management for the IABAI fleet.

Handles task creation, assignment, status updates, and validation.
Only orchestrators can assign tasks and validate completion.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Set
from enum import Enum
from datetime import datetime


class TaskStatus(Enum):
    """Status of a task in the fleet."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task in the IABAI fleet."""
    id: str
    project_name: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assignee: Optional[str] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    validator: Optional[str] = None
    validation_notes: str = ""
    priority: int = 0  # 0-10, higher = more urgent
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.history:
            self.history = [{
                "action": "created",
                "by": self.created_by,
                "timestamp": self.created_at.isoformat(),
            }]
    
    def assign_to(self, assignee: str, assigned_by: str) -> bool:
        """Assign this task to an agent."""
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False
        self.assignee = assignee
        self.status = TaskStatus.ASSIGNED
        self.updated_at = datetime.now()
        self.history.append({
            "action": "assigned",
            "to": assignee,
            "by": assigned_by,
            "timestamp": self.updated_at.isoformat(),
        })
        return True
    
    def start(self, started_by: str) -> bool:
        """Mark task as in progress."""
        if self.status != TaskStatus.ASSIGNED:
            return False
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.updated_at = datetime.now()
        self.history.append({
            "action": "started",
            "by": started_by,
            "timestamp": self.started_at.isoformat(),
        })
        return True
    
    def update_status(self, new_status: TaskStatus, updated_by: str) -> bool:
        """Update task status."""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()
        self.history.append({
            "action": "status_changed",
            "from": old_status.value,
            "to": new_status.value,
            "by": updated_by,
            "timestamp": self.updated_at.isoformat(),
        })
        return True
    
    def validate(self, validator: str, notes: str = "") -> bool:
        """Validate task completion (orchestrator only)."""
        if self.status != TaskStatus.NEEDS_REVIEW:
            return False
        self.status = TaskStatus.COMPLETED
        self.validator = validator
        self.validation_notes = notes
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        self.history.append({
            "action": "validated",
            "by": validator,
            "notes": notes,
            "timestamp": self.completed_at.isoformat(),
        })
        return True
    
    def add_info(self, info: str, added_by: str) -> bool:
        """Add information to a task."""
        self.metadata.setdefault("info", []).append({
            "text": info,
            "added_by": added_by,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "id": self.id,
            "project_name": self.project_name,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "assignee": self.assignee,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "validator": self.validator,
            "validation_notes": self.validation_notes,
            "priority": self.priority,
            "metadata": self.metadata,
            "history": self.history,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Deserialize task from dictionary."""
        task = cls(
            id=data["id"],
            project_name=data["project_name"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            assignee=data.get("assignee"),
            created_by=data.get("created_by", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            validator=data.get("validator"),
            validation_notes=data.get("validation_notes", ""),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
            history=data.get("history", []),
        )
        return task


class TaskManager:
    """Manages tasks across all projects in the IABAI fleet."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.project_tasks: Dict[str, Set[str]] = {}  # project_name -> set of task_ids
    
    def create_task(self, project_name: str, title: str, description: str = "",
                   created_by: str = "", priority: int = 0) -> Optional[Task]:
        """Create a new task in a project."""
        task_id = f"{project_name.lower()}-{len(self.project_tasks.get(project_name.lower(), set())) + 1}"
        
        task = Task(
            id=task_id,
            project_name=project_name,
            title=title,
            description=description,
            created_by=created_by,
            priority=priority,
        )
        
        self.tasks[task_id] = task
        
        if project_name.lower() not in self.project_tasks:
            self.project_tasks[project_name.lower()] = set()
        self.project_tasks[project_name.lower()].add(task_id)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_project_tasks(self, project_name: str) -> List[Task]:
        """Get all tasks for a project."""
        task_ids = self.project_tasks.get(project_name.lower(), set())
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]
    
    def assign_task(self, task_id: str, assignee: str, assigned_by: str) -> bool:
        """Assign a task to an agent (requires authorization)."""
        task = self.tasks.get(task_id)
        if task:
            return task.assign_to(assignee, assigned_by)
        return False
    
    def update_task_status(self, task_id: str, new_status: TaskStatus, 
                          updated_by: str) -> bool:
        """Update task status."""
        task = self.tasks.get(task_id)
        if task:
            return task.update_status(new_status, updated_by)
        return False
    
    def validate_task(self, task_id: str, validator: str, 
                     notes: str = "") -> bool:
        """Validate task completion (orchestrator only)."""
        task = self.tasks.get(task_id)
        if task:
            return task.validate(validator, notes)
        return False
    
    def add_task_info(self, task_id: str, info: str, added_by: str) -> bool:
        """Add information to a task."""
        task = self.tasks.get(task_id)
        if task:
            return task.add_info(info, added_by)
        return False
    
    def get_pending_tasks(self, project_name: Optional[str] = None) -> List[Task]:
        """Get all pending tasks, optionally filtered by project."""
        tasks = self.tasks.values() if not project_name else \
                self.get_project_tasks(project_name)
        return [t for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.ASSIGNED)]
    
    def get_in_progress_tasks(self, project_name: Optional[str] = None) -> List[Task]:
        """Get all in-progress tasks."""
        tasks = self.tasks.values() if not project_name else \
                self.get_project_tasks(project_name)
        return [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
    
    def get_completed_tasks(self, project_name: Optional[str] = None) -> List[Task]:
        """Get all completed tasks."""
        tasks = self.tasks.values() if not project_name else \
                self.get_project_tasks(project_name)
        return [t for t in tasks if t.status == TaskStatus.COMPLETED]
    
    def get_task_stats(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about tasks."""
        tasks = self.tasks.values() if not project_name else \
                self.get_project_tasks(project_name)
        
        by_status = {}
        for task in tasks:
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total": len(tasks),
            "by_status": by_status,
            "by_priority": self._get_priority_stats(tasks),
        }
    
    def _get_priority_stats(self, tasks: List[Task]) -> Dict[str, int]:
        """Get task statistics by priority."""
        stats = {"high": 0, "medium": 0, "low": 0}
        for task in tasks:
            if task.priority >= 7:
                stats["high"] += 1
            elif task.priority >= 4:
                stats["medium"] += 1
            else:
                stats["low"] += 1
        return stats
