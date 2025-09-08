"""
Agent Workspace System - Core Classes

Provides persistent task memory and intelligent planning to prevent redundant actions
and maintain context across multi-step tasks.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Action:
    """Represents an action taken by the agent."""
    timestamp: datetime
    action_id: str
    tool: str
    args: Dict[str, Any]
    thought: str
    goal: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action_id": self.action_id,
            "tool": self.tool,
            "args": self.args,
            "thought": self.thought,
            "goal": self.goal
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action_id=data["action_id"],
            tool=data["tool"],
            args=data["args"],
            thought=data["thought"],
            goal=data["goal"]
        )


@dataclass
class Observation:
    """Represents an observation from an action."""
    timestamp: datetime
    observation_id: str
    action_id: str
    status: str
    output: Any
    extracted_info: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "observation_id": self.observation_id,
            "action_id": self.action_id,
            "status": self.status,
            "output": self.output,
            "extracted_info": self.extracted_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Observation':
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            observation_id=data["observation_id"],
            action_id=data["action_id"],
            status=data["status"],
            output=data["output"],
            extracted_info=data["extracted_info"]
        )


class TaskWorkspace:
    """
    Persistent workspace for a single task execution.
    
    Provides memory for actions, observations, and accumulated knowledge
    to prevent redundant operations and enable smarter decision making.
    """
    
    def __init__(self, task_id: str = None, original_request: str = ""):
        self.task_id = task_id or str(uuid.uuid4())
        self.original_request = original_request
        self.current_goal = ""
        self.actions_taken: List[Action] = []
        self.observations: List[Observation] = []
        self.accumulated_knowledge: Dict[str, Any] = {}
        self.progress_state = "initialized"
        self.next_steps: List[str] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_action(self, tool: str, args: Dict[str, Any], thought: str, goal: str) -> str:
        """Add a new action to the workspace."""
        action_id = str(uuid.uuid4())
        action = Action(
            timestamp=datetime.now(),
            action_id=action_id,
            tool=tool,
            args=args,
            thought=thought,
            goal=goal
        )
        self.actions_taken.append(action)
        self.current_goal = goal
        self.updated_at = datetime.now()
        return action_id
    
    def add_observation(self, action_id: str, status: str, output: Any, extracted_info: Dict[str, Any] = None) -> str:
        """Add an observation for a given action."""
        observation_id = str(uuid.uuid4())
        observation = Observation(
            timestamp=datetime.now(),
            observation_id=observation_id,
            action_id=action_id,
            status=status,
            output=output,
            extracted_info=extracted_info or {}
        )
        self.observations.append(observation)
        self.updated_at = datetime.now()
        return observation_id
    
    def update_knowledge(self, key: str, value: Any):
        """Update accumulated knowledge."""
        self.accumulated_knowledge[key] = value
        self.updated_at = datetime.now()
    
    def get_knowledge(self, key: str, default: Any = None) -> Any:
        """Retrieve accumulated knowledge."""
        return self.accumulated_knowledge.get(key, default)
    
    def has_performed_action(self, tool: str, args: Dict[str, Any] = None) -> bool:
        """Check if a similar action has already been performed."""
        for action in self.actions_taken:
            if action.tool == tool:
                if args is None:
                    return True
                # Check if args are similar (exact match for now, could be smarter)
                if action.args == args:
                    return True
        return False
    
    def get_last_observation_for_tool(self, tool: str) -> Optional[Observation]:
        """Get the most recent observation for a specific tool."""
        for action in reversed(self.actions_taken):
            if action.tool == tool:
                # Find corresponding observation
                for obs in reversed(self.observations):
                    if obs.action_id == action.action_id:
                        return obs
        return None
    
    def get_progress_summary(self) -> str:
        """Generate a summary of progress so far."""
        summary = f"Task: {self.original_request}\n"
        summary += f"Current Goal: {self.current_goal}\n"
        summary += f"Actions Taken: {len(self.actions_taken)}\n"
        summary += f"Status: {self.progress_state}\n"
        
        if self.accumulated_knowledge:
            summary += "\nAccumulated Knowledge:\n"
            for key, value in self.accumulated_knowledge.items():
                summary += f"  {key}: {value}\n"
        
        if self.next_steps:
            summary += "\nNext Steps:\n"
            for step in self.next_steps:
                summary += f"  - {step}\n"
        
        return summary
    
    def get_action_history_summary(self) -> str:
        """Get a summary of actions and their outcomes."""
        if not self.actions_taken:
            return "No actions taken yet."
        
        summary = "Action History:\n"
        for i, action in enumerate(self.actions_taken, 1):
            # Find corresponding observation
            obs = None
            for observation in self.observations:
                if observation.action_id == action.action_id:
                    obs = observation
                    break
            
            summary += f"{i}. {action.tool}({action.args}) - {action.thought}\n"
            if obs:
                summary += f"   → {obs.status}: {str(obs.output)[:100]}...\n"
            else:
                summary += f"   → No observation recorded\n"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workspace to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "original_request": self.original_request,
            "current_goal": self.current_goal,
            "actions_taken": [action.to_dict() for action in self.actions_taken],
            "observations": [obs.to_dict() for obs in self.observations],
            "accumulated_knowledge": self.accumulated_knowledge,
            "progress_state": self.progress_state,
            "next_steps": self.next_steps,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskWorkspace':
        """Create workspace from dictionary."""
        workspace = cls(
            task_id=data["task_id"],
            original_request=data["original_request"]
        )
        workspace.current_goal = data["current_goal"]
        workspace.actions_taken = [Action.from_dict(a) for a in data["actions_taken"]]
        workspace.observations = [Observation.from_dict(o) for o in data["observations"]]
        workspace.accumulated_knowledge = data["accumulated_knowledge"]
        workspace.progress_state = data["progress_state"]
        workspace.next_steps = data["next_steps"]
        workspace.created_at = datetime.fromisoformat(data["created_at"])
        workspace.updated_at = datetime.fromisoformat(data["updated_at"])
        return workspace


class WorkspaceManager:
    """
    Manages TaskWorkspace instances with persistence and retrieval.
    """
    
    def __init__(self, storage_dir: str = "./workspaces"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.active_workspaces: Dict[str, TaskWorkspace] = {}
    
    def create_workspace(self, original_request: str) -> TaskWorkspace:
        """Create a new task workspace."""
        workspace = TaskWorkspace(original_request=original_request)
        self.active_workspaces[workspace.task_id] = workspace
        self.save_workspace(workspace)
        return workspace
    
    def get_workspace(self, task_id: str) -> Optional[TaskWorkspace]:
        """Retrieve a workspace by task ID."""
        if task_id in self.active_workspaces:
            return self.active_workspaces[task_id]
        
        # Try to load from disk
        workspace_file = self.storage_dir / f"{task_id}.json"
        if workspace_file.exists():
            with open(workspace_file, 'r') as f:
                data = json.load(f)
            workspace = TaskWorkspace.from_dict(data)
            self.active_workspaces[task_id] = workspace
            return workspace
        
        return None
    
    def save_workspace(self, workspace: TaskWorkspace):
        """Persist workspace to disk."""
        workspace_file = self.storage_dir / f"{workspace.task_id}.json"
        with open(workspace_file, 'w') as f:
            json.dump(workspace.to_dict(), f, indent=2, default=str)
    
    def update_workspace(self, workspace: TaskWorkspace):
        """Update workspace in memory and persist to disk."""
        workspace.updated_at = datetime.now()
        self.active_workspaces[workspace.task_id] = workspace
        self.save_workspace(workspace)
    
    def close_workspace(self, task_id: str):
        """Mark workspace as completed and clean up from active memory."""
        if task_id in self.active_workspaces:
            workspace = self.active_workspaces[task_id]
            workspace.progress_state = "completed"
            self.save_workspace(workspace)
            del self.active_workspaces[task_id]
    
    def list_active_workspaces(self) -> List[str]:
        """List all active workspace IDs."""
        return list(self.active_workspaces.keys())
    
    def cleanup_old_workspaces(self, max_age_hours: int = 24):
        """Clean up workspaces older than max_age_hours."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for workspace_file in self.storage_dir.glob("*.json"):
            if workspace_file.stat().st_mtime < cutoff_time:
                workspace_file.unlink()
                
        # Also clean up from active memory
        to_remove = []
        for task_id, workspace in self.active_workspaces.items():
            if workspace.updated_at.timestamp() < cutoff_time:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_workspaces[task_id]
