import uuid
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger('aide.tasks')

class TaskStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"

@dataclass
class Task:
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id":    self.task_id,
            "task_type":  self.task_type,
            "status":     self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress":   self.progress,
            "message":    self.message,
            "result":     self.result,
            "error":      self.error,
            "metadata":   self.metadata,
        }

class TaskManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._task_lock = threading.Lock()
        return cls._instance

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now()
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )
        with self._task_lock:
            self._tasks[task_id] = task
        logger.info("Task created: %s type=%s", task_id, task_type)
        return task_id

    def update_task(self, task_id: str, status=None, progress=None,
                    message=None, result=None, error=None):
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task:
                task.updated_at = datetime.now()
                if status   is not None: task.status   = status
                if progress is not None: task.progress = progress
                if message  is not None: task.message  = message
                if result   is not None: task.result   = result
                if error    is not None: task.error    = error

    def complete_task(self, task_id: str, result: Dict):
        self.update_task(task_id, status=TaskStatus.COMPLETED,
                         progress=100, message="Done", result=result)
        logger.info("Task completed: %s", task_id)

    def fail_task(self, task_id: str, error: str):
        self.update_task(task_id, status=TaskStatus.FAILED,
                         message="Failed", error=error)
        logger.error("Task failed: %s — %s", task_id, error)

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._task_lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list:
        with self._task_lock:
            return [t.to_dict() for t in
                    sorted(self._tasks.values(),
                           key=lambda x: x.created_at, reverse=True)]
