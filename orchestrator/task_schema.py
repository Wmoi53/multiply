from pydantic import BaseModel
from typing import Optional

class Task(BaseModel):
    type: str
    agent_label: str
    payload: dict
    due_date: Optional[str]
    priority: Optional[int] = 3
