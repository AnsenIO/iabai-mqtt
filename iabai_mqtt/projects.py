"""
Project tracking for the IABAI fleet.

Manages project lifecycle, status tracking, and task organization.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Set
from enum import Enum
from datetime import datetime


class ProjectStatus(Enum):
    """Status of a project in the fleet."""
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


@dataclass
class Project:
    """Represents a project in the IABAI fleet."""
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tasks: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    members: Set[str] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    
    @property
    def task_count(self) -> int:
        return len(self.tasks)
    
    @property
    def completed_tasks(self) -> int:
        return sum(1 for task in self.tasks.values() 
                   if task.get("status") == "completed")
    
    @property
    def progress(self) -> float:
        """Calculate project progress percentage."""
        if not self.tasks:
            return 0.0
        return (self.completed_tasks / len(self.tasks)) * 100
    
    def add_task(self, task_id: str, task_data: Dict[str, Any]):
        """Add a task to the project."""
        self.tasks[task_id] = task_data
        self.updated_at = datetime.now()
    
    def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update a task in the project."""
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)
            self.updated_at = datetime.now()
    
    def remove_task(self, task_id: str):
        """Remove a task from the project."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.updated_at = datetime.now()
    
    def add_member(self, member_name: str):
        """Add a member to the project."""
        self.members.add(member_name)
    
    def remove_member(self, member_name: str):
        """Remove a member from the project."""
        self.members.discard(member_name)
    
    def add_tag(self, tag: str):
        """Add a tag to the project."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize project to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tasks": self.tasks,
            "metadata": self.metadata,
            "members": list(self.members),
            "tags": self.tags,
            "progress": self.progress,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Deserialize project from dictionary."""
        project = cls(
            name=data["name"],
            description=data.get("description", ""),
            status=ProjectStatus(data.get("status", "draft")),
            created_by=data.get("created_by", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            tasks=data.get("tasks", {}),
            metadata=data.get("metadata", {}),
            members=set(data.get("members", [])),
            tags=data.get("tags", []),
        )
        return project


class ProjectTracker:
    """Manages projects in the IABAI fleet."""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.tags: Dict[str, Set[str]] = {}  # tag -> set of project names
    
    def create_project(self, name: str, description: str = "", 
                       created_by: str = "", tags: List[str] = None) -> Project:
        """Create a new project."""
        project = Project(
            name=name,
            description=description,
            created_by=created_by,
            tags=tags or [],
        )
        
        self.projects[name.lower()] = project
        
        # Update tags
        for tag in (tags or []):
            if tag not in self.tags:
                self.tags[tag] = set()
            self.tags[tag].add(name.lower())
        
        return project
    
    def get_project(self, name: str) -> Optional[Project]:
        """Get a project by name."""
        return self.projects.get(name.lower())
    
    def update_project(self, name: str, updates: Dict[str, Any]) -> Optional[Project]:
        """Update a project."""
        project = self.projects.get(name.lower())
        if project:
            for key, value in updates.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            project.updated_at = datetime.now()
        return project
    
    def delete_project(self, name: str) -> bool:
        """Delete a project."""
        if name.lower() in self.projects:
            project = self.projects[name.lower()]
            # Remove from tags
            for tag in project.tags:
                if tag in self.tags:
                    self.tags[tag].discard(name.lower())
            del self.projects[name.lower()]
            return True
        return False
    
    def add_task_to_project(self, project_name: str, task_id: str, 
                           task_data: Dict[str, Any]) -> bool:
        """Add a task to a project."""
        project = self.projects.get(project_name.lower())
        if project:
            project.add_task(task_id, task_data)
            return True
        return False
    
    def update_task_in_project(self, project_name: str, task_id: str,
                              updates: Dict[str, Any]) -> bool:
        """Update a task in a project."""
        project = self.projects.get(project_name.lower())
        if project:
            project.update_task(task_id, updates)
            return True
        return False
    
    def get_projects_by_tag(self, tag: str) -> List[Project]:
        """Get all projects with a specific tag."""
        project_names = self.tags.get(tag, set())
        return [self.projects[name] for name in project_names if name in self.projects]
    
    def get_all_projects(self) -> Dict[str, Project]:
        """Get all projects."""
        return self.projects.copy()
    
    def search_projects(self, query: str) -> List[Project]:
        """Search projects by name, description, or tags."""
        query_lower = query.lower()
        results = []
        
        for project in self.projects.values():
            if (query_lower in project.name.lower() or
                query_lower in project.description.lower() or
                any(query_lower in tag.lower() for tag in project.tags)):
                results.append(project)
        
        return results
    
    def get_project_stats(self) -> Dict[str, Any]:
        """Get statistics about all projects."""
        total = len(self.projects)
        by_status = {}
        total_tasks = 0
        total_completed = 0
        
        for project in self.projects.values():
            status = project.status.value
            by_status[status] = by_status.get(status, 0) + 1
            total_tasks += len(project.tasks)
            total_completed += project.completed_tasks
        
        return {
            "total_projects": total,
            "by_status": by_status,
            "total_tasks": total_tasks,
            "total_completed_tasks": total_completed,
            "overall_progress": (total_completed / total_tasks * 100) if total_tasks > 0 else 0,
        }
